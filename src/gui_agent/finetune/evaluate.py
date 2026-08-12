from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gui_agent.agent.config import load_config

from .data import SYSTEM_PROMPT, load_examples
from .metrics import EvaluationResult, score_predictions


def _dependencies() -> tuple[Any, Any, Any, Any, Any]:
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig
    except ImportError as error:
        raise RuntimeError("??????????pip install -e \".[finetune]\"") from error
    return torch, PeftModel, AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig


def evaluate_model(
    config_path: str | Path,
    dataset_path: str | Path,
    output_path: str | Path,
    adapter_path: str | Path | None = None,
    limit: int | None = None,
) -> EvaluationResult:
    config = load_config(config_path).get("finetune", {})
    model_path = config.get("model_path")
    if not model_path:
        raise ValueError("?????????model_path")
    torch, peft_model, model_class, processor_class, quantization_class = _dependencies()
    processor = processor_class.from_pretrained(adapter_path or model_path)
    model = model_class.from_pretrained(
        model_path,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        quantization_config=quantization_class(load_in_4bit=True),
    )
    if adapter_path:
        model = peft_model.from_pretrained(model, adapter_path)
    model.eval()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    with output.open("w", encoding="utf-8") as handle:
        for example in load_examples(dataset_path)[:limit]:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": example.instruction},
            ]
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text], return_tensors="pt")
            device = next(model.parameters()).device
            inputs = {key: value.to(device) for key, value in inputs.items()}
            generated = model.generate(**inputs, max_new_tokens=int(config.get("eval_max_tokens", 160)))
            prediction = processor.batch_decode(
                generated[:, inputs["input_ids"].shape[1] :], skip_special_tokens=True
            )[0].strip()
            row = {
                "example_id": example.example_id,
                "reference": example.response,
                "prediction": prediction,
            }
            rows.append(row)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return score_predictions(rows)
