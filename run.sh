#!/bin/bash

case "$1" in
	r)
		PYTHONPATH=pretix-python ./main.py
		;;
	t)
		PYTHONPATH=pretix-python ipython --no-banner
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
