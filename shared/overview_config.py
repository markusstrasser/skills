from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class OverviewConfig:
    project_root: Path
    types: list[str]
    model: str
    output_dir: str
    prompt_dir: str
    exclude: str
    no_gitignore: bool
    loc_threshold: int
    dirs_by_type: dict[str, list[str]]

    def prompt_file(self, overview_type: str) -> Path:
        if self.prompt_dir.startswith("/"):
            return Path(self.prompt_dir) / f"{overview_type}.md"
        return self.project_root / self.prompt_dir / f"{overview_type}.md"

    def output_file(self, overview_type: str) -> Path:
        if self.output_dir.startswith("/"):
            return Path(self.output_dir) / f"{overview_type}-overview.md"
        return self.project_root / self.output_dir / f"{overview_type}-overview.md"


def read_overview_config(project_root: Path) -> OverviewConfig:
    conf_file = project_root / ".claude" / "overview.conf"
    config: dict[str, str] = {
        "OVERVIEW_TYPES": "source",
        "OVERVIEW_MODEL": "gemini-3-flash-preview",
        "OVERVIEW_OUTPUT_DIR": ".claude/overviews",
        "OVERVIEW_PROMPT_DIR": str((Path.home() / "Projects" / "skills" / "hooks" / "overview-prompts")),
        "OVERVIEW_EXCLUDE": "",
        "OVERVIEW_NO_GITIGNORE": "",
        "OVERVIEW_LOC_THRESHOLD": "200",
    }
    if conf_file.exists():
        for line in conf_file.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            config[key.strip()] = value.strip().strip('"')

    for key in (
        "OVERVIEW_TYPES",
        "OVERVIEW_MODEL",
        "OVERVIEW_OUTPUT_DIR",
        "OVERVIEW_PROMPT_DIR",
        "OVERVIEW_EXCLUDE",
        "OVERVIEW_NO_GITIGNORE",
        "OVERVIEW_LOC_THRESHOLD",
    ):
        env_value = os.environ.get(key)
        if env_value:
            config[key] = env_value

    overview_types = [item.strip() for item in config["OVERVIEW_TYPES"].split(",") if item.strip()]
    dirs_by_type: dict[str, list[str]] = {}
    for overview_type in overview_types:
        config_key = f"OVERVIEW_{overview_type.upper()}_DIRS"
        dirs_by_type[overview_type] = [item.strip() for item in config.get(config_key, "").split(",") if item.strip()]

    return OverviewConfig(
        project_root=project_root,
        types=overview_types,
        model=config["OVERVIEW_MODEL"],
        output_dir=config["OVERVIEW_OUTPUT_DIR"],
        prompt_dir=config["OVERVIEW_PROMPT_DIR"],
        exclude=config["OVERVIEW_EXCLUDE"],
        no_gitignore=config["OVERVIEW_NO_GITIGNORE"].lower() == "true",
        loc_threshold=int(config["OVERVIEW_LOC_THRESHOLD"]),
        dirs_by_type=dirs_by_type,
    )
