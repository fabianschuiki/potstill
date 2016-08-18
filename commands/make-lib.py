#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
import sys, os, argparse, itertools
from potstill.macro import Macro
from potstill.timing import Timing
from potstill.layout import Layout
from potstill.output.lib import make_lib


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill make-lib", description="Generate the LIB view of a memory macro.")
parser.add_argument("NADDR", type=int, help="number of address lines")
parser.add_argument("NBITS", type=int, help="number of bits per word")
parser.add_argument("VDD", type=float, help="supply voltage [V]", nargs="?")
parser.add_argument("TEMP", type=float, help="junction temperature [°C]", nargs="?")
args = parser.parse_args()


# Generate and output the LIB file.
macro = Macro(args.NADDR, args.NBITS)
timing = Timing(macro)
layout = Layout(macro)
sys.stdout.write(make_lib(timing, layout))
