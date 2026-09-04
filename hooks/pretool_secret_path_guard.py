#!/usr/bin/env python3
# Gov-ID: hook:secret-path-guard
# goal: keep the two operator secret stores out of agent tool reads, deterministically
# verifier: skills/hooks/test_secret_path_guard.py
# blast_radius: shared
"""pretool_secret_path_guard.py — ONE definition of the protected secret paths, consumed by
the Bash dispatcher gate (`gate_secret_path_guard`) and the Read/Grep/Glob hook
(`pretool-secret-path-read-guard.py`).

Why a hook and not a settings.json `Read()` deny rule (2026-09-04): the two global deny rules
`Read(//Users/alien/.config/sops/age/keys.txt)` and `Read(//Users/alien/.config/secrets/**)`
made Claude Code's auto-mode permission classifier STOP FOR A HUMAN whenever a Bash command's
read path could not be resolved — verbatim: "grep on 'justfile' after a cd would search a
directory that cannot be determined here, and a Read() deny rule is configured; only you can
approve running it anyway." A subagent lane blocked on that prompt while the operator was AFK
("THIS CANNOT BE ASKED AGAIN"). 317 of that session's 1,151 Bash commands carried the same
`cd <cwd>; …` shape and merely happened not to be asked about: the prompt is a model's judgment,
so it cannot be made deterministic from the command side. Removing the deny rules removes the
whole class; this module keeps the protection they provided, without ever asking.

Scope — narrow and literal, matching the accidental-dump threat model (the agent typing the path):
  * any spelling of the two stores: absolute, `~`-, or `$HOME`-relative, or a bare `.config/...`
    reference (`.config/sops/age`, `.config/secrets`), plus `sops/age` on its own;
  * a shell glob directly on a `.config` child (`~/.config/sec*`, `~/.config/*`) — the one
    cheap obfuscation of the same paths;
  * the one-hop indirection `cd ~/.config && cat secrets/x`.
Bodies of QUOTED-delimiter heredocs (<<'EOF') are data the shell never expands, so a test or a
memo that names the paths can still be written through Bash; an unquoted heredoc body is scanned.
Nothing else under `.config` (gh, modal, git …) is touched.

Calibration 2026-09-04: FN — every incident-shaped read in test_secret_path_guard.FIRES fires;
FP — 0 fires over 1,151 real Bash commands of the originating session and 2 over 4,570 across
12 sessions, both being the commands that wrote this guard with the paths in an unquoted context.
"""

from __future__ import annotations

import re

from lib_bash_cmd_strip import strip_quoted_heredocs

PROTECTED_PATHS: tuple[str, ...] = (
    ".config/sops/age",  # keys.txt lives here; the directory is the unit
    ".config/secrets",
    "sops/age",  # `cd ~/.config && cat sops/age/keys.txt`
)

# A glob metacharacter directly in the `.config` child segment: `.config/sec*`, `.config/*`,
# `.config/s?crets`, `.config/[s]ecrets`. `.config/gh/*` does NOT match (child is `gh`).
_CONFIG_CHILD_GLOB = re.compile(r"\.config/[A-Za-z0-9_.-]*[*?\[]")

# One-hop indirection: `.config` is named and `secrets/` is later used as a directory
# (`cd ~/.config && cat secrets/x`). `rg secrets scripts/` has no `secrets/`; a repo's
# `docs/secrets/` has no `.config`; only both together is refused.
_INDIRECT_SECRETS_DIR = re.compile(r"(?<![\w.-])secrets/")


def offending_secret_path(text: str) -> str | None:
    """Return the protected token found in ``text`` (a shell command or a tool path), else None."""
    if not text:
        return None
    text = strip_quoted_heredocs(text)
    for token in PROTECTED_PATHS:
        if token in text:
            return token
    match = _CONFIG_CHILD_GLOB.search(text)
    if match:
        return match.group(0)
    if ".config" in text and _INDIRECT_SECRETS_DIR.search(text):
        return "secrets/"
    return None


def reason(token: str, tool: str = "Bash") -> str:
    return (
        f"BLOCKED: {tool} would touch a protected secret store ({token!r}). The operator's "
        "SOPS age key (~/.config/sops/age/keys.txt) and ~/.config/secrets/ are never read into "
        "an agent transcript — a dumped secret cannot be un-read. Decrypt with the tool that "
        "owns the key (`sops -d file`) and pass only the decrypted VALUE you need; if a task "
        "truly needs the key material, it is the operator's to handle. Writing a file that merely "
        "NAMES these paths is fine through the Write tool or a quoted-delimiter heredoc (<<'EOF'). "
        "This deterministic hook replaced the settings.json Read() deny rules on 2026-09-04 "
        "because those made the permission classifier stop for a human on every unresolvable "
        "read path."
    )
