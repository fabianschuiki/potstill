#!/bin/bash
# Copyright (c) 2016 Fabian Schuiki
set -e

echo "#!/bin/bash" > prep.sh
echo "potstill batch-prep-all" >> prep.sh
chmod +x prep.sh

outdir=output
echo "#!/bin/bash" > merge.sh
echo "cd \$(dirname \${BASH_SOURCE[0]})" >> merge.sh
echo "if [ ! -d $outdir ]; then mkdir $outdir; fi" >> merge.sh
chmod +x merge.sh

for num_addr in {2..7}; do
	echo "potstill batch-merge $num_addr $outdir 4 32 128" >> merge.sh

	for num_bits in 4 32 128; do
		MACRO_NAME=$(printf 'PS%dX%d' $((2**$num_addr)) $num_bits)
		echo "$MACRO_NAME"
		if [ ! -d $MACRO_NAME ]; then
			mkdir $MACRO_NAME
		fi
		pushd $MACRO_NAME > /dev/null
		potstill batch-prep-ops $num_addr $num_bits
		popd > /dev/null
	done
done
