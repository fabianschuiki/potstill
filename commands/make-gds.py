#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script generates GDS layout data for a memory macro.

import sys, os, argparse
from potstill.macro import Macro
from potstill.layout import Layout
from potstill.output.gds import make_gds, make_phalanx_input


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill make-gds", description="Generate the GDS layout data of a memory macro.")
parser.add_argument("NADDR", type=int, help="number of address lines")
parser.add_argument("NBITS", type=int, help="number of bits per word")
parser.add_argument("-o", "--output", metavar="GDSFILE", type=str, help="name of the output GDS file")
parser.add_argument("-p", "--phalanx", action="store_true", help="write Phalanx input file to stdout")
args = parser.parse_args()


# Calculate the layout.
macro = Macro(args.NADDR, args.NBITS)
layout = Layout(macro)
filename = args.output or (macro.name+".gds")


# Dump the input file to stdout if requested.
if args.phalanx:
	sys.stdout.write(make_phalanx_input(layout, filename))
	sys.exit(0)


# Generate GDS output.
make_gds(layout, filename)
