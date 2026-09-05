#!/usr/bin/env python3
"""LoRA fine-tune of a small base model on the dairy-systems seed data.
Single command: `python train.py`. Resumable - re-running after a kill
picks up from the last checkpoint in output/ automatically.
"""
import argparse
import glob
import json
import os

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
)
from transformers.trainer_utils import get_last_checkpoint

DEFAULT_MODEL = "Qwen/Qwen3-0.6B"
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
MAX_SEQ_LENGTH = 512  # kept short - phone RAM is the binding constraint, not model quality

# Qwen3's attention + MLP projection layer names - the standard LoRA target
# set for this architecture family.
LORA_TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]


def load_examples(data_dir):
    examples = []
    for path in sorted(glob.glob(os.path.join(data_dir, "*.jsonl"))):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    examples.append(json.loads(line))
    return examples


def build_supervised_example(tokenizer, example, max_length):
    """Tokenize with the model's chat template, masking loss on the prompt
    portion so training only optimizes for the assistant's response."""
    user_content = example["instruction"]
    if example.get("input"):
        user_content += "\n\n" + example["input"]
    messages = [{"role": "user", "content": user_content}]

    prompt_ids = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True,
    )
    full_ids = tokenizer.apply_chat_template(
        messages + [{"role": "assistant", "content": example["output"]}],
        tokenize=True, add_generation_prompt=False,
    )
    full_ids = full_ids[:max_length]
    prompt_len = min(len(prompt_ids), len(full_ids))

    labels = [-100] * prompt_len + full_ids[prompt_len:]
    return {"input_ids": full_ids, "attention_mask": [1] * len(full_ids), "labels": labels}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--epochs", type=float, default=3.0)
    args = parser.parse_args()

    print(f"Loading tokenizer/model: {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.float32,  # fp32: CPU-only aarch64 build, no confirmed bf16/fp16 autograd support
        low_cpu_mem_usage=True,
    )
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()  # required for grad-checkpointing to work through a frozen base + LoRA

    lora_config = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        target_modules=LORA_TARGET_MODULES, task_type="CAUSAL_LM", bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    raw_examples = load_examples(args.data_dir)
    print(f"Loaded {len(raw_examples)} training examples from {args.data_dir}")
    if not raw_examples:
        raise SystemExit(f"No .jsonl files found in {args.data_dir}")

    dataset = Dataset.from_list(raw_examples)
    dataset = dataset.map(
        lambda ex: build_supervised_example(tokenizer, ex, MAX_SEQ_LENGTH),
        remove_columns=dataset.column_names,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    last_checkpoint = get_last_checkpoint(args.output_dir)
    if last_checkpoint:
        print(f"Resuming from checkpoint: {last_checkpoint}")

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,  # effective batch size 8, without the memory cost
        num_train_epochs=args.epochs,
        learning_rate=2e-4,
        logging_steps=5,
        save_steps=20,
        save_total_limit=3,
        bf16=False, fp16=False,  # see torch_dtype comment above
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True, label_pad_token_id=-100),
    )

    trainer.train(resume_from_checkpoint=last_checkpoint)

    final_dir = os.path.join(args.output_dir, "adapter_final")
    model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    print(f"Done. LoRA adapter saved to {final_dir}")


if __name__ == "__main__":
    main()
