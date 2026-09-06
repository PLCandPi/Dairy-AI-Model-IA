# Termux LLM Training

A LoRA fine-tuning pipeline that runs natively on a phone (Termux, CPU-only,
no training GPU support on this hardware) to specialize a small model into a
**dairy plant monitoring systems assistant**.

## What this is - and isn't

- It reads code and operational context and suggests what might be going on
  and what a code-level fix could look like. **Advisory only.** It never
  edits files, restarts services, or touches any actuator/relay itself -
  every suggestion is meant to be reviewed by a person before anything
  changes on a real system.
- It's seeded with real HTST pasteurization / CIP domain knowledge and one
  real codebase ([HeatWatch](https://github.com/PLCandPi/HeatWatch-Kattapana-Milma)),
  not a "universal" model that understands any dairy plant out of the box.
  Fine-tuning on a small base model raises its familiarity with this
  domain and codebase - it does not turn it into a large-model-class code
  reasoner. Treat its output as a fast first-pass opinion, not a verdict.
- Training happens on-device, CPU-only. There is no confirmed way to use
  this phone's GPU (Adreno 612, Snapdragon 675) for training - only
  inference frameworks (llama.cpp/Ollama via Vulkan) accelerate on it.

## Model

`Qwen/Qwen3-0.6B` - chosen specifically to fit this phone's available RAM
(~2.6-2.8GB) for real backprop training with LoRA + gradient checkpointing.
`1.7B` was tried and is too tight for training (fine for inference-only use
via Ollama, not for holding gradients/activations too).

## Quick start (Termux)

```bash
bash setup_termux.sh
python train.py
```

That's it - `train.py` has no required arguments. It loads every `.jsonl`
file under `data/`, LoRA fine-tunes the base model, and saves the adapter to
`output/adapter_final/`.

**Resumable by design**: training checkpoints every 20 steps to `output/`.
If the process gets killed (phone reboot, Termux backgrounded and killed by
Android, app force-closed), just run `python train.py` again - it detects
the last checkpoint and continues from there automatically.

## Quick start (Colab)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/PLCandPi/Termux-LLM-Training/blob/main/colab_train.ipynb)

Same `train.py`, run on a GPU runtime instead of the phone - no Termux/Android
build issues, and minutes instead of hours. `train.py` auto-detects CUDA and
switches to fp16; nothing else to configure. Trade-off: your data leaves the
device and the runtime is ephemeral, so the last notebook cell zips and
downloads the trained adapter before the session disconnects.

## Data

`data/*.jsonl`, each line `{"instruction": ..., "input": ..., "output": ..., "think": ...}`.
`think` is optional but strongly recommended: Qwen3's chat template always
wraps the assistant's reply in a `<think>...</think>` block, empty if
`think` isn't supplied - training on an empty one teaches the model to
suppress its own reasoning rather than use it. Populate `think` with the
real step-by-step reasoning that should lead to `output`.

- `dairy_domain_seed.jsonl` - HTST pasteurization and CIP process knowledge
  (setpoints, cycle stages, common fault modes, sensor behavior).
- `heatwatch_codebase_seed.jsonl` - scenarios grounded in the actual
  HeatWatch poller/dashboard code: its Chilling Failed Detector logic and
  known rough edges, config validation gaps, resilience behavior.

Add more `.jsonl` files here as real incidents/fixes accumulate - that's
more valuable than anything synthetic, and the loader picks up every file
in the directory automatically.

## Why CPU-only, why fp32, why this LoRA setup

- No confirmed `bitsandbytes` quantization support for aarch64 - so this
  trains the base model in plain fp32 rather than a quantized (QLoRA-style)
  setup. Heavier per-step, but the reliable option on this hardware.
- `gradient_checkpointing` + `enable_input_require_grads()` are both
  required together - checkpointing alone silently breaks gradient flow
  through a frozen base model with a LoRA adapter on top.
- LoRA targets Qwen3's attention + MLP projection layers
  (`q/k/v/o_proj`, `gate/up/down_proj`) - the standard target set for this
  architecture family.
