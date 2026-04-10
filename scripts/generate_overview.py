#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.context_packet import BudgetPolicy, ContextPacket, PacketSection, SourceFileBlock, TextBlock, atomic_write_text
from shared.context_renderers import write_packet_artifact
from shared.git_context import run_git
from shared.llm_dispatch import DispatchProfile, dispatch, map_model_to_profile, profile_input_budget, PROFILES
from shared.overview_config import OverviewConfig, read_overview_config
from shared.repomix_source import build_include_pattern, capture_repomix_to_file


BUILDER_VERSION = "2026-04-10-v1"
DEFAULT_PROJECTS = ("meta", "intel", "selve", "genomics")


@dataclass(frozen=True)
class OverviewPayload:
    overview_type: str
    profile_name: str
    profile: DispatchProfile
    project_root: Path
    output_file: Path
    payload_path: Path
    manifest_path: Path
    token_estimate: int | None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_project_root(project_root: str | None) -> Path:
    if project_root:
        return Path(project_root).expanduser().resolve()
    try:
        return Path(run_git(Path.cwd(), ["rev-parse", "--show-toplevel"]).strip())
    except Exception:
        return Path.cwd().resolve()


def current_commit_hash(project_root: Path) -> str:
    try:
        return run_git(project_root, ["rev-parse", "HEAD"]).strip()
    except Exception:
        return "unknown"


def resolve_dispatch_profile(config: OverviewConfig) -> str:
    return map_model_to_profile(config.model)


def build_overview_packet(
    project_root: Path,
    config: OverviewConfig,
    overview_type: str,
    *,
    profile_name: str,
    output_dir: Path,
) -> OverviewPayload:
    prompt_file = config.prompt_file(overview_type)
    if not prompt_file.exists():
        raise FileNotFoundError(f"prompt template not found: {prompt_file}")

    dirs = config.dirs_by_type.get(overview_type) or []
    if not dirs:
        raise ValueError(f"no directories configured for type '{overview_type}'")

    output_dir.mkdir(parents=True, exist_ok=True)
    include_pattern = build_include_pattern(dirs)
    repomix_output = output_dir / f".overview-{overview_type}-codebase.txt"
    capture_repomix_to_file(
        project_root=project_root,
        include_pattern=include_pattern,
        exclude=config.exclude,
        no_gitignore=config.no_gitignore,
        output_path=repomix_output,
    )

    budget = profile_input_budget(profile_name)
    packet = ContextPacket(
        title=f"{overview_type} overview payload",
        sections=[
            PacketSection(
                "Instructions",
                [TextBlock("instructions", prompt_file.read_text(), metadata={"path": str(prompt_file)})],
                tag="instructions",
            ),
            PacketSection(
                "Codebase",
                [SourceFileBlock(repomix_output, title="codebase", priority=100, drop_if_needed=False)],
                tag="codebase",
            ),
        ],
        metadata={
            "project_root": str(project_root),
            "overview_type": overview_type,
            "trailing_text": "Write the requested codebase overview in markdown.",
        },
        budget_policy=BudgetPolicy(
            metric="tokens",
            limit=budget["input_token_limit"] or 120000,
            estimate_method=budget["input_token_estimator"],
        ),
    )
    payload_path = output_dir / f".overview-{overview_type}-payload.txt"
    manifest_path = output_dir / f".overview-{overview_type}-payload.manifest.json"
    artifact = write_packet_artifact(
        packet,
        renderer="tagged",
        output_path=payload_path,
        manifest_path=manifest_path,
        builder_name="overview_payload",
        builder_version=BUILDER_VERSION,
    )
    profile = PROFILES[profile_name]
    return OverviewPayload(
        overview_type=overview_type,
        profile_name=profile_name,
        profile=profile,
        project_root=project_root,
        output_file=config.output_file(overview_type),
        payload_path=payload_path,
        manifest_path=manifest_path,
        token_estimate=artifact.token_estimate,
    )


def metadata_line(*, commit_hash: str, profile_name: str, model: str) -> str:
    return (
        f"<!-- Generated: {utc_now()} | git: {commit_hash[:7]} | "
        f"profile: {profile_name} | model: {model} -->"
    )


def write_overview_output(
    *,
    output_file: Path,
    markdown_body: str,
    commit_hash: str,
    profile_name: str,
    model: str,
) -> None:
    rendered = metadata_line(commit_hash=commit_hash, profile_name=profile_name, model=model) + "\n\n" + markdown_body.rstrip() + "\n"
    atomic_write_text(output_file, rendered)


def write_marker(project_root: Path, overview_type: str, commit_hash: str) -> None:
    marker = project_root / ".claude" / f"overview-marker-{overview_type}"
    marker.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(marker, commit_hash + "\n")


