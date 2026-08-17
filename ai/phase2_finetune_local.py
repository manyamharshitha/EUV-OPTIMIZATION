"""
phase2_finetune_local.py  --  Person C (AI Engineer)

Builds the local model from Modelfile + claude_knowledge.json.

-----------------------------------------------------------------------------
READ THIS BEFORE SAYING THE WORD "FINE-TUNE" TO A JUDGE
-----------------------------------------------------------------------------

The workplan calls this step a fine-tune. What this script actually does is
`ollama create`, which builds a model with a custom system prompt, decoding
parameters, and injected knowledge on top of a frozen base model.

That is NOT fine-tuning. No weights are updated. No gradients are computed.
There is no training set, no loss curve, no LoRA adapter.

The distinction matters because a judge with ML background will ask "what did
you fine-tune it on?" and "what was your loss?" -- and if the honest answer is
"we didn't, we wrote a system prompt", it is far better to have said so
first.

What to say:

    "We didn't fine-tune. We ran a frozen Mistral 7B locally with a
     constrained system prompt and a generated fact base, and we put a
     hard validator in front of its output so it can't state a number
     outside the published envelope. Weight-level training on a laptop
     in three days wasn't realistic, and the validator matters more for
     correctness anyway."

That answer is stronger than a vague claim of fine-tuning, because it is true
and it shows you understood the trade-off.

If you genuinely want weight updates later, the route is a LoRA adapter via
llama.cpp or unsloth on the base model, then `FROM ./adapter` in the
Modelfile. That is a multi-day job with a GPU and it is out of scope for a
three-day build.
-----------------------------------------------------------------------------

Runs offline. Requires Ollama installed and the base model pulled.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODELFILE = os.path.join(HERE, "Modelfile")
KNOWLEDGE = os.path.join(HERE, "claude_knowledge.json")
BUILD_MODELFILE = os.path.join(HERE, "Modelfile.generated")

MODEL_NAME = "my-claude-local"
BASE_MODEL = "mistral:7b-instruct"


def check_prerequisites() -> dict:
    """Everything that must be true before a build can start."""
    checks = {}

    ollama = shutil.which("ollama")
    checks["ollama_installed"] = {
        "ok": ollama is not None,
        "detail": ollama or "not found on PATH -- install from ollama.com",
    }

    checks["modelfile_present"] = {
        "ok": os.path.exists(MODELFILE),
        "detail": MODELFILE,
    }

    checks["knowledge_present"] = {
        "ok": os.path.exists(KNOWLEDGE),
        "detail": KNOWLEDGE if os.path.exists(KNOWLEDGE)
        else "run phase1_generate_knowledge.py first",
    }

    if ollama:
        try:
            listed = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=15)
            checks["base_model_pulled"] = {
                "ok": BASE_MODEL.split(":")[0] in listed.stdout,
                "detail": f"run: ollama pull {BASE_MODEL}",
            }
        except (subprocess.SubprocessError, OSError) as exc:
            checks["base_model_pulled"] = {"ok": False, "detail": str(exc)}
    else:
        checks["base_model_pulled"] = {"ok": False, "detail": "ollama missing"}

    checks["_all_ok"] = all(v["ok"] for k, v in checks.items()
                            if not k.startswith("_"))
    return checks


def compose_modelfile() -> str:
    """
    Fold the generated knowledge into the Modelfile's system prompt.

    Kept as a separate generated file so the hand-written Modelfile stays
    readable and reviewable in git.
    """
    with open(MODELFILE, encoding="utf-8") as handle:
        template = handle.read()

    with open(KNOWLEDGE, encoding="utf-8") as handle:
        knowledge = json.load(handle)

    lines = ["", "GROUNDED FACTS -- these are the only facts you may use:", ""]

    for entry in knowledge.get("physics", []):
        lines.append(f"- {entry['fact']} [{entry['source']}]")
    for entry in knowledge.get("components", []):
        lines.append(f"- {entry['fact']} [{entry['source']}]")

    injection = "\n".join(lines)

    # Splice the facts into the existing SYSTEM block, before its closing
    # triple quote.
    marker = '"""'
    last = template.rfind(marker)
    if last == -1:
        composed = template + '\n\nSYSTEM """' + injection + '"""\n'
    else:
        composed = template[:last] + injection + "\n" + template[last:]

    # Refusals go in as few-shot MESSAGE pairs, NOT as prose in the system
    # prompt.
    #
    # This matters more than it looks. With the refusals written as "Q: ... A:
    # ..." text, Mistral 7B read them as background reading and answered the
    # 7 nm question from its own priors -- it volunteered that "EUV systems
    # are typically capable of resolutions around or below 7 nm", which is
    # exactly the claim this project must never make. A 7B follows
    # demonstrated turns far more reliably than described rules, so the same
    # content delivered as conversation history holds where prose did not.
    exchanges = []
    for entry in knowledge.get("refusals", []):
        question = " ".join(entry["question"].split())
        answer = " ".join(entry["answer"].split())
        exchanges.append(f'MESSAGE user """{question}"""')
        exchanges.append(f'MESSAGE assistant """{answer}"""')

    if exchanges:
        composed += (
            "\n\n# Few-shot refusals. These are demonstrations, not examples\n"
            "# to paraphrase -- the model should answer these questions this\n"
            "# way verbatim.\n" + "\n".join(exchanges) + "\n"
        )

    return composed


def build() -> int:
    checks = check_prerequisites()

    print("Prerequisites")
    print("-" * 58)
    for name, check in checks.items():
        if name.startswith("_"):
            continue
        mark = "OK  " if check["ok"] else "FAIL"
        print(f"  [{mark}] {name}: {check['detail']}")
    print()

    if not checks["_all_ok"]:
        print("Cannot build. Resolve the failures above.")
        print()
        print("Typical first-time setup:")
        print("  1. Install Ollama from https://ollama.com")
        print(f"  2. ollama pull {BASE_MODEL}")
        print("  3. python phase1_generate_knowledge.py")
        print("  4. python phase2_finetune_local.py")
        return 1

    composed = compose_modelfile()
    with open(BUILD_MODELFILE, "w", encoding="utf-8") as handle:
        handle.write(composed)
    print(f"Composed {BUILD_MODELFILE} "
          f"({len(composed.splitlines())} lines including grounded facts)")

    print(f"Building {MODEL_NAME}...")
    try:
        result = subprocess.run(
            ["ollama", "create", MODEL_NAME, "-f", BUILD_MODELFILE],
            capture_output=True, text=True, timeout=900)
    except subprocess.SubprocessError as exc:
        print(f"Build failed: {exc}")
        return 1

    if result.returncode != 0:
        print("Build failed:")
        print(result.stderr)
        return 1

    print(f"Built {MODEL_NAME}")
    print()
    print("Verify with:")
    print(f'  ollama run {MODEL_NAME} "Can this machine reach 7 nm?"')
    print()
    print("Expected: a refusal explaining 14.3 nm at NA 0.33.")
    print("If it says yes, the system prompt is not being applied -- rebuild.")
    return 0


if __name__ == "__main__":
    sys.exit(build())
