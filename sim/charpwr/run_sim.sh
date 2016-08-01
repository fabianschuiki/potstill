#!/bin/bash
set -e

potstill netlist TOP 2 8 > PS4X8.cir
potstill nodeset X 2 8 > PS4X8.ns
potstill char 2 8 > input.scs
cds_mmsim spectre input.scs +escchars +log spectre.out -format psfxl -raw psf +aps +lqtimeout 900 -maxw 5 -maxn 5
