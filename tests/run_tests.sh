#!/usr/bin/env bash
# Compiles the pure-Java core and runs the tests + backtest. Needs only a JDK (8+).
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="$(mktemp -d)"
javac --release 8 -encoding UTF-8 -d "$OUT" \
  app/src/main/java/com/localguard/autoreply/core/*.java tests/GuardTests.java
java -cp "$OUT" GuardTests
