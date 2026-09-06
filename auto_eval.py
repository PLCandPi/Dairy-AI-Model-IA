#!/usr/bin/env python3
"""Automated post-training check. Runs held-out questions through the
fine-tuned model and checks each answer against known facts pulled from the
real source material used to draft that topic's training data (PMO,
AIMS module manual, etc) - the model is never asked to grade itself, only
matched against ground truth gathered independently.

Not a substitute for reading the answers (see compare_eval.py) - a fast
first pass to catch obvious regressions/confabulation, and to tell you
which topics need more or better training data. Anything flagged should go
back into TOPICS.md as a "needs work" item, not be auto-corrected - only a
person (or the next research round) should decide what the fix actually is.
"""
import json
from datetime import datetime, timezone

from eval_common import generate, load_model

# Each check's "any_of" list is an OR - the answer only needs to contain one
# of the listed phrasings. All checks in a case must hit for it to pass.
# red_flags are known-wrong phrasings seen in past confabulation - any hit
# fails the case regardless of the checks above.
EVAL_CASES = [
    {
        "topic": "analog_io_seed",
        "question": (
            "An analog input module reports a channel's raw process value as "
            "+32767, and it never changes even while other channels update "
            "normally. What does that mean?"
        ),
        "checks": [
            ["32767"],
            ["sensor open", "disconnected", "open circuit", "no sensor"],
        ],
        "red_flags": ["32767 degrees", "3276.7", "3,276.7"],
    },
    {
        "topic": "analog_io_seed",
        "question": "What's the purpose of hysteresis on an alarm setpoint?",
        "checks": [
            ["chatter", "flap", "oscillat", "rapid"],
            ["dead band", "deadband", "hysteresis"],
        ],
        "red_flags": [],
    },
    {
        "topic": "pmo_regulatory_seed",
        "question": (
            "What temperature and hold time does the FDA PMO require for "
            "standard continuous-flow HTST pasteurization of milk?"
        ),
        "checks": [["72"], ["161"], ["15 second", "15s", "15-second"]],
        "red_flags": [],
    },
    {
        "topic": "pmo_regulatory_seed",
        "question": (
            "Why is a pasteurizer's holding tube sized for the fastest "
            "particle rather than the average flow rate?"
        ),
        "checks": [["laminar"], ["twice", "2x", "double", "two times"]],
        "red_flags": [],
    },
    {
        "topic": "pmo_regulatory_seed",
        "question": (
            "How far upstream of the Flow Diversion Device can its "
            "temperature sensor be located, per the FDA PMO?"
        ),
        "checks": [["46", "18 inch", '18"', "18-inch"]],
        "red_flags": [],
    },
    {
        "topic": "heatwatch_codebase_seed",
        "question": (
            "Two RTD sensors on the same plate heat exchanger start "
            "drifting in opposite directions over a few weeks. What does "
            "that suggest?"
        ),
        "checks": [
            ["one", "single", "individually", "independent"],
            ["fail", "faulty", "drift", "calibrat"],
        ],
        "red_flags": [],
    },
]


def check_answer(answer, case):
    low = answer.lower()
    hit_flags = [f for f in case["red_flags"] if f.lower() in low]
    check_results = [
        {"any_of": group, "matched": any(alt.lower() in low for alt in group)}
        for group in case["checks"]
    ]
    passed = all(r["matched"] for r in check_results) and not hit_flags
    return passed, check_results, hit_flags


def main():
    print("Loading fine-tuned model")
    model, tokenizer = load_model()

    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "results": []}
    for case in EVAL_CASES:
        answer = generate(model, tokenizer, case["question"], max_new_tokens=250)
        passed, check_results, hit_flags = check_answer(answer, case)
        report["results"].append({
            "topic": case["topic"],
            "question": case["question"],
            "answer": answer,
            "passed": passed,
            "checks": check_results,
            "red_flags_hit": hit_flags,
        })
        print(f"[{'PASS' if passed else 'FLAG'}] ({case['topic']}) {case['question'][:70]}...")

    with open("eval_report.json", "w") as f:
        json.dump(report, f, indent=2)

    flagged = [r for r in report["results"] if not r["passed"]]
    print(f"\n{len(flagged)}/{len(report['results'])} flagged - see eval_report.json for full answers")
    if flagged:
        print("Flagged topics (candidates for TOPICS.md 'needs work'):")
        for r in flagged:
            print(f"  - {r['topic']}: {r['question'][:80]}")


if __name__ == "__main__":
    main()
