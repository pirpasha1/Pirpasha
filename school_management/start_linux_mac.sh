#!/usr/bin/env bash
# Start the School Management System on Linux or macOS:  ./start_linux_mac.sh
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "First run: setting up, please wait..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --quiet -r requirements.txt
fi
exec .venv/bin/python run.py "$@"
