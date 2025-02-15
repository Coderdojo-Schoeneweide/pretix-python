#!/bin/bash

case "$1" in
	r)
		PYTHONPATH=pretix-python ./tests/main.py
		;;
	t)
		PYTHONPATH=pretix-python ipython --no-banner
		;;
	*)
		echo "invalid option: \"$1\""
		;;
esac