def generate_one(
    *,
    project_root: Path,
    config: OverviewConfig,
    overview_type: str,
    commit_hash: str,
    dry_run: bool,
) -> int:
    profile_name = resolve_dispatch_profile(config)
    prompt_file = config.prompt_file(overview_type)
    dirs = config.dirs_by_type.get(overview_type) or []
    output_file = config.output_file(overview_type)

    if dry_run:
        print(f"[dry-run] {overview_type}")
        print(f"  output: {output_file}")
        print(f"  profile: {profile_name}")
        print(f"  model: {PROFILES[profile_name].model}")
        print(f"  prompt: {prompt_file}")
        print(f"  dirs: {', '.join(dirs)}")
        return 0

    payload = build_overview_packet(
        project_root,
        config,
        overview_type,
        profile_name=profile_name,
        output_dir=config.output_file(overview_type).parent,
    )

    budget = profile_input_budget(payload.profile_name)
    if payload.token_estimate and budget["input_token_limit"] and payload.token_estimate > budget["input_token_limit"]:
        print(
            f"[{overview_type}] ERROR: payload (~{payload.token_estimate} tokens) exceeds safe limit "
            f"({budget['input_token_limit']}) for {payload.profile_name}",
            file=sys.stderr,
        )
        return 1

    temp_output = payload.output_file.parent / f".overview-{overview_type}.tmp.md"
    result = dispatch(
        profile=payload.profile_name,
        prompt=payload.payload_path.read_text(),
        context_manifest_path=payload.manifest_path,
        output_path=temp_output,
    )
    if result.status not in {"ok", "parse_error"} or not temp_output.exists() or temp_output.stat().st_size == 0:
        print(f"[{overview_type}] ERROR: dispatch failed ({result.status})", file=sys.stderr)
        return 1

    write_overview_output(
        output_file=payload.output_file,
        markdown_body=temp_output.read_text(),
        commit_hash=commit_hash,
        profile_name=payload.profile_name,
        model=result.model,
    )
    temp_output.unlink(missing_ok=True)
    write_marker(project_root, overview_type, commit_hash)
    print(f"[{overview_type}] Done → {payload.output_file} (marker: {commit_hash[:7]})")
    return 0


def live_mode(args: argparse.Namespace) -> int:
    project_root = resolve_project_root(args.project_root)
    commit_hash = args.commit_hash or current_commit_hash(project_root)
    config = read_overview_config(project_root)

    if args.auto:
        failures = 0
        for overview_type in config.types:
            marker = project_root / ".claude" / f"overview-marker-{overview_type}"
            if marker.exists() and marker.read_text().strip() == commit_hash:
                print(f"[{overview_type}] Already current (marker matches {commit_hash[:7]}), skipping")
                continue
            failures += generate_one(
                project_root=project_root,
                config=config,
                overview_type=overview_type,
                commit_hash=commit_hash,
                dry_run=args.dry_run,
            )
        return 1 if failures else 0

    if not args.type:
        print("Error: specify --type TYPE or --auto", file=sys.stderr)
        return 1
    return generate_one(
        project_root=project_root,
        config=config,
        overview_type=args.type,
        commit_hash=commit_hash,
        dry_run=args.dry_run,
    )


def batch_submit_command(jsonl_file: Path, *, wait: bool, output_file: Path | None = None) -> list[str]:
    command = ["uv", "run", "llmx", "batch", "submit", str(jsonl_file), "-m", "gemini-3.1-pro-preview"]
    if wait:
        command.append("--wait")
    if output_file is not None:
        command.extend(["-o", str(output_file)])
    return command


def batch_get_command(job_name: str, *, output_file: Path) -> list[str]:
    return ["uv", "run", "llmx", "batch", "get", job_name, "-o", str(output_file)]


def build_batch_requests(work_dir: Path, projects: list[str]) -> tuple[int, Path, Path]:
    jsonl_file = work_dir / "batch-input.jsonl"
    manifest_path = work_dir / "manifest.json"
    count = 0
    manifest_entries: list[dict[str, object]] = []

    with jsonl_file.open("w") as jsonl_handle:
        for project in projects:
            project_root = Path.home() / "Projects" / project
            conf_path = project_root / ".claude" / "overview.conf"
            if not conf_path.exists():
                continue
            config = read_overview_config(project_root)
            profile_name = resolve_dispatch_profile(config)
            commit_hash = current_commit_hash(project_root)
            for overview_type in config.types:
                payload = build_overview_packet(
                    project_root,
                    config,
                    overview_type,
                    profile_name=profile_name,
                    output_dir=work_dir / project,
                )
                key = f"{project}-{overview_type}"
                json.dump({"key": key, "prompt": payload.payload_path.read_text()}, jsonl_handle)
                jsonl_handle.write("\n")
                manifest_entries.append(
                    {
                        "key": key,
                        "project": project,
                        "project_root": str(project_root),
                        "type": overview_type,
                        "output": str(payload.output_file),
                        "profile": payload.profile_name,
                        "model": payload.profile.model,
                        "commit_hash": commit_hash,
                    }
                )
                count += 1

    manifest_path.write_text(json.dumps(manifest_entries, indent=2) + "\n")
    return count, jsonl_file, manifest_path


