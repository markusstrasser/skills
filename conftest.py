"""Repo-wide xdist grouping.

pyproject runs `--dist loadgroup`. By default every test is grouped by its module,
which is exactly `--dist loadfile` (a file's tests share one worker, so module state
stays safe). Modules listed in PER_TEST_MODULES opted out: each of their tests is
its own group, so one long file no longer runs serially on a single worker.
Within those modules, tests that need a shared worker keep an explicit group.
"""

import pytest

# Files whose tests isolate themselves (fresh tmp_path HOME per test) and are long
# enough that file-level scheduling made them the critical path.
PER_TEST_MODULES = {
    # 128 tests, each spawning the dispatcher; was ~175-400 s on one worker.
    "hooks/test_bash_dispatch.py",
}

# Fixtures whose tests watch live processes (pgrep/killall replays against decoys);
# keep them on one worker so decoys from parallel tests never share a process table
# window. Their patterns are unique per test, so this is belt-and-braces.
SERIAL_FIXTURES = {"decoys": "live-process-decoys"}


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    # Runs before xdist's own hook, which appends the xdist_group name to each nodeid.
    for item in items:
        if item.get_closest_marker("xdist_group"):
            continue
        module = item.nodeid.split("::", 1)[0]
        if module in PER_TEST_MODULES:
            group = next(
                (g for f, g in SERIAL_FIXTURES.items() if f in getattr(item, "fixturenames", ())),
                None,
            )
            if group:
                item.add_marker(pytest.mark.xdist_group(group))
            continue  # ungrouped: scheduled per test
        item.add_marker(pytest.mark.xdist_group(module))
