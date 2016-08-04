#!/bin/bash
set -e

../../templates/tsu.py 2 8 tsu
potstill netlist TOP 2 8 > PS4X8.cir
potstill nodeset X 2 8 > PS4X8.ns
cds_mmsim spectre tsu.scs +escchars +log spectre.out -format psfxl -raw tsu.psf ++aps
