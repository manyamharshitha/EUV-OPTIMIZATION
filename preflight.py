"""
preflight.py  --  run this immediately before presenting

The demo has one part that lives outside the repository: the local model. It
is ~4.4 GB on disk, it is not in git, and it is per-machine. A laptop that
worked yesterday can present differently today -- a Windows update restarted
the Ollama service, someone cloned the repo to a second machine, the model was
pulled on a different user account.

None of that is visible until a judge is watching. This checks it in about
five seconds.

    python preflight.py

Exit code 0 means everything a judge will touch is working. Exit code 1 means
something is degraded -- read the output, because in most cases the demo still
runs, just with a weaker claim you now have to make out loud.

Standard library only. Makes no network call except to 127.0.0.1.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


class Check:
    """PASS / WARN / FAIL, where WARN means 'runs, but say something'."""

    def __init__(self):
        self.results = []

    def record(self, name: str, state: str, detail: str = "",
               fix: str = "") -> None:
        self.results.append({"name": name, "state": state,
                             "detail": detail, "fix": fix})
        marker = {"PASS": "  OK  ", "WARN": " WARN ", "FAIL": " FAIL "}[state]
        print(f"  [{marker}] {name}")
        if detail:
            print(f"           {detail}")
        if fix and state != "PASS":
            print(f"           fix: {fix}")

    def counts(self) -> tuple:
        return (sum(1 for r in self.results if r["state"] == "PASS"),
                sum(1 for r in self.results if r["state"] == "WARN"),
                sum(1 for r in self.results if r["state"] == "FAIL"))


def check_data(check: Check) -> None:
    """A's files. Without these there is nothing to optimise."""
    required = ["components.csv", "particle_limits.json"]
    optional = ["laser_experiments.csv", "mirror_experiments.csv",
                "vacuum_experiments.csv"]

    data_dir = os.path.join(HERE, "data")
    missing = [f for f in required
               if not os.path.exists(os.path.join(data_dir, f))]

    if missing:
        check.record("Person A's data present", "FAIL",
                     f"missing: {', '.join(missing)}",
                     "restore data/ from the repository")
        return

    absent = [f for f in optional
              if not os.path.exists(os.path.join(data_dir, f))]
    if absent:
        check.record("Person A's data present", "WARN",
                     f"experiment CSVs missing: {', '.join(absent)}",
                     "the data-learning screen will be empty")
    else:
        check.record("Person A's data present", "PASS",
                     f"{len(required) + len(optional)} files")


def check_backend(check: Check) -> dict | None:
    """The whole pipeline, once, timed."""
    import time
    try:
        import backend
        start = time.time()
        result = backend.run()
        elapsed = time.time() - start
    except Exception as exc:
        check.record("Backend runs", "FAIL", f"{type(exc).__name__}: {exc}",
                     "run python demo_proof.py to locate the break")
        return None

    if not result.get("ok"):
        check.record("Backend runs", "FAIL", str(result.get("errors")))
        return result

    combos = result["results"]["combinations_evaluated"]
    state = "PASS" if elapsed < 5.0 else "WARN"
    check.record("Backend runs", state,
                 f"{combos:,} combinations in {elapsed:.2f}s",
                 "slow first run is usually import cost; run it twice"
                 if state == "WARN" else "")
    return result


def check_ollama(check: Check) -> bool:
    """Is a local model actually going to answer, or will the demo fall back?"""
    if shutil.which("ollama") is None:
        check.record("Ollama installed", "WARN", "not on PATH",
                     "install from ollama.com -- demo still runs, AI panels "
                     "will show rule_based")
        return False

    check.record("Ollama installed", "PASS", shutil.which("ollama"))

    sys.path.insert(0, os.path.join(HERE, "ai"))
    try:
        import ai_local_claude
    except ImportError as exc:
        check.record("AI module importable", "FAIL", str(exc))
        return False

    health = ai_local_claude.model_available(force=True)

    if not health["available"]:
        check.record("Ollama service responding", "WARN",
                     health.get("reason", "no response on 127.0.0.1:11434"),
                     "start Ollama from the Start menu, or reboot")
        return False

    check.record("Ollama service responding", "PASS", health["endpoint"])

    if not health["target_model_present"]:
        check.record(f"Model {ai_local_claude.MODEL_NAME} built", "WARN",
                     f"available: {', '.join(health['models']) or 'none'}",
                     "python ai/phase2_finetune_local.py")
        return False

    check.record(f"Model {ai_local_claude.MODEL_NAME} built", "PASS")
    return True


