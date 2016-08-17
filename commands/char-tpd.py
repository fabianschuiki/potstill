#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script provides the means to prepare, execute, and analyze the results of
# a propagation and transition time characterization.

import sys, os, argparse
from potstill.char.util import *
from potstill.char.tpd import Input, Run


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill char-tpd", description="Prepare, execute, and analyze the results of a propagation and transition time characterization.")
argparse_init_macro(parser)
parser.add_argument("TSLEW", type=float, help="input transition time [s]")
parser.add_argument("CLOAD", type=float, help="output load capacitance [F]")
parser.add_argument("--spectre", action="store_true", help="write SPECTRE input file to stdout")
parser.add_argument("--ocean", action="store_true", help="write OCEAN input file to stdout")
args = parser.parse_args()


# Create the input files.
macro = argparse_get_macro(args)
inp = Input(macro, args.TSLEW, args.CLOAD)

if args.spectre:
	sys.stdout.write(inp.make_spectre())
	sys.exit(0)
if args.ocean:
	sys.stdout.write(inp.make_ocean())
	sys.exit(0)

# Execute the run.
run = Run(inp)
run.run()
