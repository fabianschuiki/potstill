# Copyright (c) 2016 Fabian Schuiki
#
# This file implements timing calculation for memory macros.

import sys, os, yaml, csv
from bisect import bisect
from collections import OrderedDict


class Pin(object):
	def __init__(self, name):
		super(Pin, self).__init__()
		self.name = name
		self.dir = "output" if name == "RD" else "input"
		self.capacitance = None

	def internal_powers(self):
		return ["asdf"]


# A class that loads a table of values from a CSV file, groups them according to
# operating conditions and pivot columns, and linearly interpolates the data
# based on a num_bits column.
class Table(object):
	def __init__(self, path, pivot_columns, num_bits):
		super(Table, self).__init__()
		with open(path) as f:
			rd = csv.reader(f)
			columns = next(rd)
			# print(columns)

			# Find the indices of the num_bits and pivot columns.
			idx_num_bits = columns.index("num_bits")
			idx_opcond = [columns.index(x) for x in ["vdd", "temp"]]
			idx_pivot_columns = [columns.index(x) for x in pivot_columns]
			prune_idx = set([idx_num_bits] + idx_opcond + idx_pivot_columns)
			keep_columns = [(i,k) for (i,k) in enumerate(columns) if i not in prune_idx]

			# Group the rows by opcond, pivot columns, and num_bits.
			grouped = dict()
			for row in rd:
				nb_key = int(row[idx_num_bits])
				opcond_key = ",".join([columns[k]+"="+row[k] for k in idx_opcond])
				pivot_key = ",".join([columns[k]+"="+row[k] for k in idx_pivot_columns])

				if opcond_key in grouped:
					a = grouped[opcond_key]
				else:
					a = dict()
					grouped[opcond_key] = a

				if pivot_key in a:
					b = a[pivot_key]
				else:
					b = OrderedDict([(k, dict()) for (_,k) in keep_columns])
					a[pivot_key] = b

				for (i,k) in keep_columns:
					if row[i]:
						c = b[k]
						assert(nb_key not in c)
						c[nb_key] = row[i]

			# Interpolate the results based on num_bits.
			self.values = dict()
			for (opcond, runs) in grouped.items():
				for (run, params) in runs.items():
					for (param, datapoints) in params.items():

						if opcond in self.values:
							dst_a = self.values[opcond]
						else:
							dst_a = dict()
							self.values[opcond] = dst_a

						if param in dst_a:
							dst_b = dst_a[param]
						else:
							dst_b = dict()
							dst_a[param] = dst_b

						assert(run not in dst_b)

						stops = list(sorted(datapoints.keys()))

						# Find the leftmost value among the stops that is greater
						# than num_bits. This then corresponds to the upper value of
						# the linear interpolation.
						upper = bisect(stops, num_bits)
						if upper == 0:
							upper += 1
						elif upper == len(stops):
							upper -= 1
						lower = upper-1

						if len(stops) > 1:
							# Find the interpolation factor.
							lower_val = stops[lower]
							upper_val = stops[upper]
							f = float(num_bits - lower_val) / (upper_val - lower_val)

							# Interpolate the value.
							v = float(datapoints[lower_val])*(1-f) + float(datapoints[upper_val])*f
						else:
							v = datapoints[stops[0]]

						dst_b[run] = v


class Figures(object):
	def __init__(self, opcond, values):
		super(Figures, self).__init__()
		self.opcond = opcond
		self.values = values

	def one(self, name):
		return next(iter(self.values[name].values()))

	def all(self, name):
		return self.values[name] if name in self.values else None


class Timing(object):
	def __init__(self, macond):
		super(Timing, self).__init__()
		self.macond = macond
		with open(macond.techdir+"/config.yml") as f:
			self.config = yaml.load(f)

		self.name = self.macond.name + ("_%dV%dC" % (int(self.macond.vdd*100), int(self.macond.temp)))

		# Load the timing tables.
		basedir = "%s/tables/%d" % (macond.techdir, macond.num_words)
		tables = [
			Table(basedir+"/pwrck.csv", ["tslew"], macond.num_bits),
			Table(basedir+"/pwrintcap.csv", ["tslew"], macond.num_bits),
			Table(basedir+"/pwrout.csv", ["tslew", "cload"], macond.num_bits),
			Table(basedir+"/trdwr.csv", ["tslew", "cload"], macond.num_bits),
			Table(basedir+"/tsuho.csv", ["tslewck", "tslewpin"], macond.num_bits),
		]

		# Merge the timing figures.
		self.figures = dict()
		for tbl in tables:
			for (opcond, figures) in tbl.values.items():
				if opcond in self.figures:
					self.figures[opcond].values.update(figures)
				else:
					self.figures[opcond] = Figures(opcond, figures.copy())
