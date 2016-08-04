#!/bin/bash
set -e

../../templates/pwrck.ocn.py 2 > pwrck.ocn
cat pwrck.ocn > analysis.ocn
echo "exit" >> analysis.ocn
cds_ic6 ocean -nograph < analysis.ocn
