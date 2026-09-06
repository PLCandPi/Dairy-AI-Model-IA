# Pending review

Draft `.jsonl` batches land here after a research round (web search + real
source material, drafted into `{instruction, input, think, output}`
entries) - `train.py`'s loader only reads `data/*.jsonl` directly, not this
subdirectory, so nothing here trains until a person moves it up a level.

Review with `python scripts/review_pending.py`, then either:

- Looks good: `mv data/pending/<file>.jsonl data/<file>.jsonl`, commit, retrain.
- Needs edits: edit in place, re-run the review script, then move.
- Reject: delete it.

Never move a file here directly into `data/` without reading it first - the
whole point of this folder is that a batch is draft until a person has
actually looked at it.
