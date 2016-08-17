#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
# Execute all "run.sh" scripts in an entire directory tree.

function print_usage {
	echo "usage: potstill batch-run [-h|--help] [-a|--all] [NUM_PROCS]" >&2
}

# Parse the command line arguments.
NUM_PROCS=1
ALL=false
NUM_PROCS_SET=false
while [ $# -gt 0 ]; do
	key="$1"

	case "$1" in
		-h|--help)
			print_usage
			echo >&2
			echo "Execute multiple characterizations in a batch." >&2
			echo >&2
			echo "Options:" >&2
			echo "  -h, --help  show this help message and exit" >&2
			echo "  -a, --all   run all \"run.sh\" files in this directory tree" >&2
			echo "  NUM_PROCS   number of parallel jobs to launch" >&2
			echo >&2
			echo "If -a is not set, this command executes each line in stdin as a separate job." >&2
			exit
			;;
		-a|--all)
			ALL=true
			;;
		*)
			if $NUM_PROCS_SET; then
				echo "superfluous argument $key"
				print_usage
				exit 1
			fi
			NUM_PROCS=$1
			NUM_PROCS_SET=true
			;;
	esac
	shift
done

# Execute the commands.
echo "Starting batch run"
start=$(date +%s.%N)
XARGS="xargs -L 1 -P $NUM_PROCS potstill batch-run-one"
if $ALL; then
	find . -mindepth 2 -name "run.sh" | $XARGS
else
	$XARGS
fi
duration=$(echo "$(date +%s.%N) - $start" | bc)
echo "Finished batch run (after $duration s)"
