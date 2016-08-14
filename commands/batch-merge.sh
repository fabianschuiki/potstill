#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
set -e

if [ $# -lt 3 ]; then
	echo "usage: potstill batch-merge NUM_ADDR OUTDIR NUM_BITS [NUM_BITS ...]" >&2
	exit 1
fi
num_addr=$1
num_words=$((2**$num_addr))
outdir=$2

if [ ! -d $outdir/$num_words ]; then
	mkdir $outdir/$num_words
fi

CMD="potstill collect -r"
for nb in "${@:3}"; do
	MACRO_NAME=$(printf 'PS%dX%d' $num_words $nb)
	CMD="$CMD -d $MACRO_NAME num_bits=$nb"
done

for char in pwrck pwrintcap pwrout trdwr tsuho; do
	$CMD $char.csv > $outdir/$num_words/$char.csv
done
