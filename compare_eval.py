#!/usr/bin/env python3
"""Side-by-side base vs fine-tuned comparison on held-out questions -
none of these appear verbatim in data/*.jsonl. Manual read, not a metric:
the point is to see whether the adapter changed anything meaningful."""
import argparse

from eval_common import generate, load_model

HELD_OUT_QUESTIONS = [
    "The dashboard's manual-test override for the relay is active, and the "
    "milk outlet reads 40C for over ten minutes. Will the physical alarm "
    "relay actually trigger? Why or why not?",

    "Two RTD sensors on the same plate heat exchanger start drifting in "
    "opposite directions over a few weeks. What does that suggest, and how "
    "would it show up in the historical temperature trend?",

    "Why doesn't raising the acid wash temperature setpoint reduce "
    "microbial risk the same way extending the HTST holding time does?",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--adapter-dir", default="output/adapter_final",
        help="Path to a specific adapter/checkpoint, e.g. output/checkpoint-120",
    )
    args = parser.parse_args()

    print(f"Loading base + fine-tuned model from {args.adapter_dir}")
    model, tokenizer = load_model(adapter_dir=args.adapter_dir)

    for q in HELD_OUT_QUESTIONS:
        print("\n" + "=" * 100)
        print("Q:", q)
        print("-" * 100)
        with model.disable_adapter():
            print("[BASE]  ", generate(model, tokenizer, q))
        print("-" * 100)
        print("[TUNED] ", generate(model, tokenizer, q))


if __name__ == "__main__":
    main()
