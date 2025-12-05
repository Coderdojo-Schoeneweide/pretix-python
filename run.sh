#!/bin/bash

PROJ="$(cd "$(dirname "$0")" && pwd)"

case "$1" in
    r)	
		source "$PROJ/venv/bin/activate"
        PYTHONPATH="$PROJ/pretix-python" python3 "$PROJ/main.py"
        ;;
    t)	
		source "$PROJ/venv/bin/activate"
        PYTHONPATH="$PROJ/pretix-python" ipython --no-banner
        ;;
    -h)
        echo "--------------------------"
        echo "| How to use this script |"
        echo "--------------------------"
        echo ""
        echo "r - lets you run the programm in normal mode"
        echo "t - lets you run the programm in test mode"
        ;;
    *)
        echo "invalid option: \"$1\" use -h for help"
        ;;
esac
