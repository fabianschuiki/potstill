#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
# Execute all "run.sh" scripts in an entire directory tree.

function print_usage {
	echo "usage: potstill batch-run [-hafm] [-p PREFIX] [-n NAME] [-P NUM_PROCS]" >&2
}

# Parse the command line arguments.
NUM_PROCS=1
ALL=false
FAILED=false
MISSING=false
PREFIX=
NAME="run.sh"
while [ $# -gt 0 ]; do
	key="$1"

	case "$1" in
		-h|--help)
			print_usage
			echo >&2
			echo "Execute multiple characterizations in a batch." >&2
			echo >&2
			echo "Options:" >&2
			echo "  -h, --help             show this help message and exit" >&2
			echo "  -a, --all              execute all runs" >&2
			echo "  -f, --failed           execute failed runs" >&2
			echo "  -m, --missing          execute runs that have not yet been run" >&2
			echo "  -n, --name NAME        name of the file to run [\"run.sh\"]" >&2
			echo "  -P, --procs NUM_PROCS  number of parallel jobs to launch" >&2
			echo >&2
			echo "If -a is not set, this command executes each line in stdin as a separate job." >&2
			exit 1
			;;
		-a|--all) ALL=true; shift ;;
		-f|--failed) FAILED=true; shift ;;
		-m|--missing) MISSING=true; shift ;;
		-p|--prefix)
			if [ $# -lt 2 ]; then
				echo "expected prefix after $key" >&2
				exit 1
			fi
			PREFIX="$2"
			shift 2
			;;
		-n|--name)
			if [ $# -lt 2 ]; then
				echo "expected runfile name after $key" >&2
				exit 1
			fi
			NAME="$2"
			shift 2
			;;
		-P|--procs)
			if [ $# -lt 2 ]; then
				echo "expected number of jobs after $key" >&2
				exit 1
			fi
			NUM_PROCS=$2
			shift 2
			;;
		*) break ;;
	esac
done

list_runfiles() {
	if $ALL; then
		find . -mindepth 2 -name "$NAME"
	else
		cat
	fi | \
	if [ ! -z "$PREFIX" ]; then
		grep "$PREFIX/$NAME"
	else
		cat
	fi | \
	if $FAILED || $MISSING; then
		while read runfile; do
			ECFILE="$(dirname "$runfile")/exitcode"
			if [ ! -e "$ECFILE" ]; then
				$MISSING && echo "$runfile"
			elif $FAILED && [ "$(cat "$ECFILE")" -ne 0 ]; then
				echo "$runfile"
			fi
		done
	else
		cat
	fi
}

# Execute the commands.
echo "Starting batch run"
start=$(date +%s.%N)
list_runfiles | xargs -L 1 -P $NUM_PROCS potstill batch-run-one
duration=$(echo "$(date +%s.%N) - $start" | bc)
echo "Finished batch run (after $duration s)"
