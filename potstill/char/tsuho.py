# Copyright (c) 2016 Fabian Schuiki
#
# This file implements input file generation and simulation execution for the
# setup and hold time analysis of a full memory macro.

import sys, os, numbers, collections, subprocess, csv
import potstill
from potstill.char import util
from potstill.char.util import ScsWriter, OcnWriter


def d2str(v):
	return "%.8g" % v


def lerp(v, a, b, x, y):
	f = float(v - a) / (b - a)
	return x*(1-f) + y*f


def crossings(points, th):
	for ((ta,va), (tb,vb)) in zip(points[0:-1], points[1:]):
		if va < th and vb >= th:
			yield(lerp(th, va, vb, ta, tb), 1)
		elif vb < th and va >= th:
			yield(lerp(th, vb, va, tb, ta), -1)


class Probe(object):
	def __init__(self, terminal, probe, inverted=False, relative_to_clock=True, name=None, outer=False):
		super(Probe, self).__init__()
		self.name = name or terminal
		self.terminal = terminal
		self.probe = probe
		self.inverted = inverted
		self.relative_to_clock = relative_to_clock
		self.outer = outer


class Pulse(object):
	def __init__(self, start, end, start_clock=None, end_clock=None, inverted=False, repeat=False):
		super(Pulse, self).__init__()
		assert(start < end)
		assert(start_clock is None or end_clock is None or start_clock < end_clock)
		self.start = start
		self.end = end
		self.start_clock = start_clock
		self.end_clock = end_clock
		self.inverted = inverted
		self.repeat = repeat

	def val0(self):
		return "0"

	def val1(self):
		return "-vdd" if self.inverted else "vdd"


