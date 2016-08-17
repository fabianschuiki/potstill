#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script provides to means to prepare, execute, and analyze the results of
# a setup and hold time characterization.

import sys, os, argparse
from potstill.char.util import *
from potstill.char.tsuho import SetupInput, HoldInput, SetupRun, HoldRun, SetupHoldRun


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill char-tsuho", description="Prepare, execute, and analyze the results of a setup and hold time characterization.")
argparse_init_macro(parser)
parser.add_argument("TSLEWCK", type=float, help="input transition time [s]")
parser.add_argument("TSLEWPIN", type=float, help="input transition time [s]")
parser.add_argument("--setup", action="store_true", help="only run setup time analysis")
parser.add_argument("--hold", action="store_true", help="only run hold time analysis")
parser.add_argument("--spectre", action="store_true", help="write SPECTRE input file to stdout")
parser.add_argument("--analyze", metavar="PSFASCII", type=str, help="analyze results")
args = parser.parse_args()


# Create the input files.
macro = argparse_get_macro(args)
setup_run = SetupRun(macro, args.TSLEWCK, args.TSLEWPIN)
hold_run  = HoldRun(macro, args.TSLEWCK, args.TSLEWPIN)

if args.setup:
	inp = SetupInput(macro, args.TSLEWCK, args.TSLEWPIN)
	run = setup_run
elif args.hold:
	inp = HoldInput(macro, args.TSLEWCK, args.TSLEWPIN)
	run = hold_run
else:
	inp = None
	run = SetupHoldRun(macro, args.TSLEWCK, args.TSLEWPIN)

if args.spectre:
	if inp is None:
		sys.stderr.write("specify either --setup or --hold in conjunction with --spectre\n")
		sys.exit(1)
	sys.stdout.write(inp.make_spectre())
	sys.exit(0)

if args.analyze is not None:
	if inp is None:
		sys.stderr.write("specify either --setup or --hold in conjunction with --analyze\n")
		sys.exit(1)
	print(inp.analyze(args.analyze))
	sys.exit(0)

run.run()