def distribute_results(results_file: Path, manifest_path: Path) -> int:
    manifest = {entry["key"]: entry for entry in json.loads(manifest_path.read_text())}
    distributed = 0
    for line in results_file.read_text().splitlines():
        if not line.strip():
            continue
        result = json.loads(line)
        key = result.get("key")
        if key not in manifest:
            print(f"WARN: no manifest entry for {key}", file=sys.stderr)
            continue
        entry = manifest[key]
        content = result.get("content") or ""
        if not content:
            print(f"ERROR: empty batch result for {key}", file=sys.stderr)
            continue
        output_file = Path(entry["output"])
        write_overview_output(
            output_file=output_file,
            markdown_body=content,
            commit_hash=str(entry["commit_hash"]),
            profile_name=str(entry["profile"]),
            model=str(result.get("model") or entry["model"]),
        )
        write_marker(Path(entry["project_root"]), str(entry["type"]), str(entry["commit_hash"]))
        distributed += 1
    return distributed


def batch_mode(args: argparse.Namespace) -> int:
    projects = list(DEFAULT_PROJECTS)
    with TemporaryDirectory(prefix="overview-batch-") as temp_dir:
        work_dir = Path(temp_dir)
        if args.mode == "get":
            manifest_path = Path(f"/tmp/overview-batch-manifest-{args.job_name.replace('/', '-')}.json")
            if not manifest_path.exists():
                print(f"Error: manifest not found at {manifest_path}", file=sys.stderr)
                return 1
            results_file = work_dir / "results.jsonl"
            llmx_root = Path.home() / "Projects" / "llmx"
            proc = subprocess.run(
                batch_get_command(args.job_name, output_file=results_file),
                cwd=llmx_root,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                print(proc.stderr, file=sys.stderr)
                return 1
            distributed = distribute_results(results_file, manifest_path)
            print(f"Distributed {distributed} overviews", file=sys.stderr)
            return 0

        count, jsonl_file, manifest_path = build_batch_requests(work_dir, projects)
        if count == 0:
            print("No overviews to generate", file=sys.stderr)
            return 0
        if args.mode == "dry-run":
            print(f"Would submit {count} overview requests from {jsonl_file}")
            return 0

        llmx_root = Path.home() / "Projects" / "llmx"
        results_file = work_dir / "results.jsonl"
        proc = subprocess.run(
            batch_submit_command(jsonl_file, wait=args.mode == "submit-wait", output_file=results_file if args.mode == "submit-wait" else None),
            cwd=llmx_root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            return 1

        submitted_job = None
        for line in proc.stdout.splitlines() + proc.stderr.splitlines():
            if line.startswith("Submitted:"):
                submitted_job = line.split(":", 1)[1].strip()
                break

        if submitted_job:
            saved_manifest = Path(f"/tmp/overview-batch-manifest-{submitted_job.replace('/', '-')}.json")
            shutil.copy2(manifest_path, saved_manifest)
            print(f"Manifest: {saved_manifest}")
            print(f"Job: {submitted_job}")

        if args.mode == "submit-only":
            return 0

        if not results_file.exists():
            print("Batch job completed without results file", file=sys.stderr)
            return 1
        distributed = distribute_results(results_file, manifest_path)
        print(f"Distributed {distributed} overviews", file=sys.stderr)
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Overview generation entrypoint")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    live = subparsers.add_parser("live")
    live.add_argument("--type")
    live.add_argument("--auto", action="store_true")
    live.add_argument("--dry-run", action="store_true")
    live.add_argument("--project-root")
    live.add_argument("--commit-hash")

    batch = subparsers.add_parser("batch")
    mode_group = batch.add_mutually_exclusive_group()
    mode_group.add_argument("--submit-only", action="store_true")
    mode_group.add_argument("--get", dest="job_name")
    mode_group.add_argument("--dry-run", action="store_true")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.subcommand == "live":
        return live_mode(args)
    args.mode = "submit-wait"
    if args.submit_only:
        args.mode = "submit-only"
    elif args.job_name:
        args.mode = "get"
    elif args.dry_run:
        args.mode = "dry-run"
    return batch_mode(args)


if __name__ == "__main__":
    raise SystemExit(main())
