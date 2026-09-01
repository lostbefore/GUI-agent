from __future__ import annotations

from pathlib import Path
from typing import Any

from gui_agent.agent.config import load_config

from .data import SYSTEM_PROMPT, load_examples


def _dependencies() -> dict[str, Any]:
    try:
        import torch
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import (
            AutoModelForImageTextToText,
            AutoProcessor,
            BitsAndBytesConfig,
            Trainer,
            TrainingArguments,
        )
    except ImportError as error:
        raise RuntimeError('??????????pip install -e ".[finetune]"') from error
    return {
        "torch": torch,
        "LoraConfig": LoraConfig,
        "get_peft_model": get_peft_model,
        "prepare_model_for_kbit_training": prepare_model_for_kbit_training,
        "AutoModelForImageTextToText": AutoModelForImageTextToText,
        "AutoProcessor": AutoProcessor,
        "BitsAndBytesConfig": BitsAndBytesConfig,
        "Trainer": Trainer,
        "TrainingArguments": TrainingArguments,
    }


def _batch(processor: Any, examples: list[dict[str, Any]], max_length: int) -> dict[str, Any]:
    messages = [
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": str(example["instruction"])},
            {"role": "assistant", "content": str(example["response"])},
        ]
        for example in examples
    ]
    texts = [processor.apply_chat_template(message, tokenize=False) for message in messages]
    batch = processor(
        text=texts, padding=True, truncation=True, max_length=max_length, return_tensors="pt"
    )
    labels = batch["input_ids"].clone()
    labels[batch["attention_mask"] == 0] = -100
    batch["labels"] = labels
    return batch


class _ExampleDataset:
    def __init__(self, examples: list[Any]) -> None:
        self.examples = examples

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self.examples[index].to_dict()


def train_lora(config_path: str | Path) -> Path:
    config = load_config(config_path).get("finetune", {})
    required = ("model_path", "train_file", "validation_file", "output_dir")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError(f"?????????{', '.join(missing)}")
    modules = _dependencies()
    torch = modules["torch"]
    output = Path(config["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    processor = modules["AutoProcessor"].from_pretrained(config["model_path"])
    quantization = modules["BitsAndBytesConfig"](
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = modules["AutoModelForImageTextToText"].from_pretrained(
        config["model_path"],
        device_map={"": 0},
        torch_dtype=torch.bfloat16,
        quantization_config=quantization,
    )
    model.config.use_cache = False
    model = modules["prepare_model_for_kbit_training"](model)
    lora = modules["LoraConfig"](
        r=int(config.get("lora_rank", 8)),
        lora_alpha=int(config.get("lora_alpha", 16)),
        lora_dropout=float(config.get("lora_dropout", 0.05)),
        target_modules=list(config.get("target_modules", ["q_proj", "v_proj"])),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = modules["get_peft_model"](model, lora)
    max_length = int(config.get("max_length", 1024))
    arguments = modules["TrainingArguments"](
        output_dir=str(output),
        learning_rate=float(config.get("learning_rate", 1e-4)),
        max_steps=int(config.get("max_steps", 40)),
        per_device_train_batch_size=int(config.get("batch_size", 1)),
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=int(config.get("gradient_accumulation_steps", 8)),
        logging_steps=int(config.get("logging_steps", 5)),
        save_strategy="steps",
        save_steps=int(config.get("save_steps", 20)),
        eval_strategy="steps",
        eval_steps=int(config.get("eval_steps", 20)),
        bf16=True,
        report_to=[],
        remove_unused_columns=False,
    )
    trainer = modules["Trainer"](
        model=model,
        args=arguments,
        train_dataset=_ExampleDataset(load_examples(config["train_file"])),
        eval_dataset=_ExampleDataset(load_examples(config["validation_file"])),
        data_collator=lambda examples: _batch(processor, examples, max_length),
    )
    trainer.train()
    adapter = output / "adapter"
    trainer.model.save_pretrained(adapter)
    processor.save_pretrained(adapter)
    return adapter
