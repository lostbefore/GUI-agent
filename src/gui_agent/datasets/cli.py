from __future__ import annotations

import argparse

from .preprocessors import PREPROCESSORS, preprocess_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize public GUI-agent datasets to JSONL")
    parser.add_argument("dataset", choices=sorted(PREPROCESSORS))
    parser.add_argument("--input", required=True, help="Raw dataset directory")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--limit", type=int, help="Optional maximum number of records")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    count = preprocess_dataset(args.dataset, args.input, args.output, limit=args.limit)
    print(f"Wrote {count} {args.dataset} records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
