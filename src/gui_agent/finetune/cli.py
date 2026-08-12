from __future__ import annotations

import argparse
import json
from pathlib import Path

from .data import build_sft_dataset
from .evaluate import evaluate_model
from .metrics import load_prediction_rows, score_predictions, write_comparison_report
from .train import train_lora


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GUI agent LoRA fine-tuning")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Build train and validation JSONL files")
    prepare.add_argument("--input", action="append", required=True)
    prepare.add_argument("--output-dir", default="data/finetune")
    prepare.add_argument("--validation-ratio", type=float, default=0.1)
    prepare.add_argument("--seed", type=int, default=42)
    prepare.add_argument("--limit", type=int)
    prepare.add_argument("--max-actions", type=int, default=6)
    prepare.add_argument("--source-split", action="append", default=["train"])
    train = commands.add_parser("train", help="Run QLoRA fine-tuning")
    train.add_argument("--config", required=True)
    evaluate = commands.add_parser("evaluate", help="Generate model predictions and score them")
    evaluate.add_argument("--config", required=True)
    evaluate.add_argument("--dataset", required=True)
    evaluate.add_argument("--output", required=True)
    evaluate.add_argument("--adapter")
    evaluate.add_argument("--limit", type=int)
    compare = commands.add_parser("compare", help="Create comparison report")
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--finetuned", required=True)
    compare.add_argument("--output", default="docs/week5-finetune-comparison-report.md")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        counts = build_sft_dataset(
            args.input,
            args.output_dir,
            validation_ratio=args.validation_ratio,
            seed=args.seed,
            limit=args.limit,
            max_actions=args.max_actions,
            source_splits=args.source_split,
        )
        print(json.dumps(counts, ensure_ascii=False))
        return 0
    if args.command == "train":
        print(f"LoRA weights saved to {train_lora(args.config)}")
        return 0
    if args.command == "evaluate":
        result = evaluate_model(args.config, args.dataset, args.output, args.adapter, args.limit)
        print(json.dumps(result.to_dict(), ensure_ascii=False))
        return 0
    baseline = score_predictions(load_prediction_rows(args.baseline))
    finetuned = score_predictions(load_prediction_rows(args.finetuned))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_comparison_report(baseline, finetuned, output)
    print(f"Comparison report written to {output}")
    return 0


if __name__ == "__main__":    raise SystemExit(main())