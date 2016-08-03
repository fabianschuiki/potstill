#!/bin/bash
set -e

../../templates/pwrout.py 2 8 pwrout
cat pwrout.ocn > analysis.ocn
echo "exit" >> analysis.ocn
cds_ic6 ocean -nograph < analysis.ocn
