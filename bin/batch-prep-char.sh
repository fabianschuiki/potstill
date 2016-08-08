#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
set -e

if [ $# -lt 7 ]; then
	echo "usage: batch-prep-char NUM_ADDR NUM_BITS VDD TEMP CHAR \"TSLEW...\" \"CLOAD...\"" >&2
	exit 1
fi
num_addr=$1
num_bits=$2
vdd=$3
temp=$4
char=$5
tslew="$6"
cload="$7"

echo "#!/bin/bash" > prep.sh
echo "potstill batch-prep-char $num_addr $num_bits $vdd $temp $char \"$tslew\" \"$cload\"" >> prep.sh
chmod +x prep.sh

echo "#!/bin/bash" > run.sh
echo "cd \$(dirname \${BASH_SOURCE[0]})" >> run.sh
echo "if [ -e exitcode ]; then rm exitcode; fi" >> run.sh
echo "if [ \$# -eq 0 ]; then args=\"-r\"; else args=\"\$@\"; fi" >> run.sh
echo "start=\$(date +%s.%N)" >> run.sh

PS="potstill char $num_addr $num_bits --vdd $vdd --temp $temp"
PSTAIL="\$args &> potstill.out"

case $char in
pwrck)
	echo "$PS pwrck $tslew $PSTAIL" >> run.sh
	;;
pwrintcap)
	echo "$PS pwrintcap $tslew $PSTAIL" >> run.sh
	;;
pwrout)
	echo "$PS pwrout --tslew $tslew --cload $cload $PSTAIL" >> run.sh
	;;
trdwr)
	echo "$PS trdwr --tslew $tslew --cload $cload $PSTAIL" >> run.sh
	;;
tsuho)
	echo "$PS tsuho --tslewck $tslew --tslewpin $tslew $PSTAIL" >> run.sh
	;;
*)
	echo "unknown characterization \"$char\"" >&2
	exit 1
	;;
esac

echo "status=\$?" >> run.sh
echo "echo \$status > exitcode" >> run.sh
echo "echo \"\$(date +%s.%N) - \$start\" | bc > duration" >> run.sh
echo "exit \$status" >> run.sh
chmod +x run.sh

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
