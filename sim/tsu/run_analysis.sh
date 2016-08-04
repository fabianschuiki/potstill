#!/bin/bash
set -e

../../templates/tsu.py 2 8 tsu
cat tsu.ocn > analysis.ocn
echo "exit" >> analysis.ocn
cds_ic6 ocean -nograph < analysis.ocn
