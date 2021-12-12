#!/bin/sh

dir="$(dirname "$(readlink -f "$0")")"
venv="$dir/.venv_client"

if [ ! -d "$venv" ]; then
  echo "Initializing virtual environment in $venv"
  python3 -m venv "$venv"
  . "$venv/bin/activate"
  echo "Installing required modules"
  python3 -m pip install -r "$dir/requirements_client.txt"
else
  . "$venv/bin/activate"
fi

code=42
while [ $code -eq 42 ]; do
    "$dir/lvt_client.py" $1 $2 $3 $4 $5 $6 $7 $8 $9
    code=$?
done

deactivate