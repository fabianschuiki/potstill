#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
# Execute all "collect.sh" scripts in an entire directory tree.

find . -mindepth 2 -name "collect.sh" | while read f; do
	echo "$f"
	"$f"
done
