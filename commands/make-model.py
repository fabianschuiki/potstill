#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script generates the simulation model for a memory macro.

import sys, os, argparse, itertools
from potstill.macro import Macro
from potstill.output.model import make_vhdl


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill make-model", description="Generate the simulation model for a memory macro.")
parser.add_argument("NADDR", type=int, help="number of address lines")
parser.add_argument("NBITS", type=int, help="number of bits")
args = parser.parse_args()


# Generate the simulation model for the macro.
macro = Macro(args.NADDR, args.NBITS)
sys.stdout.write(make_vhdl(macro))
