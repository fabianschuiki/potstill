#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# This script reads a CSV file containing two columns and merges rows
# that only differ in their "_rise" or "_fall" suffix by adding the
# values in the second column.

import sys,csv
from collections import OrderedDict

if len(sys.argv) < 2:
	sys.stderr.write("usage: csv-merge-edges FILE [FILE ...]\n")
	sys.exit(1)

for filename in sys.argv[1:]:
	with open(filename) as f:
		rd = csv.reader(f)
		data = OrderedDict([(x[0], float(x[1])) for x in rd])

	wr = csv.writer(sys.stdout)
	handled = set()
	for (k,v) in data.items():
		if k in handled:
			continue

		if k.endswith("_rise"):
			n = k[:-5]
			ko = n+"_fall"
			w = v + data[ko]
			handled.add(ko)
		elif k.endswith("_fall"):
			n = k[:-5]
			ko = n+"_rise"
			w = v + data[ko]
			handled.add(ko)
		else:
			n = k
			w = v

		wr.writerow([n,w])
