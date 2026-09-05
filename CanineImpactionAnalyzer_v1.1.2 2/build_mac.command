#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "Canine Impaction Analyzer" \
  main.py

echo
echo "BUILD COMPLETE"
echo "Open: dist/Canine Impaction Analyzer.app"
