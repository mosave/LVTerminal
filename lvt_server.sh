#!/bin/sh

dir="$(dirname "$(readlink -f "$0")")"
venv="$dir/.venv_server"

do_activate () {
  if [ ! -d "$venv" ]; then
    echo "Initializing virtual environment in $venv"
    python3 -m venv "$venv"
    . "$venv/bin/activate"
    echo "Installing required modules"
    python3 -m pip install -r "$dir/requirements_server.txt"
  else
    echo "Activating virtual environment"
    . "$venv/bin/activate"
  fi
}

do_deactivate () {
  echo "Deactivating virtual environment"
  pkill -f "^python.*lvt_server"
  deactivate
}

code=42
while [ $code -eq 42 ]; do
    do_activate
    "$dir/lvt_server.py" $1 $2 $3 $4 $5 $6 $7 $8 $9
    code=$?
    do_deactivate
done

deactivate

