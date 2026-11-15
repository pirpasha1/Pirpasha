#!/usr/bin/env sh
# Start the Payroll & Attendance application (macOS / Linux)
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
python3 -m streamlit run app.py
