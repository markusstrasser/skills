#!/bin/bash
# Regression for bin/rg: a socket stdin must not block a pathless search; a pipe still feeds rg.
# The real rg on the same socket is the negative control: it blocks (the hazard the wrapper exists for).
set -u
here=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
echo needle > "$tmp/a.txt"
fail=0

on_socket() {  # run "$1 -l needle" in $tmp with a never-closing socket as stdin; print its stdout or TIMEOUT
  (cd "$tmp" && uv run --no-project python3 -c '
import socket, subprocess, sys
a, b = socket.socketpair()
try:
    r = subprocess.run([sys.argv[1], "-l", "needle"], stdin=a, capture_output=True, text=True, timeout=float(sys.argv[2]))
    print(r.stdout.strip())
except subprocess.TimeoutExpired:
    print("TIMEOUT")
' "$1" "$2")
}

out=$(on_socket "$here/bin/rg" 10)
if [ "$out" = "a.txt" ]; then echo "✓ socket stdin, no path: the wrapper searched the directory"; else echo "✗ socket stdin: got '$out'"; fail=1; fi

out=$(on_socket /opt/homebrew/bin/rg 3)
if [ "$out" = "TIMEOUT" ]; then echo "✓ control: the real rg blocks on the same socket"; else echo "! the real rg no longer blocks on a socket stdin (got '$out'): the wrapper can be retired"; fi

out=$(printf 'needle\nhay\n' | "$here/bin/rg" needle)
if [ "$out" = "needle" ]; then echo "✓ pipe stdin is still searched"; else echo "✗ pipe stdin: got '$out'"; fail=1; fi

out=$(cd "$tmp" && "$here/bin/rg" -l needle . < /dev/null)
if [ "$out" = "./a.txt" ]; then echo "✓ explicit path"; else echo "✗ explicit path: got '$out'"; fail=1; fi

exit $fail