class Input(util.Input):
	probes = [
		Probe("RE", "X.XRWCKG.X0.n1", inverted=True, outer=True, relative_to_clock=False),
		Probe("RA", "X.nRA0"),
		Probe("WE", "X.XRWCKG.X1.n1", inverted=True, outer=True, relative_to_clock=False),
		Probe("WA", "X.XAD.XCKG0.n1", relative_to_clock=False),
		Probe("WD", "X.nWD0"),
	]

	def __init__(self, macro, tslewck, tslewpin, num_steps=3, intervals=None, inclusive_intervals=True):
		super(Input, self).__init__(macro)
		self.tslewck = tslewck
		self.tslewpin = tslewpin
		self.num_steps = num_steps
		self.Tcycle = 14*self.T
		self.intervals = intervals or dict([
			(p.name, ((-self.T/2, self.T/2), (-self.T/2, self.T/2))) for p in self.probes
		])

		# Adjust the intervals in case they should be exclusive.
		if not inclusive_intervals:
			self.intervals = dict([
				(name, (
					self.make_interval_exclusive(rise),
					self.make_interval_exclusive(fall),
				))
				for (name, (rise,fall)) in self.intervals.items()
			])

		# Assemble a lists of rising and falling setup times checks to perform.
		# Each of these will be translated into a separate pulse during the
		# simulation.
		self.stops = dict([
			(name, (
				list(self.calc_stops(rise)),
				list(self.calc_stops(fall))
			))
			for (name,(rise,fall)) in self.intervals.items()
		])

		# Make a list of pulses for each of the probes.
		self.pulses = dict([
			(probe.name, list(self.calc_pulses(probe)))
			for probe in self.probes
		])

		# Make a list of reference edges that serve to calculate the propagation
		# delay for each signal. For clock-sensitive signals, these are the
		# rising clock edges. For other signals, these are the times the input
		# signals change.
		self.edges = dict([
			(probe.name, self.calc_edges(probe))
			for probe in self.probes
		])


	def make_interval_exclusive(self, intv):
		(a,b) = intv
		f = float(b-a) / (self.num_steps+1)
		return (a+f, b-f)


	def calc_stops(self, intv):
		f = float(intv[1]-intv[0]) / (self.num_steps-1)
		for i in range(self.num_steps):
			yield intv[0] + i*f


	def make_spectre(self):
		wr = ScsWriter()
		wr.comment("Setup and hold time analysis for "+self.macro.name)
		self.write_spectre_prolog(wr)
		wr.stmt("parameters", ("tslewck", self.tslewck), ("tslewpin", self.tslewpin))
		wr.skip()

		wr.comment("Circuit Under Test")
		self.write_spectre_cut(wr, RE="RE", RA="RA", WE="WE", WA="WA", WD="WD")
		wr.vdc("VDD", "VDD")
		wr.skip()

		# Generate two overlaid clock signals. The first clock impulse has a
		# high rise time tsc. This is the critical edge for which setup time is
		# measured. The second clock edge serves as a "safe" edge during which
		# the content of the sequential cells is set to a known state in case of
		# a setup violation.
		wr.comment("Clock Generation")
		wr.vpulse("VCK0", "nCK1", 0, 0, "vdd", delay=d2str(3*self.T)+"-tslewck/2", width=d2str(self.T)+"-tslewck", period=4*self.T, rise="tslewck", fall="tslewck")
		wr.vpulse("VCK1", "CK", "nCK1", 0, "vdd", delay=d2str(1*self.T)+"-tslewck/2", width=d2str(1*self.T)+"-tslewck", period=4*self.T, rise="tslewck", fall="tslewck")
		wr.skip()

		# Generate the input signals for each of the probing pins.
		wr.comment("Stimuli Generation")
		for probe in self.probes:

			# Assemble a generator that produces the high and low vpulse
			# terminals in conjunction with an index for each step.
			name = "V"+probe.name
			pulses = self.pulses[probe.name]
			terms = ["0"] + ["n%s%d" % (name,i) for i in range(len(pulses)-1)] + [probe.terminal]
			zp = zip(terms[1:], terms[0:-1], pulses, range(len(pulses)))

			# Generate one voltage source for each individual pulse.
			for (hi,lo,p,step) in zp:
				wr.vpulse(name+str(step), hi, lo, p.val0(), p.val1(),
					delay=d2str(p.start) + "-tslewpin/2",
					width=d2str(p.end-p.start) + "-tslewpin",
					rise="tslewpin",
					fall="tslewpin",
					period=(self.Tcycle if p.repeat else None)
				)

		wr.skip()

		wr.comment("Analysis")
		wr.tran(self.num_steps*self.Tcycle + 1*self.T, errpreset="liberal")
		wr.stmt("save CK X.XAD.nWE0 " + " ".join(
			[p.terminal for p in self.probes] +
			[p.probe for p in self.probes]
		))

		return wr.collect()


	# Analyzes the results of the SPECTRE run.
	def analyze(self, psfascii_file):

		# Load the waves from the ASCII file.
		waves = dict(
			[(p.name, list()) for p in self.probes] +
			[(p.probe, list()) for p in self.probes]
		)
		with open(psfascii_file) as f:
			# Skip everything up until the VALUE section.
			for raw_line in f:
				if raw_line.strip() == "VALUE":
					break

			# Parse the values.
			time = None
			for raw_line in f:
				line = raw_line.strip()
				if line == "END":
					break
				fields = line.split()
				name = fields[0].strip('\"')
				value = float(fields[1])
				if name == "time":
					time = value
				else:
					if name in waves:
						assert(time is not None)
						waves[name].append((time, value))

		# Find the crossing points for each of the observed probes.
		Vth = self.macro.vdd/2
		results = list()
		for probe in self.probes:
			(rise_edges, fall_edges) = self.edges[probe.name]
			rise_Tpd = dict()
			fall_Tpd = dict()
			for (t, probe_edge) in crossings(waves[probe.probe], Vth):

				# Calculate the cycle this crossing belongs to.
				cycle = int(t / self.Tcycle)
				assert(cycle >= 0 and cycle < self.num_steps)

				# Find the reference edge of the probe's input terminal for this
				# crossing.
				edge = -probe_edge if probe.inverted else probe_edge
				edges = rise_edges if edge == 1 else fall_edges

				# Calculate the propagation delay. Ignore negative propagation
				# delays as well as rising edges that lie after the cycle's
				# falling stimulus. Both of which are a result of glitching or
				# partial transition.
				Tpd = t - edges[cycle]
				if Tpd < 0:
					continue
				if edge == 1 and t >= fall_edges[cycle]:
					continue

				# Store the propagation delay for this stop. Lists for the
				# rising and falling Tpds are separate. Note that due to
				# glitching there might be multiple edges
				dst = rise_Tpd if edge == 1 else fall_Tpd
				if not cycle in dst or dst[cycle] < Tpd:
					dst[cycle] = Tpd

			# Convert the (cycle => tpd) mapping in rise_Tpd and fall_Tpd to a
			# list of (tsu, tpd) tuples.
			stops = self.stops[probe.name]
			results.append((
				probe.name,
				[(stops[0][c], rise_Tpd[c]) for c in sorted(rise_Tpd.keys())],
				[(stops[1][c], fall_Tpd[c]) for c in sorted(fall_Tpd.keys())],
			))

		return results


