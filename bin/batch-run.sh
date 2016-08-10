#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
# Execute all "run.sh" scripts in an entire directory tree.

if [ $# -lt 1 ]; then
	NUM_PROCS=1
else
	NUM_PROCS=$1
fi

echo "Starting batch run"
start=$(date +%s.%N)
find . -mindepth 2 -name "run.sh" -print0 | xargs -0 -n 1 -P $NUM_PROCS potstill batch-run-single
duration=$(echo "$(date +%s.%N) - $start" | bc)
echo "Finished batch run (after $duration s)"
