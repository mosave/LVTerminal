#!/bin/bash

dir="$(dirname "$(readlink -f "$0")")"
venv="$dir/.venv_client"

while [ $# -ne 0 ]
do
    case "$1" in
        -i)
            init="Y"
            ;;
        --initialize)
            init="Y"
            ;;
    esac
    shift
done

do_activate () {
  if [ "$init" ] || [ ! -d "$venv" ] ; then
    echo "Initializing virtual environment in $venv"
    python3 -m venv "$venv"
    . "$venv/bin/activate"
    echo "Installing required modules"
    python3 -m pip install -r "$dir/requirements_client.txt"
  else
    echo "Activating virtual environment"
    . "$venv/bin/activate"
  fi
}

do_deactivate () {
  echo "Deactivating virtual environment"
  pkill -f "^python.*lvt_client"
  deactivate
}

do_activate

"$dir/lvt_client.py" $1 $2 $3 $4 $5 $6 $7 $8 $9
code=$?

# Reboot device
if [ $code -eq 42 ]; then
  sudo reboot
fi

do_deactivate

# Old style: reboot lvt client only:
#code=42
#while [ $code -eq 42 ] ; do
#    do_activate
#    "$dir/lvt_client.py" $1 $2 $3 $4 $5 $6 $7 $8 $9
#    code=$?
#    do_deactivate
#done

