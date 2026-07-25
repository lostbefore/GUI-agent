from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .config import build_model, load_config
from .core import DesktopAgent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan or decide a desktop GUI task")
    parser.add_argument("--config", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--screenshot")
    args = parser.parse_args(argv)
    agent = DesktopAgent(build_model(load_config(args.config)))
    plan = agent.plan(args.goal)
    result = {"plan": asdict(plan)}
    if args.screenshot:
        result["decision"] = asdict(agent.decide(args.goal, plan, args.screenshot))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
