#!/bin/bash
set -e

../../templates/pwrintcap.py 2 8 pwrintcap
potstill netlist TOP 2 8 > PS4X8.cir
potstill nodeset X 2 8 > PS4X8.ns
cds_mmsim spectre pwrintcap.scs +escchars +log spectre.out -format psfxl -raw pwrintcap.psf +aps +lqtimeout 900 -maxw 5 -maxn 5
