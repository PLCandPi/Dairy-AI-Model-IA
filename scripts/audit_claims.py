#!/usr/bin/env python3
"""Heuristic claim_type consistency checker for data/*.jsonl and
data/pending/*.jsonl entries carrying the {metadata: {claim_type}} schema.

This is NOT a truth oracle - it can't check an answer against the actual
standard/manual/codebase text on its own (see scripts in this repo's
history for examples of that verification actually being done by hand).
What it CAN catch: wording that reads as an unqualified, absolute
requirement ("the standard requires", "always", "never") tagged as one of
the softer claim_types (interpretation, comparison_inference,
engineering_rationale, derived_from_standard, common_practice) - probably
under-tagged, the claim sounds more certain than its label - and the
reverse: wording that reads as hedged/uncertain ("typically", "commonly",
"worth verifying") tagged as one of the high-confidence claim_types
(explicit_requirement, explicit_standard_concept,
mixed_requirement_and_rationale, failure_mode_analysis) - probably
over-tagged, the label claims more certainty than the text itself does.

Flags are prompts for a human to look again, not failures. The point is
catching entries where the *label* and the *wording* disagree with each
other - that mismatch is exactly what lets a model learn "this is a
universal rule" from something that was actually hedged as one engineer's
interpretation, or vice versa.
"""
import glob
import json
import sys

ABSOLUTE_MARKERS = [
    "the standard requires", "the standard defines", "the standard specifies",
    "always", "never", "must ", "only ever", "is required to",
]
HEDGE_MARKERS = [
    "typically", "commonly", "often", "in practice", "worth verifying",
    "worth checking", "widely-used", "widely used", "maps closest to",
    "commonly called", "design intent", "may ", "can also", "generally",
]

# claim_type values where confident/absolute wording is expected, because the
# claim is grounded in something verified (a quoted requirement, the
# standard's own stated rationale, or a traced failure-mode analysis) -
# distinct from the "softer" categories (interpretation, comparison_inference,
# engineering_rationale, derived_from_standard, common_practice) where
# unhedged absolute wording is more likely to be overclaiming.
HIGH_CONFIDENCE_CLAIM_TYPES = {
    "explicit_requirement",
    "explicit_standard_concept",
    "explicit_standard_rationale",
    "mixed_requirement_and_rationale",
    "requirement_with_exception",
    "failure_mode_analysis",
}


def load_entries(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def check_entry(entry):
    meta = entry.get("metadata")
    if not meta or "claim_type" not in meta:
        return None  # not using this schema - nothing to check
    claim_type = meta["claim_type"]
    text = (entry.get("output", "") + " " + entry.get("reasoning_summary", "")).lower()

    has_absolute = any(m in text for m in ABSOLUTE_MARKERS)
    has_hedge = any(m in text for m in HEDGE_MARKERS)
    is_high_confidence = claim_type in HIGH_CONFIDENCE_CLAIM_TYPES

    if not is_high_confidence and has_absolute and not has_hedge:
        return "under-tagged? reads as an unqualified rule but tagged '%s'" % claim_type
    if is_high_confidence and has_hedge and not has_absolute:
        return "over-tagged? reads as hedged/uncertain but tagged '%s'" % claim_type
    return None


def main():
    paths = sys.argv[1:] or (
        glob.glob("data/*.jsonl") + glob.glob("data/pending/*.jsonl")
    )
    total_checked, total_flagged = 0, 0
    by_claim_type = {}

    for path in sorted(paths):
        entries = load_entries(path)
        file_flags = []
        for i, entry in enumerate(entries, 1):
            meta = entry.get("metadata")
            if not meta or "claim_type" not in meta:
                continue
            total_checked += 1
            by_claim_type.setdefault(meta["claim_type"], 0)
            by_claim_type[meta["claim_type"]] += 1
            note = check_entry(entry)
            if note:
                total_flagged += 1
                file_flags.append((i, entry["instruction"][:80], note))

        if file_flags:
            print(f"\n=== {path} ===")
            for lineno, instr, note in file_flags:
                print(f"  line {lineno}: {note}")
                print(f"    {instr}...")

    print(f"\n{total_checked} entries carry claim_type metadata; {total_flagged} flagged for a look.")
    print("By claim_type:", by_claim_type)
    print(
        "\nReminder: this only checks wording-vs-label consistency, not "
        "correctness against the actual standard. High-confidence claim_types "
        f"({', '.join(sorted(HIGH_CONFIDENCE_CLAIM_TYPES))}) are the "
        "highest-stakes bucket - review those first."
    )


if __name__ == "__main__":
    main()
