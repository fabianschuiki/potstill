#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script provides the means to prepare, execute, and analyze the results of
# a power characterization.

import sys, os, argparse
from potstill.char.util import CommonArgs
from potstill.char.pwr import Input, Run


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill char-pwr", description="Prepare, execute, and analyze the results of a power characterization.")
common = CommonArgs(parser)
parser.add_argument("TSLEW", type=float, help="input transition time [s]")
parser.add_argument("CLOAD", type=float, help="output load capacitance [F]")
common.parse()

# Create the input files.
macro = common.get_macro()
inp = Input(macro, common.args.TSLEW, common.args.CLOAD, **common.get_input_kwargs())
common.handle_input(inp)

# Execute the run.
run = Run(inp, **common.get_run_kwargs())
common.handle_run(run)
run.run()
