#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
set -e

TSLEWS="10e-12 50e-12 200e-12"
CLOADS="1e-15 10e-15 50e-15"

if [ $# -lt 5 ]; then
	echo "usage: batch-prep-char NUM_ADDR NUM_BITS VDD TEMP CHAR" >&2
	echo "$@" >&2
	echo "$PWD" >&2
	exit 1
fi
char=$5

echo "#!/bin/bash" > prep.sh
echo "potstill batch-prep-char $@" >> prep.sh
chmod +x prep.sh

echo "#!/bin/bash" > collect.sh
echo "cd \$(dirname \${BASH_SOURCE[0]})" >> collect.sh
echo "potstill collect results.csv > results.csv" >> collect.sh
chmod +x collect.sh

function make_run {
	if [ ! -d "$1" ]; then
		mkdir "$1"
	fi
	pushd "$1" > /dev/null
	potstill batch-prep-run "${@:2}"
	popd > /dev/null
}

case $char in
pwrck|pwrintcap)
	for tslew in $TSLEWS; do
		make_run "tslew=$tslew" $@ $tslew
	done
	;;
pwrout|trdwr)
	for tslew in $TSLEWS; do
		for cload in $CLOADS; do
			make_run "tslew=$tslew,cload=$cload" $@ --tslew $tslew --cload $cload
		done
	done
	;;
tsuho)
	for tslewck in $TSLEWS; do
		for tslewpin in $TSLEWS; do
			make_run "tslewck=$tslewck,tslewpin=$tslewpin" $@ --tslewck $tslewck --tslewpin $tslewpin
		done
	done
	;;
*)
	echo "unknown characterization \"$char\"" >&2
	exit 1
	;;
esac
