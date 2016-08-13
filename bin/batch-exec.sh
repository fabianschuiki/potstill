#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
# Execute all instances of a certaing file in an entire directory tree.

if [ $# -lt 1 ]; then
	echo "usage: potstill batch-exec FILENAME [FILENAME ...]" >&2
	exit 1
fi

for filename in "$@"; do
	find . -name "$filename" | while read f; do
		echo "$f"
		"$f"
	done
done
