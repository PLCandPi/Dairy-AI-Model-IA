#!/usr/bin/env python3
"""Validates data/pending/*.jsonl batches before a human decides to merge
them into data/. Checks schema, flags entries missing a "think" field (see
README's note on why that field matters), and flags likely-duplicate
instructions against what's already in data/*.jsonl. Doesn't move or delete
anything - that's a manual step, on purpose."""
import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
PENDING_DIR = os.path.join(DATA_DIR, "pending")
ALLOWED_KEYS = {"instruction", "input", "think", "output"}
DUPLICATE_THRESHOLD = 0.7


def load_jsonl(path):
    entries = []
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append((lineno, json.loads(line)))
            except json.JSONDecodeError as e:
                entries.append((lineno, e))
    return entries


def existing_instructions():
    instructions = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.jsonl"))):
        for _, entry in load_jsonl(path):
            if isinstance(entry, dict) and "instruction" in entry:
                instructions.append((os.path.basename(path), entry["instruction"]))
    return instructions


def word_set(text):
    return set(re.findall(r"\w+", text.lower()))


def most_similar(instruction, existing):
    # Containment (overlap / smaller set) rather than a symmetric ratio -
    # a short instruction fully contained in a longer, differently-phrased
    # one should still flag, which plain SequenceMatcher on raw characters
    # misses whenever one side has extra clauses the other doesn't.
    words = word_set(instruction)
    best = (None, None, 0.0)
    for source_file, other in existing:
        other_words = word_set(other)
        smaller = min(len(words), len(other_words)) or 1
        overlap = len(words & other_words) / smaller
        if overlap > best[2]:
            best = (source_file, other, overlap)
    return best


def main():
    pending_files = sorted(glob.glob(os.path.join(PENDING_DIR, "*.jsonl")))
    if not pending_files:
        print("No pending batches in data/pending/.")
        return

    existing = existing_instructions()
    any_issues = False

    for path in pending_files:
        print(f"\n=== {os.path.relpath(path, REPO_ROOT)} ===")
        entries = load_jsonl(path)
        valid, no_think, issues = 0, 0, 0

        for lineno, entry in entries:
            if isinstance(entry, Exception):
                print(f"  line {lineno}: INVALID JSON - {entry}")
                issues += 1
                continue

            extra_keys = set(entry.keys()) - ALLOWED_KEYS
            if extra_keys:
                print(f"  line {lineno}: unexpected keys {extra_keys}")
                issues += 1
            if not entry.get("instruction") or not entry.get("output"):
                print(f"  line {lineno}: missing instruction or output")
                issues += 1
                continue
            if not entry.get("think"):
                print(f"  line {lineno}: no 'think' field - trains an empty reasoning block")
                no_think += 1

            source_file, similar, ratio = most_similar(entry["instruction"], existing)
            if ratio >= DUPLICATE_THRESHOLD:
                print(f"  line {lineno}: {ratio:.0%} similar to an instruction already in {source_file}")
                print(f"    existing: {similar[:100]}")
                issues += 1

            valid += 1

        print(f"  {valid} parseable entries, {no_think} missing 'think', {issues} flagged issues")
        if issues:
            any_issues = True

    if any_issues:
        print("\nSome entries need a look before merging - see flags above.")
        sys.exit(1)
    print("\nNo blocking issues found. Still read the content before merging - this only checks structure.")


if __name__ == "__main__":
    main()
