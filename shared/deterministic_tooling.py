"""Deterministic tooling-overview generator.

The tooling overview is an INVENTORY (hooks / skills / agents / MCP servers) — that
is ground-truth data, not something to summarize. Generating it with an LLM over a
repomix snapshot was the wrong tool: the snapshot drifts between regenerations, the
payload can exceed the model budget (intel hit 5.4M tokens → silent failure → a
month-stale overview that taught 4 deleted hooks as active gates), and the model can
mislabel a hook's mode. This module reads the registration + source-of-truth files
directly, so the injected inventory CANNOT drift, overflow, cost anything, or hallucinate.

`build_tooling_overview(project_root)` returns the markdown BODY (the caller prepends
the metadata line). Generalises across repos: missing agents/ or shadow_mode.json
degrade to empty/unannotated sections.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

# hook event → settings.json key
_HOOK_EVENTS = ["PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit", "SessionStart", "PreCompact"]
_HOOK_FILE_RE = re.compile(r"([A-Za-z0-9_./~$-]*?/)?((?:pre|post)tool[-\w]*|stop[-\w]*|session[-\w]*|userprompt[-\w]*|postwrite[-\w]*|poststop[-\w]*)\.(py|sh)\b")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _resolve_hook_path(project_root: Path, command: str) -> Path | None:
    """Resolve a registered hook command string to an on-disk file, or None for
    inline shell guards (commands with no hook-file reference)."""
    m = _HOOK_FILE_RE.search(command)
    if not m:
        return None
    raw = command[m.start():m.end()]
    raw = raw.replace("$CLAUDE_PROJECT_DIR", str(project_root)).replace("${CLAUDE_PROJECT_DIR}", str(project_root))
    raw = str(Path(raw).expanduser())
    p = Path(raw)
    if not p.is_absolute():
        p = project_root / p
    return p if p.exists() else (p if raw else None)


def _clean_description(raw: str, name: str) -> str:
    """Turn a hook docstring/comment header into a clean one-line description:
    strip the hook's own name self-reference, collapse whitespace, take the first
    sentence, and cap at a word boundary."""
    stem = name.rsplit(".", 1)[0]
    text = " ".join(raw.split())  # collapse newlines/indentation into single spaces
    # strip a leading "<hookname>[.py|.sh]" self-reference whether followed by a
    # separator (— : -) or just whitespace (name on its own docstring line).
    pat = re.compile(rf"^{re.escape(stem)}(?:\.(?:py|sh))?\b\s*[—:–-]?\s*", re.IGNORECASE)
    prev = None
    while text != prev:  # strip a possibly-repeated "<hookname> — " self-reference
        prev = text
        text = pat.sub("", text).strip()
    if not text:
        return ""
    m = re.match(r"(.+?[.!?])(?:\s|$)", text)
    sentence = m.group(1) if m and len(m.group(1)) <= 160 else text
    if len(sentence) > 150:
        sentence = sentence[:150].rsplit(" ", 1)[0] + "…"
    return sentence.rstrip(" .")


def _docstring_first_line(path: Path, name: str = "") -> str:
    """Clean one-line description from a hook's module docstring (or shell header)."""
    name = name or path.name
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return ""
    if path.suffix == ".py":
        try:
            doc = ast.get_docstring(ast.parse(text)) or ""
        except SyntaxError:
            doc = ""
        return _clean_description(doc, name)
    # shell: gather the leading `# ` comment block (skip shebang)
    lines: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#!"):
            continue
        if s.startswith("#"):
            lines.append(s.lstrip("# ").strip())
        elif lines or s:
            break
    return _clean_description(" ".join(lines), name)


def _shadow_set(project_root: Path) -> set[str]:
    f = project_root / ".claude" / "hooks" / "shadow_mode.json"
    if not f.exists():
        return set()
    try:
        d = json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return set()
    raw = d.get("shadowed_hooks", d) if isinstance(d, dict) else d
    if isinstance(raw, dict):
        return {k for k in raw}
    if isinstance(raw, list):
        return {x if isinstance(x, str) else x.get("hook", "") for x in raw}
    return set()


