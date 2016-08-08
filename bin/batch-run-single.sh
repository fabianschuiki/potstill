#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
# Execute all "run.sh" scripts in a subdirectory in parallel.

if [ $# -lt 1 ]; then
	echo "usage: batch-run-single RUNSCRIPT [ARGS...]" >&2
	exit 1
fi

echo "Starting $@"
start=$(date +%s.%N)
"$@"
status=$?
duration=$(echo "$(date +%s.%N) - $start" | bc)
if [ $status -ne 0 ]; then
	echo "Failed $@ (after $duration s)"
else
	echo "Finished $@ (after $duration s)"
fi
