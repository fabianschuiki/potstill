#!/bin/bash
set -e

../../templates/tho.py 2 8 ../tsu/tsu.csv tho
cat tho.ocn > analysis.ocn
echo "exit" >> analysis.ocn
cds_ic6 ocean -nograph < analysis.ocn
