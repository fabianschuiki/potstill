#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script produces all output files for a memory macro of given
# size.

import sys, os, argparse
from potstill import netlist, nodeset
from potstill.macro import Macro
from potstill.layout import Layout
from potstill.timing import Timing
from potstill.output.lib import make_lib
from potstill.output.lef import make_lef
from potstill.output.model import make_vhdl
from potstill.output.gds import make_gds


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill make", description="Generate a memory macro.")
parser.add_argument("NADDR", type=int, help="number of address lines")
parser.add_argument("NBITS", type=int, help="number of bits")
parser.add_argument("-o", "--outname", metavar="OUT", type=str, help="name of the output files")
parser.add_argument("--nodeset-prefix", type=str, default="X", help="prefix of the circuit in the nodeset file")
args = parser.parse_args()


# Generate the layout and timings for the macro.
macro = [
	Macro(args.NADDR, args.NBITS, vdd=1.2, temp=25),
	Macro(args.NADDR, args.NBITS, vdd=1.08, temp=125),
	Macro(args.NADDR, args.NBITS, vdd=1.32, temp=0),
]
sys.stderr.write("# Calculating layout\n")
layout = Layout(macro[0])
sys.stderr.write("# Calculating timing\n")
timings = [Timing(m) for m in macro]
prefix = args.outname or macro[0].name

def open_outfile(suffix):
	name = prefix+suffix
	sys.stdout.write(name+"\n")
	return open(name, "w")


# Generate GDS file.
sys.stdout.write(prefix+".gds\n")
make_gds(layout, prefix+".gds")

# Generate LEF file.
with open_outfile(".lef") as f:
	f.write(make_lef(layout))

# Generate LIB files.
for timing in timings:
	with open_outfile("_"+timing.suffix+".lib") as f:
		f.write(make_lib(timing, layout))

# Generate netlist file.
with open_outfile(".cir") as f:
	f.write(netlist.generate(args.NADDR, args.NBITS))

# Generate nodeset file.
with open_outfile(".ns") as f:
	f.write(nodeset.generate(args.nodeset_prefix, args.NADDR, args.NBITS))

# Generate the simulation model.
with open_outfile(".vhd") as f:
	f.write(make_vhdl(macro[0]))
