#!/bin/bash
set -e

../../templates/tho.py 2 8 ../tsu/tsu.csv tho
potstill netlist TOP 2 8 > PS4X8.cir
potstill nodeset X 2 8 > PS4X8.ns
cds_mmsim spectre tho.scs +escchars +log spectre.out -format psfxl -raw tho.psf ++aps
