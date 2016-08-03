#!/bin/bash
set -e

../../templates/pwrout.py 2 8 pwrout
potstill netlist TOP 2 8 > PS4X8.cir
potstill nodeset X 2 8 > PS4X8.ns
cds_mmsim spectre pwrout.scs +escchars +log spectre.out -format psfxl -raw pwrout.psf +aps +lqtimeout 900 -maxw 5 -maxn 5
