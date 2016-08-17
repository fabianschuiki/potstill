#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script gathers the contents of a bunch of CSV files into one, prefixing
# the information with additional columns whose values it extracts from the
# name of the subdirectory where the corresponding rows were found.

import sys, csv, os, argparse
from collections import OrderedDict


# Parse the command line arguments.
parser = argparse.ArgumentParser(prog="potstill collect", description="Collect results from multiple parametric sweep runs.")
parser.add_argument("FILENAME", type=str, help="name of the file to collect")
parser.add_argument("-r", "--rows", action="store_true", help="treat first line as header, others as data")
parser.add_argument("-d", "--dir", metavar=("DIR", "PARAMS"), nargs=2, action="append", default=[])
args = parser.parse_args()


def dirs():
	if len(args.dir) == 0:
		for d in os.listdir():
			yield (d,d)
	else:
		for d in args.dir:
			yield d


# Make a list of all files that need to be merged into one.
rows = list()
keys = list()
keys_seen = set()
for (d,dp) in dirs():
	f = d+"/"+args.FILENAME
	if os.path.isdir(d) and os.path.exists(f):

		# Split the directory name into parameter names and values.
		params = OrderedDict([a.split("=") for a in dp.split(",")])

		# Read the file.
		new_rows = list()
		with open(f) as fd:
			rd = csv.reader(fd)
			if args.rows:
				columns = next(rd)
				for row in rd:
					data = params.copy()
					data.update(OrderedDict(zip(columns,row)))
					new_rows.append(data)
			else:
				data = params.copy()
				data.update(OrderedDict([(x[0], float(x[1])) for x in rd]))
				new_rows.append(data)

		# Merge in the data.
		for row in new_rows:
			rows.append(row)
			for k in row.keys():
				if k not in keys_seen:
					keys.append(k)
					keys_seen.add(k)


# Output the merged data as CSV.
wr = csv.writer(sys.stdout)
wr.writerow(keys)
for r in rows:
	row = [(r[k] if k in r else None) for k in keys]
	wr.writerow(row)
