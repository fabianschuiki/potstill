# Copyright (c) 2016 Fabian Schuiki
import sys, csv, os
import argparse
from collections import OrderedDict


parser = argparse.ArgumentParser(prog="potstill collect", description="Collect results from multiple parametric sweep runs.")
parser.add_argument("FILENAME", type=str, help="Name of the file to collect")
args = parser.parse_args()


# Make a list of all files that need to be merged into one.
rows = list()
keys = list()
keys_seen = set()
for d in os.listdir():
	f = d+"/"+args.FILENAME
	if os.path.isdir(d) and os.path.exists(f):

		# Split the directory name into parameter names and values.
		data = OrderedDict([a.split("=") for a in d.split(",")])

		# Read the file.
		with open(f) as fd:
			rd = csv.reader(fd)
			data.update(OrderedDict([(x[0], float(x[1])) for x in rd]))

		# Merge in the data.
		rows.append(data)
		for k in data.keys():
			if k not in keys_seen:
				keys.append(k)
				keys_seen.add(k)


# Output the merged data as CSV.
wr = csv.writer(sys.stdout)
wr.writerow(keys)
for r in rows:
	row = [(r[k] if k in r else None) for k in keys]
	wr.writerow(row)
