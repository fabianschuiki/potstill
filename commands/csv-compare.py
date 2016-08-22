#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script implements comparison between multiple CSV files. The files are
# expected to contain two columns, one with field names and one with actual
# values. The tool pairs up the fields, formats each in engineering notation,
# and produces a percentage comparison.

import sys, csv, math
from collections import OrderedDict

if len(sys.argv) < 2:
	sys.stderr.write("usage: potstill csv-compare BASELINE [OTHER ...]\n")
	sys.exit(1)


# Read the input files.
keys = list()
keys_seen = set()

def read_file(filename):
	with open(filename) as f:
		rd = csv.reader(f)
		data = OrderedDict([(x[0], float(x[1])) for x in rd])

	for k in data.keys():
		if k not in keys_seen:
			keys.append(k)
			keys_seen.add(k)

	return data

baseline = read_file(sys.argv[1])
optimized = [read_file(x) for x in sys.argv[2:]]


# Format the data and build output columns.
class Column(object):
	def __init__(self, rows):
		super(Column, self).__init__()
		self.rows = rows
		self.width = max(*[(len(x) if x is not None else 0) for x in rows])

	def padded(self):
		return [(x or "").ljust(self.width) for x in self.rows]

def format_abs(v):
	if v == 0:
		return "0"
	log = math.log10(v)
	base = int(math.floor(log/3))*3
	return "%.4ge%d" % (v / 10**base, base)

def format_rel(bl, ot):
	if ot == 0:
		return ""
	if bl == 0:
		return "--"
	d = ot/bl-1
	if d == 0:
		return " 0%"
	elif d < 0:
		return "-%.3g%%" % (-d*100)
	else:
		return "+%.3g%%" % (d*100)

columns = list()
columns.append(Column(keys))

def make_sep_column():
	columns.append(Column(["|" for k in keys]))
def make_abs_column(data):
	columns.append(Column([(format_abs(data[k]) if k in data else None) for k in keys]))
def make_rel_column(data):
	columns.append(Column([(format_rel(baseline[k], data[k]) if k in data and k in baseline else None) for k in keys]))

make_sep_column()
make_abs_column(baseline)
for o in optimized:
	make_sep_column()
	make_abs_column(o)
	make_rel_column(o)


# Assemble output table.
lines = zip(*[c.padded() for c in columns])
for l in lines:
	print(" ".join(l))
