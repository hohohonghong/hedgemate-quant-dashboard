#!/usr/bin/env python3
"""Run the intraday Top5 news overlay pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .news_intraday_overlay import default_model_for_provider, normalize_ai_provider, run_pipeline
except ImportError:
    from news_intraday_overlay import default_model_for_provider, normalize_ai_provider, run_pipeline


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--data-version", default=None)
    parser.add_argument("--trigger-reason", default="scheduled")
    parser.add_argument("--provider", default=None, choices=["gemini", "openai"], help="AI provider for structured news validation.")
    parser.add_argument("--model", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-network", action="store_true", help="Use fallback fixtures without API/RSS/search calls.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    provider = normalize_ai_provider(args.provider)
    outputs = run_pipeline(
        run_id=args.run_id,
        data_version=args.data_version,
        trigger_reason=args.trigger_reason,
        force=args.force,
        allow_network=not args.no_network,
        provider_name=provider,
        model_name=args.model or default_model_for_provider(provider),
    )
    print("DONE")
    for key, value in outputs.items():
        if isinstance(value, Path):
            print(f"{key.upper()}={value}")
    if outputs.get("reused"):
        print(f"REUSED={outputs.get('reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
