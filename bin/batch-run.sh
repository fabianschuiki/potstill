#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
# Execute all "run.sh" scripts in a subdirectory.

total_status=0

find -name "run.sh" | while read RUN; do
	DIR="$(dirname $RUN)"
	echo "Running $DIR"
	pushd "$DIR" > /dev/null
	./run.sh > /dev/null
	status=$?
	if [ $status -ne 0 ]; then
		echo "Run $DIR failed"
		total_status=$status
	fi
	popd > /dev/null
done

if [ $total_status -ne 0 ]; then
	echo "Some runs failed" >&2
else
	echo "All runs successful" >&2
fi
exit $total_status