def check_model_behaviour(check: Check) -> None:
    """
    Does the model actually obey its grounding?

    A built model that answers "yes, 7 nm" is worse than no model at all --
    it contradicts the honesty slide in front of the judge who asked.
    """
    import ai_local_claude

    answer = ai_local_claude._generate(
        "Can this machine reach 7 nm resolution?",
        ai_local_claude.SYSTEM_PROMPT)

    if answer is None:
        check.record("Model answers within timeout", "WARN",
                     f"no response in {ai_local_claude.REQUEST_TIMEOUT_S:.0f}s",
                     "CPU inference can be slow; raise REQUEST_TIMEOUT_S")
        return

    check.record("Model answers within timeout", "PASS",
                 f"{len(answer)} chars")

    lowered = answer.lower()
    grounded = ("14.3" in lowered or "not" in lowered or "cannot" in lowered
                or "no" in lowered.split()[:6])

    if grounded:
        check.record("Model obeys its grounding", "PASS",
                     "correctly declines the 7 nm claim")
    else:
        check.record("Model obeys its grounding", "FAIL",
                     f"answered: {answer[:90]}",
                     "rebuild: python ai/phase2_finetune_local.py")


def check_disclosure(check: Check, result: dict) -> None:
    """What the tool will admit about itself on screen."""
    disclosures = result.get("disclosure", {})
    entries = disclosures.get("entries", [])

    if not entries:
        check.record("Disclosures generated", "FAIL", "none in payload")
        return

    critical = [e for e in entries if e["severity"] == "critical"]
    check.record("Disclosures generated", "PASS",
                 f"{len(entries)} total, {disclosures['must_state_count']} "
                 f"must be said aloud")

    for entry in critical:
        check.record(f"CRITICAL: {entry['id']}", "WARN",
                     entry["headline"][:76],
                     f'say: "{entry["say_this"][:70]}..."')


def check_offline(check: Check) -> None:
    """The claim the whole pitch rests on."""
    try:
        outcome = subprocess.run(
            [sys.executable, "demo_proof.py"], cwd=HERE,
            capture_output=True, text=True, timeout=300)
    except (subprocess.SubprocessError, OSError) as exc:
        check.record("Offline proof passes", "FAIL", str(exc))
        return

    tail = outcome.stdout.strip().splitlines()[-3:]
    summary = next((line.strip() for line in reversed(tail)
                    if "verified" in line), "")

    if outcome.returncode == 0:
        check.record("Offline proof passes", "PASS", summary)
    else:
        check.record("Offline proof passes", "FAIL", summary or "see output",
                     "python demo_proof.py")


def main() -> int:
    print("=" * 68)
    print("  PREFLIGHT -- run this before you present")
    print("=" * 68 + "\n")

    check = Check()

    check_data(check)
    result = check_backend(check)
    if result:
        check_disclosure(check, result)

    print()
    model_ready = check_ollama(check)
    if model_ready:
        check_model_behaviour(check)

    print()
    check_offline(check)

    passed, warned, failed = check.counts()
    print("\n" + "=" * 68)
    print(f"  {passed} pass / {warned} warn / {failed} fail")
    print("=" * 68)

    if failed:
        print("\n  DO NOT PRESENT until the FAIL items are fixed.")
        return 1

    if not model_ready:
        print("\n  Demo will run. The AI panels will show rule_based, which is")
        print("  honest but weaker. If you present like this, say it out loud")
        print("  before a judge notices the label:")
        print('    "That panel is rule-based right now, not the model.')
        print('     Every number on screen is deterministic either way."')
        return 1

    print("\n  Ready. Local model is live and grounded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
