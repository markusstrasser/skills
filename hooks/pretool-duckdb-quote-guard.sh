#!/bin/bash
# PreToolUse hook (Bash) — catch DuckDB double-quote string literal bug
# DuckDB treats "value" as column identifier, not string. Must use 'value'.
# High-frequency bug: hit 3x in one session. Zero false positives on non-SQL.

INPUT=$(cat)
CMD=$(echo "$INPUT" | grep -oE '"command"\s*:\s*"[^"]*"' | head -1 | sed 's/"command"\s*:\s*"//;s/"$//')

# Only check commands that look like they contain SQL
echo "$CMD" | grep -qiE 'duckdb|\.execute\(|SELECT |INSERT |UPDATE |WHERE ' || exit 0

# Look for = "word" pattern (double-quoted string literal in SQL context)
# Match: WHERE col = "value"  or  = "compound"  or IN ("a", "b")
# Skip: legitimate uses like Python string containing SQL with proper escaping
if echo "$CMD" | grep -qE "= \"[a-zA-Z_]+\"" && ! echo "$CMD" | grep -qE "= \"[a-zA-Z_]+\"\)"; then
  echo "DuckDB gotcha: double quotes = column identifier, not string literal. Use single quotes for string values (e.g., WHERE col = 'value' not WHERE col = \"value\")."
fi