def _registered_hooks(project_root: Path) -> list[dict]:
    settings = project_root / ".claude" / "settings.json"
    if not settings.exists():
        return []
    try:
        cfg = json.loads(settings.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    hooks_cfg = cfg.get("hooks", {})
    shadow = _shadow_set(project_root)
    out: list[dict] = []
    seen: set[str] = set()
    for event in _HOOK_EVENTS:
        for block in hooks_cfg.get(event, []):
            for h in block.get("hooks", []):
                cmd = h.get("command", "")
                path = _resolve_hook_path(project_root, cmd)
                if path is None:
                    continue  # inline shell guard — no file to document
                name = path.name
                if name in seen:
                    continue
                seen.add(name)
                out.append({
                    "event": event,
                    "name": name,
                    "desc": _docstring_first_line(path, name) or "(no docstring)",
                    "shadow": name in shadow,
                    "exists": path.exists(),
                })
    return out


def _frontmatter_field(text: str, field: str) -> str:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return ""
    fm = m.group(1)
    fm_m = re.search(rf"(?m)^{re.escape(field)}\s*:\s*(.*)$", fm)
    if not fm_m:
        return ""
    val = fm_m.group(1).strip()
    # YAML block scalar (`description: |` / `>`): value is the indented block below.
    if val in ("", "|", ">", "|-", ">-", "|+", ">+"):
        lines = fm[fm_m.end():].splitlines()
        block: list[str] = []
        for ln in lines:
            if ln.strip() == "":
                if block:
                    break
                continue
            if ln[:1] in (" ", "\t"):
                block.append(ln.strip())
            else:
                break
        return " ".join(block)
    return val.strip("\"'")


def _skills(project_root: Path) -> list[dict]:
    sk_dir = project_root / ".claude" / "skills"
    if not sk_dir.is_dir():
        return []
    out = []
    # dedup by resolved path — case-insensitive filesystems return SKILL.md for
    # both the SKILL.md and skill.md globs.
    seen: set[str] = set()
    mds = sorted(set(sk_dir.glob("*/SKILL.md")) | set(sk_dir.glob("*/skill.md")),
                 key=lambda p: p.parent.name)
    for md in mds:
        rp = str(md.resolve()).lower()
        if rp in seen:
            continue
        seen.add(rp)
        try:
            text = md.read_text(errors="replace")
        except OSError:
            continue
        name = _frontmatter_field(text, "name") or md.parent.name
        desc = _frontmatter_field(text, "description")
        # first sentence of the description, trimmed
        desc = re.split(r"(?<=[.!?])\s", desc)[0][:160] if desc else ""
        out.append({"name": name, "desc": desc})
    return out


def _agents(project_root: Path) -> list[dict]:
    ag_dir = project_root / ".claude" / "agents"
    if not ag_dir.is_dir():
        return []
    out = []
    for md in sorted(ag_dir.glob("*.md")):
        text = md.read_text(errors="replace")
        name = _frontmatter_field(text, "name") or md.stem
        desc = _frontmatter_field(text, "description")
        desc = re.split(r"(?<=[.!?])\s", desc)[0][:160] if desc else ""
        out.append({"name": name, "desc": desc})
    return out


def _mcps(project_root: Path) -> list[dict]:
    f = project_root / ".mcp.json"
    if not f.exists():
        return []
    try:
        d = json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    servers = d.get("mcpServers", {})
    return [{"name": k} for k in sorted(servers)]


def build_tooling_overview(project_root: Path) -> str:
    """Return the deterministic tooling-overview markdown body (no metadata line)."""
    hooks = _registered_hooks(project_root)
    skills = _skills(project_root)
    agents = _agents(project_root)
    mcps = _mcps(project_root)

    idx: list[str] = ["<!-- INDEX"]
    for h in hooks:
        tag = " (shadow)" if h["shadow"] else ""
        idx.append(f"[HOOK] {h['name']} — {h['desc']}{tag}")
    for s in skills:
        idx.append(f"[SKILL] {s['name']} — {s['desc']}".rstrip(" —"))
    for a in agents:
        idx.append(f"[AGENT] {a['name']} — {a['desc']}".rstrip(" —"))
    for mc in mcps:
        idx.append(f"[MCP] {mc['name']}")
    idx.append("-->")

    body: list[str] = ["\n".join(idx), ""]
    body.append("# Tooling Overview")
    body.append("")
    body.append(
        "_Deterministically generated from `.claude/settings.json` registrations, hook "
        "docstrings, skill/agent frontmatter, and `.mcp.json` — NOT an LLM snapshot. "
        "Cannot drift, overflow, or hallucinate; regenerate any time at $0._"
    )
    body.append("")

    body.append(f"## Registered Hooks ({len(hooks)})")
    body.append("")
    body.append("| Event | Hook | Description | State |")
    body.append("|---|---|---|---|")
    for h in hooks:
        state = "shadow" if h["shadow"] else "active"
        if not h["exists"]:
            state = "**MISSING**"
        body.append(f"| {h['event']} | `{h['name']}` | {h['desc']} | {state} |")
    body.append("")

    if skills:
        body.append(f"## Skills ({len(skills)})")
        body.append("")
        for s in skills:
            body.append(f"- **{s['name']}** — {s['desc']}".rstrip(" —"))
        body.append("")

    if agents:
        body.append(f"## Subagents ({len(agents)})")
        body.append("")
        for a in agents:
            body.append(f"- **{a['name']}** — {a['desc']}".rstrip(" —"))
        body.append("")

    if mcps:
        body.append(f"## MCP Servers ({len(mcps)})")
        body.append("")
        body.append(", ".join(f"`{m['name']}`" for m in mcps))
        body.append("")

    return "\n".join(body).rstrip() + "\n"
