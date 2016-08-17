#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
set -e

if [ $# -ne 4 ]; then
	echo "usage: batch-prep-macro NUM_ADDR NUM_BITS VDD TEMP" >&2
	exit 1
fi

echo "#!/bin/bash" > prep.sh
echo "potstill batch-prep-macro $@" >> prep.sh
chmod +x prep.sh

make_char() {
	if [ ! -d $1 ]; then
		mkdir $1
	fi
	pushd $1 > /dev/null
	potstill batch-prep-char "${@:2}" $1
	popd > /dev/null
}

make_char pwrck $@
make_char pwrintcap $@
make_char pwrout $@
# make_char trdwr $@
make_char tpd $@
make_char tsuho $@
