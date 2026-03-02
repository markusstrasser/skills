# Context views for cross-model review
# Usage: make [target]  — generates .xml views from working tree

SHELL := /bin/bash
PROJECT_ROOT := $(shell cd .. && pwd)
REPOMIX := repomix --quiet --style xml --no-security-check --no-git-sort-by-changes

# Source file sets
SKILL_FILES := $(shell find $(PROJECT_ROOT) -name 'SKILL.md' -not -path '*/archive/*' 2>/dev/null)
HOOK_FILES := $(shell find $(PROJECT_ROOT)/hooks -name '*.sh' 2>/dev/null)
SCRIPT_FILES := $(shell find $(PROJECT_ROOT) -path '*/scripts/*.py' 2>/dev/null)
SCHEMA_FILES := $(shell find $(PROJECT_ROOT) -path '*/schemas/*' 2>/dev/null)
ALL_FILES := $(SKILL_FILES) $(HOOK_FILES) $(SCRIPT_FILES) $(SCHEMA_FILES)

.PHONY: all clean filetree

all: full.xml skills.xml hooks.xml filetree.xml

# Full context — all skills + hooks + scripts
full.xml: $(ALL_FILES)
	cd $(PROJECT_ROOT) && $(REPOMIX) \
		--include "**/SKILL.md,hooks/**/*.sh,**/scripts/*.py,**/schemas/*,researcher/DOMAINS.md" \
		--ignore ".context/**,archive/**,__pycache__/**,.venv/**,test-output/**" \
		-o .context/$@

# Skills only — all SKILL.md files
skills.xml: $(SKILL_FILES)
	cd $(PROJECT_ROOT) && $(REPOMIX) \
		--include "**/SKILL.md,researcher/DOMAINS.md" \
		--ignore "archive/**" \
		-o .context/$@

# Hooks only — shared hook scripts
hooks.xml: $(HOOK_FILES)
	cd $(PROJECT_ROOT) && $(REPOMIX) \
		--include "hooks/**/*.sh" \
		-o .context/$@

# Directory structure only
filetree.xml:
	cd $(PROJECT_ROOT) && $(REPOMIX) \
		--no-files --no-file-summary \
		--ignore ".context/**,archive/**,__pycache__/**,.venv/**,test-output/**" \
		-o .context/$@

clean:
	rm -f *.xml