# Input file generator for the setup time analysis.
class SetupInput(Input):
	def __init__(self, *args, **kwargs):
		super(SetupInput, self).__init__(*args, **kwargs)


	# Generate a sequence of pulses that need to be applied to the input of the
	# specified probe.
	def calc_pulses(self, probe):
		Tstart = (1 if probe.outer else 3)*self.T
		Twidth = (10 if probe.outer else 4)*self.T
		stops = self.stops[probe.name]
		for step in range(self.num_steps):
			rise = stops[0][step]
			fall = stops[1][step]
			ck = step*self.Tcycle + Tstart
			s = ck + rise
			w = Twidth - rise + fall
			yield Pulse(s, s+w, ck, ck+Twidth)


	# Generate a touple of two lists that contain the reference edges for
	# propagation delay calculation, one for each cycle.
	def calc_edges(self, probe):
		pulses = self.pulses[probe.name]
		if probe.relative_to_clock:
			return (
				[p.start_clock for p in pulses],
				[p.end_clock   for p in pulses]
			)
		else:
			return (
				[p.start for p in pulses],
				[p.end   for p in pulses]
			)


# Input file generator for the hold time analysis.
class HoldInput(Input):
	def __init__(self, *args, **kwargs):

		# Load the setup times from disk.
		with open("setup.csv") as f:
			rd = csv.reader(f)
			self.setup_times = dict([
				(name, float(value)) for (name,value) in rd
			])

		# Call the parent __init__ function. This needs to happen after the
		# setup times have been loaded, since the calc_pulses functions called
		# by __init__ needs them.
		super(HoldInput, self).__init__(*args, **kwargs)


	# Generate a sequence of pulses that need to be applied to the input of the
	# specified probe.
	def calc_pulses(self, probe):
		Tstart = (1 if probe.outer else 3)*self.T
		Twidth = (10 if probe.outer else 4)*self.T

		# Generate the safe pulse which causes the storage elements to
		# transition to the intended value the cycle after the hold time test.
		yield Pulse(Tstart+self.T, Tstart+Twidth+self.T, Tstart, Tstart+Twidth, repeat=True)

		# Generate the application pulses that last from the setup time to the
		# hold time being tested. Generate separate pulses for the rising and
		# falling edges of the probe signal.
		stops = self.stops[probe.name]
		for step in range(self.num_steps):
			rise = stops[0][step]
			fall = stops[1][step]
			ck_rise = step*self.Tcycle + Tstart
			ck_fall = ck_rise + Twidth

			# Rising edge.
			s = ck_rise + self.setup_times["Tsu_%s_rise" % probe.name]
			e = ck_rise - rise
			if s < e - self.tslewpin:
				yield Pulse(s, e)

			# Falling edge.
			s = ck_fall + self.setup_times["Tsu_%s_fall" % probe.name]
			e = ck_fall - fall
			if s < e - self.tslewpin:
				yield Pulse(s, e, inverted=True)


	# Generate a touple of two lists that contain the reference edges for
	# propagation delay calculation, one for each cycle.
	def calc_edges(self, probe):
		Tstart = (1 if probe.outer else 3)*self.T
		Twidth = (10 if probe.outer else 4)*self.T

		if probe.relative_to_clock:
			return (
				[Tstart + i*self.Tcycle for i in range(self.num_steps)],
				[Tstart + Twidth + i*self.Tcycle for i in range(self.num_steps)]
			)
		else:
			return (
				[Tstart + self.setup_times["Tsu_%s_rise" % probe.name] + i*self.Tcycle for i in range(self.num_steps)],
				[Tstart + Twidth + self.setup_times["Tsu_%s_fall" % probe.name] + i*self.Tcycle for i in range(self.num_steps)],
			)


