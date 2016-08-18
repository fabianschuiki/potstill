#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script generates the netlist for a memory macro.

import sys, argparse
from potstill import netlist


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill make-netlist", description="Generate the netlist for a memory macro.")
parser.add_argument("NADDR", type=int, help="number of address lines")
parser.add_argument("NBITS", type=int, help="number of bits")
args = parser.parse_args()


# Generate the layout for the macro.
sys.stdout.write(netlist.generate(args.NADDR, args.NBITS))
