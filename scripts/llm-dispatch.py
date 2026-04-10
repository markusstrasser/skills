#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.llm_dispatch import DispatchOverrides, STATUS_EXIT_CODES, dispatch


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified llmx Python dispatch wrapper for skills automation")
    parser.add_argument("--profile", required=True, help="Named dispatch profile")
    parser.add_argument("--output", required=True, type=Path, help="Output markdown/text artifact path")
    parser.add_argument("--context", type=Path, help="Single assembled context file")
    parser.add_argument("--context-manifest", type=Path, help="Manifest emitted by a packet builder")
    parser.add_argument("--prompt", help="Inline prompt text")
    parser.add_argument("--prompt-file", type=Path, help="Read prompt text from file")
    parser.add_argument("--meta", type=Path, help="Optional meta.json path")
    parser.add_argument("--error-output", type=Path, help="Optional error.json path")
    parser.add_argument("--parsed-output", type=Path, help="Optional parsed JSON output path")
    parser.add_argument("--schema-file", type=Path, help="Optional JSON schema file")
    parser.add_argument("--timeout", type=int, help="Allowed override: timeout seconds")
    parser.add_argument("--reasoning-effort", help="Allowed override: reasoning effort")
    parser.add_argument("--max-tokens", type=int, help="Allowed override: max tokens")
    parser.add_argument("--search", action="store_true", help="Allowed override: enable search")
    parser.add_argument("--system", help="Optional system prompt")
    args = parser.parse_args()

    prompt = args.prompt
    if args.prompt_file:
        prompt = args.prompt_file.read_text()
    if not prompt:
        parser.error("one of --prompt or --prompt-file is required")

    schema = None
    if args.schema_file:
        schema = json.loads(args.schema_file.read_text())

    overrides = DispatchOverrides(
        timeout=args.timeout,
        reasoning_effort=args.reasoning_effort,
        max_tokens=args.max_tokens,
        search=True if args.search else None,
    )
    override_payload = overrides.as_dict()
    if not override_payload:
        overrides = None

    result = dispatch(
        profile=args.profile,
        prompt=prompt,
        context_path=args.context,
        context_manifest_path=args.context_manifest,
        output_path=args.output,
        meta_path=args.meta,
        error_path=args.error_output,
        parsed_path=args.parsed_output,
        schema=schema,
        overrides=overrides,
        system=args.system,
    )

    if result.status == "ok":
        print(result.output_path)
    else:
        print(f"{result.status}: {result.error_message or 'dispatch failed'}", file=sys.stderr)
    return STATUS_EXIT_CODES[result.status]


if __name__ == "__main__":
    raise SystemExit(main())
