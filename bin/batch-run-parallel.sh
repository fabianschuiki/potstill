#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
# Execute all "run.sh" scripts in a subdirectory in parallel.

if [ $# -ne 1 ]; then
	echo "usage: batch-run-parallel NUM_PROCS" >&2
	exit 1
fi

echo "Starting batch run"
start=$(date +%s.%N)
find -name "run.sh" -print0 | xargs -0 -n 1 -P $1 potstill batch-run-single
duration=$(echo "$(date +%s.%N) - $start" | bc)
echo "Finished batch run (after $duration s)"
