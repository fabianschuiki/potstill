#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
set -e

if [ $# -ne 2 ]; then
	echo "usage: batch-prep-ops NUM_ADDR NUM_BITS" >&2
	exit 1
fi

echo "#!/bin/bash" > prep.sh
echo "potstill batch-prep-ops $@" >> prep.sh
chmod +x prep.sh

for element in "1.2 25" "1.08 125" "1.32 0"; do
	opcond=($element)
	vdd=${opcond[0]}
	temp=${opcond[1]}
	OP_NAME="vdd=$vdd,temp=$temp"
	if [ ! -d $OP_NAME ]; then
		mkdir $OP_NAME
	fi
	pushd $OP_NAME > /dev/null
	potstill batch-prep-macro "$@" $vdd $temp
	popd > /dev/null
done
