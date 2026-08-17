"""
phase1_cloud_extract.py  --  Person C (AI Engineer)

PHASE 1 of the 3-phase architecture: extract general EUV knowledge from Claude.

    Run once. Needs internet. Never runs during the demo.

This is the only file in the project that talks to a remote host, and it exists
so the pitch's own claim is true end to end:

    "Use global knowledge -> train locally -> deploy locally -> keep data local"

The spec's security claim for this phase is that only textbook-level questions
leave the machine -- no project data, no experiment data, nothing
confidential. That claim is ENFORCED here, not asserted:

    * The questions are a fixed constant in this file. Nothing is templated
      from A's CSVs, from the optimizer, or from user input.
    * Every outgoing question is screened against a blocklist built LIVE from
      the project's own data -- supplier names, component names, component
      IDs, costs. If a question contains any of them, the run aborts before
      the socket opens.
    * --dry-run prints exactly what would be sent, so a judge can read the
      outbound payload without a network connection existing.

The screening matters because the failure it prevents is silent. If someone
later edits a question to say "why is our collector at 5 sr cheaper than
ASML's", that sentence leaks the project's design premise to a third party,
and nothing else in the codebase would notice.

Requires: pip install anthropic
          ANTHROPIC_API_KEY in the environment (or `ant auth login`)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(HERE)
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT = os.path.join(HERE, "claude_cloud_knowledge.json")

MODEL = "claude-opus-5"

SYSTEM_PROMPT = (
    "You are a semiconductor lithography reference. Answer at the level of a "
    "graduate textbook. Be precise and quantitative where the physics is "
    "settled, and say plainly when a figure is a range, is disputed, or is "
    "not publicly known. Answer in at most six sentences. Do not speculate "
    "about any specific company's internal designs or costs."
)

# Fixed list. Textbook physics only -- nothing here reveals what the project
# is building, what it costs, or who it would buy from.
QUESTIONS = [
    "What is the optimal wavelength for EUV lithography, and why was that "
    "wavelength chosen rather than a shorter one?",
    "How is efficiency loss calculated in a reflective optical system with "
    "many mirrors?",
    "What physical factors affect the reflectivity of a Mo/Si multilayer "
    "mirror at 13.5 nm?",
    "How does the Rayleigh criterion relate numerical aperture, wavelength "
    "and printable resolution in projection lithography?",
    "Why does depth of focus scale with the inverse square of numerical "
    "aperture, and what practical problem does that create?",
    "What determines the conversion efficiency of a laser-produced tin plasma "
    "EUV source?",
    "How is wafer throughput calculated from source power and exposure dose "
    "in a scanner?",
    "Why does EUV lithography require a vacuum environment?",
    "What is a killer defect in semiconductor lithography, and how does "
    "defect size relate to feature size?",
    "How does the ISO 14644-1 standard define cleanroom classes, and what is "
    "the formula?",
    "How is die yield estimated from defect density, and what assumptions "
    "does Murphy's model make?",
    "What causes contamination of an EUV collector mirror, and what "
    "mitigation methods are described in the literature?",
]


# ---------------------------------------------------------------------------
# Egress screening
# ---------------------------------------------------------------------------

def build_blocklist() -> dict:
    """
    Terms that must never appear in an outgoing question, derived live from
    the project's own data so the screen can't drift out of sync with it.
    """
    terms: set = set()
    sources: dict = {}

    components = os.path.join(DATA_DIR, "components.csv")
    if os.path.exists(components):
        with open(components, newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                for column in ("component_id", "name", "supplier", "component",
                               "option", "cost_usd", "cost_low_usd",
                               "cost_high_usd"):
                    value = (row.get(column) or "").strip()
                    if len(value) >= 4 and value.upper() not in (
                            "NONE", "TRUE", "FALSE", "MODELED", "UNSPECIFIED"):
                        terms.add(value.lower())
                        sources[value.lower()] = f"components.csv:{column}"

    # Project-identifying strings that would reveal intent even without data.
    for literal in ("hackverse", "sovereign technology for india",
                    "euv components optimizer", "our optimizer", "our design",
                    "our collector", "our machine", "our cost", "our budget",
                    "my-claude-local", "components.csv", "particle_limits",
                    "laser_experiments", "mirror_experiments",
                    "vacuum_experiments", "optimizer.py", "backend.py"):
        terms.add(literal)
        sources[literal] = "project identifier"

    return {"terms": terms, "sources": sources}


def screen(question: str, blocklist: dict) -> list:
    """Return every blocklist term found in this question."""
    lowered = question.lower()
    return sorted(
        {term for term in blocklist["terms"] if term and term in lowered})


def screen_all(questions: list) -> dict:
    """Screen the whole batch. Nothing is sent unless this passes cleanly."""
    blocklist = build_blocklist()
    violations = []

    for index, question in enumerate(questions):
        hits = screen(question, blocklist)
        if hits:
            violations.append({
                "index": index,
                "question": question,
                "leaked_terms": hits,
                "sources": [blocklist["sources"].get(h, "?") for h in hits],
            })

    return {
        "clean": not violations,
        "questions_checked": len(questions),
        "blocklist_size": len(blocklist["terms"]),
        "violations": violations,
    }


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract(questions: list, model: str = MODEL) -> dict:
    """Ask Claude the generic questions and record the answers."""
    try:
        import anthropic
    except ImportError:
        print("anthropic SDK not installed.  pip install anthropic")
        raise SystemExit(1)

    client = anthropic.Anthropic()
    answers = []

    for index, question in enumerate(questions, 1):
        print(f"  [{index}/{len(questions)}] {question[:64]}...")

        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                thinking={"type": "adaptive"},
                output_config={"effort": "medium"},
                messages=[{"role": "user", "content": question}],
            )
        except anthropic.RateLimitError:
            print("      rate limited -- stopping, partial results kept")
            break
        except anthropic.AuthenticationError:
            print("      no valid credentials.  Set ANTHROPIC_API_KEY or run "
                  "`ant auth login`")
            raise SystemExit(1)
        except anthropic.APIStatusError as exc:
            print(f"      API error {exc.status_code}: {exc.message}")
            continue
        except anthropic.APIConnectionError as exc:
            print(f"      connection failed: {exc}")
            break

        if response.stop_reason == "refusal":
            print("      declined by safety classifiers -- skipped")
            continue

        text = "\n".join(block.text for block in response.content
                         if block.type == "text").strip()
        if not text:
            continue

        answers.append({
            "question": question,
            "answer": text,
            "model": response.model,
            "source": "claude-cloud-phase1",
            "confidence": "MEDIUM",
            "note": "General physics from a frontier model. Not a citation. "
                    "Where it conflicts with A's sourced data, A's data wins.",
        })

    return {
        "_generated_by": "phase1_cloud_extract.py",
        "_purpose": "General EUV knowledge extracted once from Claude. "
                    "Phase 1 of the 3-phase local architecture.",
        "_egress_note": "Only the fixed generic questions in this file left "
                        "the machine. No project data, component data, "
                        "experiment data or user input was transmitted.",
        "_model": model,
        "_count": len(answers),
        "answers": answers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="screen and print the questions, send nothing")
    parser.add_argument("--check", action="store_true",
                        help="run the egress screen only, then exit")
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()

    print("=" * 70)
    print("  PHASE 1 -- CLOUD KNOWLEDGE EXTRACTION")
    print("=" * 70)
    print("  This is the ONLY step that uses the internet.")
    print("  It runs once, before the demo, and never during it.\n")

    report = screen_all(QUESTIONS)
    print(f"  egress screen: {report['questions_checked']} questions vs "
          f"{report['blocklist_size']} blocked terms")

    if not report["clean"]:
        print("\n  ABORTED -- a question contains project data:\n")
        for violation in report["violations"]:
            print(f"    Q{violation['index']}: {violation['question'][:60]}")
            for term, origin in zip(violation["leaked_terms"],
                                    violation["sources"]):
                print(f"      leaked {term!r} (from {origin})")
        print("\n  Nothing was sent. Fix the questions and re-run.")
        return 1

    print("  PASS -- no project data in any outgoing question\n")

    if args.check:
        return 0

    if args.dry_run:
        print("  Exact payload that would be sent:\n")
        print(f"  system: {SYSTEM_PROMPT}\n")
        for index, question in enumerate(QUESTIONS, 1):
            print(f"  {index:>2}. {question}")
        print(f"\n  {len(QUESTIONS)} requests to api.anthropic.com, "
              f"model {args.model}")
        print("  Nothing was sent (--dry-run).")
        return 0

    if not (os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("  No ANTHROPIC_API_KEY in the environment.")
        print("  Set it, or run `ant auth login`, then re-run.")
        print("  Use --dry-run to inspect the payload without credentials.")
        return 1

    print("  Sending...\n")
    knowledge = extract(QUESTIONS, args.model)

    with open(OUTPUT, "w", encoding="utf-8") as handle:
        json.dump(knowledge, handle, indent=2)

    print(f"\n  Wrote {knowledge['_count']} answers -> {OUTPUT}")
    print("  Now run phase1_generate_knowledge.py to merge these with A's "
          "sourced data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
