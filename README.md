# Dairy AI Model

A LoRA fine-tuning pipeline that specializes a small model (`Qwen/Qwen3-0.6B`)
into a **dairy plant monitoring systems assistant** - trained on real HTST
pasteurization/CIP domain knowledge, real industrial automation standards
(ISA-88, ISA-18.2, the FDA Pasteurized Milk Ordinance), and one real codebase
([HeatWatch](https://github.com/PLCandPi/HeatWatch-Kattapana-Milma)).

## What this is - and isn't

- It reads code and operational context and suggests what might be going on
  and what a code-level fix could look like. **Advisory only.** It never
  edits files, restarts services, or touches any actuator/relay itself -
  every suggestion is meant to be reviewed by a person before anything
  changes on a real system.
- It's seeded with real domain knowledge and one real codebase, not a
  "universal" model that understands any dairy plant out of the box.
  Fine-tuning on a small base model raises its familiarity with this domain
  and codebase - it does not turn it into a large-model-class code reasoner.
  Treat its output as a fast first-pass opinion, not a verdict.

## Model

`Qwen/Qwen3-0.6B` - originally chosen to fit a phone's available RAM
(~2.6-2.8GB) for on-device training with LoRA + gradient checkpointing, back
when this project trained natively on Android/Termux. On-device training is
now dropped in favor of Colab (below), but the small model size is kept:
it's cheap and fast to iterate on, and the point is a focused domain
specialist, not a general-purpose large-model-class reasoner.

## Quick start (Colab)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/PLCandPi/Dairy-AI-Model-IA/blob/main/colab_train.ipynb)

`Runtime -> Change runtime type -> T4 GPU`, then `Runtime -> Run all`.
Clones this repo, installs dependencies, trains (`train.py` auto-detects
CUDA and switches to fp16 - minutes instead of hours), then zips and
downloads the trained adapter to your machine. Trade-off: your data leaves
the device and the runtime is ephemeral - nothing persists once it
disconnects, so run the last cell before closing the tab.

## On-device (Termux) - dropped, kept for reference

This project originally trained natively on a phone via Termux, CPU-only, no
training GPU support on that hardware (Adreno 612 GPU can accelerate
inference via llama.cpp/Ollama, but there's no confirmed way to use it for
backprop/training). That path is no longer actively developed - Colab is
strictly faster and skips an entire category of Android/Termux-specific
build issues (see `SETUP_STATUS.md` for what those were). `setup_termux.sh`
and `train.py`'s CPU/fp32 fallback still work if you want to resume it:

```bash
bash setup_termux.sh
python train.py
```

`train.py` has no required arguments either way - it loads every `.jsonl`
file under `data/`, LoRA fine-tunes the base model, and saves the adapter to
`output/adapter_final/`. Resumable by design: checkpoints every 20 steps to
`output/`, and just re-running `train.py` picks up from the last checkpoint.

## Data

`data/*.jsonl`, each line:

```json
{
  "instruction": "...", "input": "",
  "think": "...", "reasoning_summary": "...",
  "output": "...",
  "metadata": {
    "domain": "...", "standard": "...",
    "category": "...", "difficulty": "...",
    "claim_type": "see TOPICS.md's Data schema section for the full taxonomy"
  }
}
```

`think` is required in practice, not just optional: Qwen3's chat template
always wraps the assistant's reply in a `<think>...</think>` block, empty
if `think` isn't supplied - training on an empty one teaches the model to
suppress its own reasoning rather than use it. `reasoning_summary` carries
the same content under a name that isn't tied to chat-template mechanics.

`metadata.claim_type` matters most: it's what stops the model from learning
"this is how ISA-18.2 works" when the honest lesson is "this is one
reasonable way engineers implement it." See `TOPICS.md`'s "Data schema"
section for the exact decision tree, and `scripts/audit_claims.py` for the
heuristic checker that flags wording/label mismatches.

- `dairy_domain_seed.jsonl` - HTST pasteurization and CIP process knowledge
  (setpoints, cycle stages, common fault modes, sensor behavior).
- `heatwatch_codebase_seed.jsonl` - scenarios grounded in the actual
  HeatWatch poller/dashboard code: its Chilling Failed Detector logic and
  known rough edges, config validation gaps, resilience behavior.
- `analog_io_seed.jsonl` - sourced from the PPI AIMS-4X/8X analog input
  module manual (Modbus sentinel values, alarm hysteresis, RTD wiring, IIR
  filtering, cold-junction compensation).
- `pmo_regulatory_seed.jsonl` - sourced from the FDA Grade "A" Pasteurized
  Milk Ordinance (exact HTST temp/time table, FDD behavior and placement,
  holding tube sizing/slope, thermal-limit-controller sealing).
- `isa_standards_seed.jsonl` - ISA-88 (physical/procedural model, phase-to-
  control-module relationship) and ISA-18.2 (alarm/alert/prompt/message,
  rationalization, alarms vs. interlocks, suppression, latching).
- `computerized_systems_seed.jsonl` and `appendix_hvi_part2_seed.jsonl` -
  FDA PMO Appendix H.VI, computerized/PLC-based public-health controls
  (dedicated computers, fail-safe behavior, sealed programming/reprogramming,
  LOSA/HFA/PDD, scan-cycle timing, CIP-mode interlocks).
- `batch_vs_htst_seed.jsonl` - why batch and continuous-flow HTST
  pasteurization need structurally different control mechanisms.

Add more `.jsonl` files here as real incidents/fixes accumulate - that's
more valuable than anything synthetic, and the loader picks up every file
in the directory automatically.

## Growing the dataset

There's no script that autonomously "scours the web and trains itself" -
turning raw source material into good `{instruction, think, output}`
entries takes judgment, not just fetching. The realistic split:

1. **Research + draft** (a person, or an AI assistant with web search/fetch
   - not a standalone script): pick a topic from `TOPICS.md`, find primary
   sources, draft candidate entries grounded in real quoted facts, write
   them to `data/pending/<topic>.jsonl`.
2. **Validate** - `python scripts/review_pending.py` checks structure (valid
   JSON, no missing `think` field, no near-duplicate of something already in
   `data/`). Mechanical only - it doesn't judge correctness.
3. **Audit** - `python scripts/audit_claims.py` flags entries whose wording
   sounds more (or less) certain than their `metadata.claim_type` label
   claims. Heuristic, not a truth check - it can't verify a claim against
   the actual standard text, only catch label/wording disagreement. Verify
   any specific factual claim (device specs, code behavior, regulatory
   text) against its actual source before trusting it - this project's own
   audit caught real misattributions exactly this way.
4. **Review + merge** - a person reads the batch, then moves it:
   `mv data/pending/<file>.jsonl data/<file>.jsonl`.
5. **Retrain**, then **`python auto_eval.py`** - runs a fixed set of
   held-out questions through the model and checks answers against known
   facts from the source material (not the model grading itself). Flags
   regressions/confabulation into `eval_report.json`; flagged topics go back
   into `TOPICS.md` as "needs work" for the next research round.

`compare_eval.py` stays the manual side-by-side check (see below) -
`auto_eval.py` is a fast automatable tripwire, not a replacement for
actually reading the answers.

## Why fp32 on CPU, fp16 on GPU, and this LoRA setup

- `train.py` auto-detects CUDA: fp16 on a training-capable GPU (Colab),
  plain fp32 on CPU-only aarch64 builds (phone) - no confirmed
  `bitsandbytes` quantization support there, so no QLoRA-style setup on that
  path.
- `gradient_checkpointing` + `enable_input_require_grads()` are both
  required together - checkpointing alone silently breaks gradient flow
  through a frozen base model with a LoRA adapter on top.
- LoRA targets Qwen3's attention + MLP projection layers
  (`q/k/v/o_proj`, `gate/up/down_proj`) - the standard target set for this
  architecture family.
