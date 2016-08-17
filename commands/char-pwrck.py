#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script provides the means to prepare, execute, and analyze the results of
# an internal power characterization of the clock pin.

import sys, os, argparse
from potstill.char.util import *
from potstill.char.pwrck import Input, Run


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill char-pwrck", description="Prepare, execute, and analyze the results of an internal power characterization of the clock pin.")
argparse_init_macro(parser)
parser.add_argument("TSLEW", type=float, help="input transition time [s]")
parser.add_argument("--spectre", action="store_true", help="write SPECTRE input file to stdout")
parser.add_argument("--ocean", action="store_true", help="write OCEAN input file to stdout")
args = parser.parse_args()


# Create the input files.
macro = argparse_get_macro(args)
inp = Input(macro, args.TSLEW)

if args.spectre:
	sys.stdout.write(inp.make_spectre())
	sys.exit(0)
if args.ocean:
	sys.stdout.write(inp.make_ocean())
	sys.exit(0)

# Execute the run.
run = Run(inp)
run.run()
