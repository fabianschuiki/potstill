#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki

if [ $# -lt 1 ] || [ $1 == "-h" ] || [ $1 == "--help" ]; then
	echo "usage: batch-run-one RUNSCRIPT [ARGS...]" >&2
	exit 1
fi

echo "Starting $@"
start=$(date +%s.%N)
"$@" &> $(dirname $1)/run.out
status=$?
duration=$(echo "$(date +%s.%N) - $start" | bc)
echo $status > $(dirname $1)/exitcode
echo $duration > $(dirname $1)/duration
if [ $status -ne 0 ]; then
	echo "Failed $@ (after $duration s)"
else
	echo "Finished $@ (after $duration s)"
fi
