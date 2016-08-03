#!/bin/bash
set -e

../../templates/pwrintcap.py 2 8 pwrintcap
cat pwrintcap.ocn > analysis.ocn
echo "exit" >> analysis.ocn
cds_ic6 ocean -nograph < analysis.ocn
