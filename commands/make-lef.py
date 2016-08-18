#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script generates the LEF view of a memory macro.

import sys, os, argparse, itertools
from potstill.macro import Macro
from potstill.layout import Layout
from potstill.output.lef import make_lef


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill make-lef", description="Generate the LEF view of a memory macro.")
parser.add_argument("NADDR", type=int, help="number of address lines")
parser.add_argument("NBITS", type=int, help="number of bits")
args = parser.parse_args()


# Generate the layout for the macro.
macro = Macro(args.NADDR, args.NBITS)
layout = Layout(macro)
sys.stdout.write(make_lef(layout))
