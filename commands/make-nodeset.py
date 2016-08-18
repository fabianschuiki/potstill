#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script generates the nodeset for a memory macro.

import sys, argparse
from potstill import nodeset


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill make-nodeset", description="Generate the nodeset for a memory macro.")
parser.add_argument("NADDR", type=int, help="number of address lines")
parser.add_argument("NBITS", type=int, help="number of bits")
parser.add_argument("-p", "--prefix", type=str, default="X", help="prefix of the instantiated circuit")
args = parser.parse_args()


# Generate the layout for the macro.
sys.stdout.write(nodeset.generate(args.prefix, args.NADDR, args.NBITS))