class Run(util.Run):
	def __init__(self, output, figure, macro, tslewck, tslewpin, threshold=1.05, max_iterations=10, target_precision=1e-12):
		super(Run, self).__init__(macro)
		self.tslewck = tslewck
		self.tslewpin = tslewpin
		self.threshold = threshold
		self.intervals = None
		self.baseline = None
		self.precision = None
		self.iteration = 0
		self.max_iterations = max_iterations
		self.target_precision = target_precision
		self.output = output
		self.figure = figure

	def prepare(self):
		self.make_netlist("netlist.cir")
		self.make_nodeset("nodeset.ns")

	def run_iteration(self):
		# Run the SPECTRE simulation and analysis. During the first iteration
		# when self.intervals = None, the interval [-T/2,T/2] is inspected for
		# all inputs.
		filename = "input.scs"
		inp = self.make_input(self.macro, self.tslewck, self.tslewpin, intervals=self.intervals, inclusive_intervals=(self.intervals is None))
		with open(filename, "w") as f:
			f.write(inp.make_spectre())
		self.exec_spectre(filename, output=self.output, format="psfascii", quiet=True)
		results = inp.analyze(self.output+"/tran.tran.tran")

		# If no baseline for Tpd has been established yet, i.e. this is the
		# first iteration, use the propagation delay for Tsu/Tho = -T/2 as the
		# baseline.
		if self.baseline is None:
			self.baseline = dict([
				(name, (rise[0][1], fall[0][1]))
				for (name, rise, fall) in results
			])
			print("Baseline Tpd:")
			for (name, (rise,fall)) in self.baseline.items():
				print("  Tpd_%s_rise: %.4gps" % (name, rise*1e12))
				print("  Tpd_%s_fall: %.4gps" % (name, fall*1e12))

		# Initialize the intervals if this is the first iteration.
		if self.intervals is None:
			self.intervals = dict([
				(name, ([None, None], [None, None]))
				for (name,_,_) in results
			])

		for (name, rise, fall) in results:
			# print("Analyzing results of %s" % name)
			(rise_baseline, fall_baseline) = self.baseline[name]
			(rise_intv, fall_intv) = self.intervals[name]
			for (points, intv, baseline) in [(rise, rise_intv, rise_baseline), (fall, fall_intv, fall_baseline)]:
				for (Tsu,Tpd) in points:
					if Tpd < baseline * self.threshold:
						if intv[0] is None or intv[0] < Tsu:
							intv[0] = Tsu
					else:
						if intv[1] is None or intv[1] > Tsu:
							intv[1] = Tsu
							break


		# Write this iteration's results to disk.
		with open(self.output+".csv", "w") as f:
			wr = csv.writer(f)
			for probe in inp.probes:
				(rise,fall) = self.intervals[probe.name]
				wr.writerow(["%s_%s_rise" % (self.figure, probe.name), rise[0]])
				wr.writerow(["%s_%s_fall" % (self.figure, probe.name), fall[0]])


		# Write the current value range for the rise and fall times for each
		# input to stdout, for informative purposes only.
		print("Iteration %d:" % self.iteration)
		for (name, (rise,fall)) in self.intervals.items():
			print("  %s: %s rise = %.4gps ±%.4gps, fall = %.4gps ±%.4gps" % (
				name, self.figure,
				(rise[0]+rise[1])*0.5*1e12, (rise[1]-rise[0])*0.5*1e12,
				(fall[0]+fall[1])*0.5*1e12, (fall[1]-fall[0])*0.5*1e12
			))

		# Calculate the overall precision achieved and keep track of the
		# iteration counter.
		self.precision = max([
			max(tb-ta, td-tc) for ((ta,tb),(tc,td)) in self.intervals.values()
		])
		print("  precision = %.4gps" % (self.precision*1e12))
		self.iteration += 1
		return self.precision


	# Perform multiple iterations of the analysis until a certain precision has
	# been reached or the maximum number of iterations have elapsed.
	def run(self):
		self.prepare()

		while (self.precision is None or self.precision > self.target_precision) and self.iteration < self.max_iterations:
			self.run_iteration()

		print("Finished after %d iterations, precision = %.4gps" % (self.iteration, self.precision*1e12))


class SetupRun(Run):
	def __init__(self, *args, **kwargs):
		super(SetupRun, self).__init__("setup", "Tsu", *args, **kwargs)

	def make_input(self, *args, **kwargs):
		return SetupInput(*args, **kwargs)


class HoldRun(Run):
	def __init__(self, *args, **kwargs):
		super(HoldRun, self).__init__("hold", "Tho", *args, **kwargs)

	def make_input(self, *args, **kwargs):
		return HoldInput(*args, **kwargs)


class SetupHoldRun(object):
	def __init__(self, *args, **kwargs):
		super(SetupHoldRun, self).__init__()
		self.setup = SetupRun(*args, **kwargs)
		self.hold = HoldRun(*args, **kwargs)

	def run(self):
		self.setup.run()
		self.hold.run()
