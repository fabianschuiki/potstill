#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
set -e

TSLEW="10e-12 50e-12 200e-12"
CLOAD="1e-15 10e-15 50e-15"

if [ $# -ne 4 ]; then
	echo "usage: batch-prep-macro NUM_ADDR NUM_BITS VDD TEMP" >&2
	exit 1
fi
num_addr=$1
num_bits=$2
vdd=$3
temp=$4

echo "#!/bin/bash" > prep.sh
echo "potstill batch-prep-macro $num_addr $num_bits $vdd $temp" >> prep.sh
chmod +x prep.sh

make_run() {
	if [ ! -d $1 ]; then
		mkdir $1
	fi
	pushd $1 > /dev/null
	potstill batch-prep-char $num_addr $num_bits $vdd $temp $1 "$TSLEW" "$CLOAD"
	popd > /dev/null
}

make_run pwrck
make_run pwrintcap
make_run pwrout
make_run trdwr
make_run tsuho

# echo "#!/bin/bash" > run.sh
# echo "cd \$(dirname \${BASH_SOURCE[0]})" >> run.sh
# echo "if [ -e exitcode ]; then rm exitcode; fi" >> run.sh
# echo "start=\$(date +%s.%N)" >> run.sh
# echo "potstill char $num_addr $num_bits --vdd $vdd --temp $temp all --tslew 10e-12 50e-12 200e-12 --cload 1e-15 10e-15 50e-15 \$@ &> potstill.out" >> run.sh
# echo "status=\$?" >> run.sh
# echo "echo \$status > exitcode" >> run.sh
# echo "echo \"\$(date +%s.%N) - \$start\" | bc > exectime" >> run.sh
# echo "exit \$status" >> run.sh
# chmod +x run.sh
