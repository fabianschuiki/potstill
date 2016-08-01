#!/bin/bash
set -e

potstill netlist AD 2 > PSAD4.cir
cds_mmsim spectre input.scs +escchars +log spectre.out -format psfxl -raw psf +aps +lqtimeout 900 -maxw 5 -maxn 5
