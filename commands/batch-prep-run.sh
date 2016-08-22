#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
set -e

if [ $# -lt 5 ]; then
	echo "usage: batch-prep-run NUM_ADDR NUM_BITS VDD TEMP CHAR ARGS..." >&2
	exit 1
fi
num_addr=$1
num_bits=$2
vdd=$3
temp=$4
char=$5

echo "#!/bin/bash" > prep.sh
echo "potstill batch-prep-run $@" >> prep.sh
chmod +x prep.sh

echo "#!/bin/bash" > run.sh
echo "cd \$(dirname \${BASH_SOURCE[0]})" >> run.sh
echo "if [ -e exitcode ]; then rm exitcode; fi" >> run.sh
echo "if [ \$# -eq 0 ]; then args=\"-r\"; else args=\"\$@\"; fi" >> run.sh
echo "start=\$(date +%s.%N)" >> run.sh

case $char in
pwr|pwrck|tpd|tsuho)
	echo "potstill char-$char $num_addr $num_bits $vdd $temp ${@:6} \"\$@\"" >> run.sh
	;;
*)
	echo "potstill char $num_addr $num_bits --vdd $vdd --temp $temp $char ${@:6} \$args" >> run.sh
	;;
esac

if [ $char = tsuho ]; then
	echo "cat setup.csv hold.csv > results.csv" >> run.sh
fi

echo "status=\$?" >> run.sh
echo "echo \$status > exitcode" >> run.sh
echo "echo \"\$(date +%s.%N) - \$start\" | bc > duration" >> run.sh
echo "exit \$status" >> run.sh
chmod +x run.sh
