#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script maps a nodeset file associated with a netlist before parasitic
# extraction to the nodes after parasitic extraction.

import sys, os, re, argparse


# Parse command line arguments.
parser = argparse.ArgumentParser(prog="potstill remap-nodeset", description="Map the nodeset of a netlist to its post parasitic extraction equivalent.")
parser.add_argument("NODESET", type=str, help="nodeset file to remap")
parser.add_argument("NETLIST", type=str, help="parasitic extraction netlist [*.pxi]")
parser.add_argument("-p", "--prefix", type=str, help="subckt prefix used in the nodeset file", default="X")
args = parser.parse_args()


# Load the nodeset file and convert it into a lookup table.
nodesets = dict()
with open(args.NODESET) as f:
	for line in f:

		# Skip empty lines.
		line = line.strip()
		if len(line) == 0:
			continue

		# Extract the nodeset path and value.
		(name,value) = line.split()
		if not name.startswith(args.prefix+"."):
			continue
		name = name[len(args.prefix)+1:].replace(".", "/").upper()
		nodesets[name] = value


# Generator that joins lines starting with a "+" with the preceding line. Also
# strips away comments and empty lines as a side-effect.
def collapse_plus_lines(it):
	line = None
	for l in it:
		l = l.split("*")[0].strip() # strip comments
		if len(l) == 0:
			continue
		if l.startswith("+"):
			line += l[1:]
		else:
			if line is not None:
				yield line
			line = l
	if line is not None:
		yield line


# Read the netlist and spawn the nodesets for each subckt that corresponds to a
# net.
unhandled_nodesets = set(nodesets.keys())
net_regex = re.compile('(.*?%(.*?))\s')
with open(args.NETLIST) as f:
	for line in collapse_plus_lines(f):

		# Look for subcircuit instantiations that replace nets.
		match = net_regex.match(line)
		if match is None:
			continue
		name = match.group(1)
		net = match.group(2)

		# Find any potential nodesets for this net subcircuit and apply the
		# nodeset to all terminals.
		try:
			value = nodesets[net]
		except KeyError as e:
			continue

		for terminal in line.split()[1:-1]:
			sys.stdout.write("%s.%s\t%s\n" % (args.prefix, terminal, value))
		unhandled_nodesets.remove(net)


for uhn in unhandled_nodesets:
	sys.stderr.write("# unmapped nodeset %s" % uhn)

sys.exit(1 if len(unhandled_nodesets) > 0 else 0)
