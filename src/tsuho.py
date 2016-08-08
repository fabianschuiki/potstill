# Copyright (c) 2016 Fabian Schuiki
import csv, os
import src.char
import itertools
from collections import OrderedDict


def scsStmt(scs, *args, **kwargs):
	scs.append(" ".join(list(args) + ["%s=%s" % (k,v) for k,v in kwargs.items()])+"\n")


class Tsu(src.char.RunInput):
	def __init__(self, macro, tslewck, tslewpin, *args, oceanOutputName="setup.csv", spectreOutputName="setup.psf", **kwargs):
		super(Tsu, self).__init__(macro, *args, oceanOutputName=oceanOutputName, spectreOutputName=spectreOutputName, **kwargs)
		self.tslewck = tslewck
		self.tslewpin = tslewpin

		self.Tfrom = -150e-12
		self.Tto = 300e-12
		self.Ncycles = 50
		self.triggerRatio = 1.05

	def generateInputs(self):
		num_addr = self.macro.num_addr
		num_bits = self.macro.num_bits
		T = 5e-9

		# Calculate the initial edge position and the drift per cycle.
		Tinit = self.Tfrom
		Tdr = (self.Tto-self.Tfrom)/(self.Ncycles-1)

		scs = list()
		ocn = list()

		scs.append("// %s" % self.macro.name)
		scs.append("include \"%s/sim/preamble.scs\"" % src.char.BASE)
		scs.append("include \"%s\"" % self.netlistName)
		scs.append("o1 options temp=%g tnom=%g" % (self.macro.temp, self.macro.temp))

		ocn.append("openResults(\"%s\")" % self.spectreOutputName)
		ocn.append("selectResult('tran)")
		ocn.append("VDD = %g" % self.macro.vdd)
		ocn.append("p = outfile(\"%s\", \"w\")" % self.oceanOutputName)

		scs.append("X (CK B %s %s B %s %s VDD 0) %s" % (
			" ".join(["A" for i in range(num_addr)]),
			" ".join(["RD%d" % i for i in range(num_bits)]),
			" ".join(["A" for i in range(num_addr)]),
			" ".join(["A" for i in range(num_bits)]),
			self.macro.name
		))

		scs.append("parameters vdd=%g tsc=%g tsd=%g tinit=%g tdr=%g" % (self.macro.vdd, self.tslewck, self.tslewpin, Tinit, Tdr))
		scs.append("VDD (VDD 0) vsource type=dc dc=vdd")

		Tstart = 1
		Tcycle = 16

		# Generate two overlaid clock signals. The first clock impulse has a high rise
		# time tsc. This is the critical edge for which setup time is measured. The
		# second clock edge serves as a "safe" edge during which the content of the
		# sequential cells is set to a known state in case of a setup violation.
		scs.append("VCK0 (nCK1 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g period=%g" % ((Tstart+2)*T, 1*T, 4*T))
		scs.append("VCK1 (CK nCK1) vsource type=pulse val0=0 val1=vdd delay=%g-0.5*tsc width=%g-0.5*tsc period=%g rise=tsc fall=10p" % (Tstart*T, 1*T, 4*T))

		# Generate the input signal for the RA and WD pins.
		scs.append("VA0 (A 0) vsource type=pulse val0=0 val1=vdd delay=%g-0.5*tsd+tinit width=%g-tsd period=%g+tdr rise=tsd fall=tsd" % ((Tstart+4)*T, 4*T, 16*T))

		# Generate the input signal for the RE and WE pins, which need to be high during
		# the testing of the other pins.
		scs.append("VB0 (B 0) vsource type=pulse val0=0 val1=vdd delay=%g-0.5*tsd+tinit width=%g-tsd period=%g+tdr rise=tsd fall=tsd" % (Tstart*T, 12*T, 16*T))

		# Specify the simulation to perform.
		scs.append("tran tran stop=%g readns=\"%s\"" % ((Tstart+self.Ncycles*16)*T, self.nodesetName))

		# The following are the probing points to determine the propagation delay for
		# the various inputs.
		prb_RE = "X.XRWCKG.X0.n1"
		prb_RA = "X.nRA0"
		prb_WE = "X.XRWCKG.X1.n1"
		prb_WA = "X.XAD.XCKG0.n1"
		prb_WD = "X.nWD0"

		# Specify what to save.
		scs.append("save CK A B")
		scs.append("save %s %s %s %s %s" % (prb_RE, prb_RA, prb_WE, prb_WA, prb_WD))
		# scs.append("save RD* depth=1")
		# scs.append("save X:currents")

		# In the OCEAN script, calculate the rising and falling edges of the measured
		# points such that the propagation delays can be calculated later.
		for s in [("RE", prb_RE, True), ("WE", prb_WE, True), ("RA", prb_RA, False), ("WA", prb_WA, False), ("WD", prb_WD, False), ("A", "A", False), ("B", "B", False)]:
			ocn.append("X_%s_rise = cross(VT(\"%s\") VDD/2 1 \"%s\" t \"cycle\")" % (s[0], s[1], "falling" if s[2] else "rising"))
			ocn.append("X_%s_fall = cross(VT(\"%s\") VDD/2 1 \"%s\" t \"cycle\")" % (s[0], s[1], "rising" if s[2] else "falling"))

		# For the level-triggered sequential elements, calculate the propagation delay
		# as the time between the related signal's crossing and the probe's crossing.
		for s in [("WA", "A"), ("RE", "B"), ("WE", "B")]:
			ocn.append("Tpd_%s_rise = (X_%s_rise - X_%s_rise)" % (s[0], s[0], s[1]))
			ocn.append("Tpd_%s_fall = (X_%s_fall - X_%s_fall)" % (s[0], s[0], s[1]))

		# For the edge triggered sequential elements.
		for s in [("RA", 4*T, 8*T), ("WD", 4*T, 8*T)]:
			ocn.append("Tpd_%s_rise = (X_%s_rise - int(X_%s_rise / %g) * %g - %g)" % (s[0], s[0], s[0], Tcycle*T, Tcycle*T, s[1]+Tstart*T))
			ocn.append("Tpd_%s_fall = (X_%s_fall - int(X_%s_fall / %g) * %g - %g)" % (s[0], s[0], s[0], Tcycle*T, Tcycle*T, s[2]+Tstart*T))

		# Calculate the threshold values for the propagation delay which if crossed mark
		# a setup violation.
		for s in ["RE", "RA", "WE", "WA", "WD"]:
			for e in ["rise", "fall"]:
				ocn.append("Tpdth_%s_%s = value(Tpd_%s_%s 1) * %f" % (s, e, s, e, self.triggerRatio))

		# Calculate the number of cycles after which the propagation delays cross the
		# corresponding threshold value.
		for s in ["RE", "RA", "WE", "WA", "WD"]:
			for e in ["rise", "fall"]:
				# Be careful to subtract 1, since the cycle count starts at 1. However,
				# the first cycle represents tsu=tinit, not tsu=tinit+tdr.
				ocn.append("Nc_%s_%s = int(cross(Tpd_%s_%s Tpdth_%s_%s 1 \"rising\")) - 1" % (s, e, s, e, s, e))
				ocn.append("fprintf(p, \"Tsu_%s_%s,%%g\\n\", %g - Nc_%s_%s * %g)" % (s, e, -Tinit, s, e, Tdr))

		ocn.append("close(p)")

		# Generate the output.
		return ("\n".join(scs), "\n".join(ocn))


class Tho(src.char.RunInput):
	def __init__(self, macro, setupCsvName, tslewck, tslewpin, *args, oceanOutputName="hold.csv", spectreOutputName="hold.psf", **kwargs):
		super(Tho, self).__init__(macro, *args, oceanOutputName=oceanOutputName, spectreOutputName=spectreOutputName, **kwargs)
		self.tslewck = tslewck
		self.tslewpin = tslewpin
		self.setupCsvName = setupCsvName

		self.Tfrom = 400e-12
		self.Tto = -100e-12
		self.Ncycles = 50
		self.triggerRatio = 1.05

	def generateInputs(self):
		num_addr = self.macro.num_addr
		num_bits = self.macro.num_bits
		T = 1e-9

		# Read the CSV file containing the setup times.
		with open(self.setupCsvName, "r") as f:
			rd = csv.reader(f)
			setupTimes = dict([(a[0], float(a[1])) for a in rd])

		Tinit = self.Tfrom
		Tdr = (self.Tto-self.Tfrom)/(self.Ncycles-1)

		scs = list()
		ocn = list()

		scs.append("// %s" % self.macro.name)
		scs.append("include \"%s/sim/preamble.scs\"" % src.char.BASE)
		scs.append("include \"%s\"" % self.netlistName)
		scs.append("o1 options temp=%g tnom=%g" % (self.macro.temp, self.macro.temp))

		ocn.append("openResults(\"%s\")" % self.spectreOutputName)
		ocn.append("selectResult('tran)")
		ocn.append("VDD = %g" % self.macro.vdd)
		ocn.append("p = outfile(\"%s\", \"w\")" % self.oceanOutputName)

		scs.append("X (CK RE %s %s WE %s %s VDD 0) %s" % (
			" ".join(["RA" for i in range(num_addr)]),
			" ".join(["RD%d" % i for i in range(num_bits)]),
			" ".join(["WA" for i in range(num_addr)]),
			" ".join(["WD" for i in range(num_bits)]),
			self.macro.name
		))

		scs.append("parameters vdd=%g tsc=%g tsd=%g tinit=%g tdr=%g" % (self.macro.vdd, self.tslewck, self.tslewpin, Tinit, Tdr))
		scs.append("VDD (VDD 0) vsource type=dc dc=vdd")

		Tstart = 1
		Tcycle = 16

		# Generate two overlaid clock signals. The first clock impulse has a high rise
		# time tsc. This is the critical edge for which setup time is measured. The
		# second clock edge serves as a "safe" edge during which the content of the
		# sequential cells is set to a known state in case of a setup violation.
		scs.append("VCK0 (nCK1 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g period=%g" % ((Tstart+2)*T, 1*T, 4*T))
		scs.append("VCK1 (CK nCK1) vsource type=pulse val0=0 val1=vdd delay=%g-0.5*tsc width=%g-0.5*tsc period=%g rise=tsc fall=10p" % (Tstart*T, 1*T, 4*T))

		# Generate the input signal for the RA, WA, and WD pins.
		for p in [("RE", True), ("WE", True), ("RA", False), ("WA", False), ("WD", False)]:
			tps = (Tstart if p[1] else Tstart+4) # Start time of the pulse.
			tpw = (12 if p[1] else 4) # Pulse width.

			tsurise = setupTimes["Tsu_%s_rise" % p[0]]
			tsufall = setupTimes["Tsu_%s_fall" % p[0]]

			# Generate the rising edge with the appropriate rising setup time.
			scs.append("V%s0 (n%s1 0) vsource type=pulse val0=0 val1=vdd delay=%g-0.5*tsd-(%g) width=%g-tsd+(%g) period=%g rise=tsd fall=tsd" % (
				p[0], p[0],
				tps*T,
				tsurise,
				tpw*T*0.5,
				tsurise,
				Tcycle*T
			))

			# Generate the falling edge with the appropriate falling setup time.
			scs.append("V%s1 (n%s2 n%s1) vsource type=pulse val0=0 val1=vdd delay=%g-0.5*tsd width=%g-tsd-(%g) period=%g rise=tsd fall=tsd" % (
				p[0], p[0], p[0],
				tps*T+tpw*T*0.5,
				tpw*T*0.5,
				tsufall,
				Tcycle*T
			))

			# Generate the falling edge that shifts and triggers a hold violation after
			# the signal has risen.
			scsStmt(scs,
				"V%s2 (n%s3 n%s2) vsource type=pulse" % (p[0], p[0], p[0]),
				"rise=tsd fall=10p",
				"val0=0 val1=-vdd",
				"delay=%g+tinit-0.5*tsd" % (tps*T),
				"width=%g-tinit-0.5*tsd-5p" % T,
				"period=%g+tdr" % (Tcycle*T)
			)

			# Generate the rising edge that shifts and triggers a hold violation after
			# the signal has fallen.
			scsStmt(scs,
				"V%s3 (%s n%s3) vsource type=pulse" % (p[0], p[0], p[0]),
				"rise=tsd fall=10p",
				"val0=0 val1=vdd",
				"delay=%g+tinit-0.5*tsd" % ((tps+tpw)*T),
				"width=%g-tinit-0.5*tsd-5p" % T,
				"period=%g+tdr" % (Tcycle*T)
			)

		# Specify the simulation to perform.
		scs.append("tran tran stop=%g readns=\"%s\"" % ((Tstart+self.Ncycles*Tcycle)*T, self.nodesetName))

		# The following are the probing points to determine the propagation delay for
		# the various inputs.
		prb_RE = "X.XRWCKG.X0.n1"
		prb_RA = "X.nRA0"
		prb_WE = "X.XRWCKG.X1.n1"
		prb_WA = "X.XAD.XCKG0.n1"
		prb_WD = "X.nWD0"

		# Specify what to save.
		scs.append("save CK RE WE WA RA WD")
		scs.append("save %s %s %s %s %s" % (prb_RE, prb_RA, prb_WE, prb_WA, prb_WD))

		# In the OCEAN script, calculate the rising and falling edges of the measured
		# points such that the propagation delays can be calculated later.
		for s in [("RE", prb_RE, True), ("WE", prb_WE, True), ("RA", prb_RA, False), ("WA", prb_WA, False), ("WD", prb_WD, False)]:
			ocn.append("X_%s_rise = cross(VT(\"%s\") VDD/2 1 \"%s\" t \"time\")" % (s[0], s[1], "falling" if s[2] else "rising"))
			ocn.append("X_%s_fall = cross(VT(\"%s\") VDD/2 1 \"%s\" t \"time\")" % (s[0], s[1], "rising" if s[2] else "falling"))

		# For the edge triggered sequential elements.
		for s in [
				("RA", 4*T, 8*T),
				("WD", 4*T, 8*T),
				("WA", 4*T - setupTimes["Tsu_WA_rise"],  8*T - setupTimes["Tsu_WA_fall"]),
				("RE", 0*T - setupTimes["Tsu_RE_rise"], 12*T - setupTimes["Tsu_RE_fall"]),
				("WE", 0*T - setupTimes["Tsu_WE_rise"], 12*T - setupTimes["Tsu_WE_fall"])
			]:
			ocn.append("Tpd_%s_rise = (X_%s_rise - int(X_%s_rise / %g) * %g - %g)" % (s[0], s[0], s[0], Tcycle*T, Tcycle*T, s[1]+Tstart*T))
			ocn.append("Tpd_%s_fall = (X_%s_fall - int(X_%s_fall / %g) * %g - %g)" % (s[0], s[0], s[0], Tcycle*T, Tcycle*T, s[2]+Tstart*T))

		# Calculate the threshold values for the propagation delay which if crossed mark
		# a setup violation.
		for s in ["RE", "RA", "WE", "WA", "WD"]:
			for e in ["rise", "fall"]:
				ocn.append("Tpdth_%s_%s = value(Tpd_%s_%s %g) * %f" % (s, e, s, e, (Tstart+Tcycle)*T, self.triggerRatio))

		# Calculate the number of cycles after which the propagation delays cross the
		# corresponding threshold value.
		for s in ["RE", "RA", "WE", "WA", "WD"]:
			for e in ["rise", "fall"]:
				ocn.append("Nc_%s_%s = int(cross(Tpd_%s_%s Tpdth_%s_%s 1 \"rising\") / %g)" % (s, e, s, e, s, e, Tcycle*T))
				ocn.append("fprintf(p, \"Tho_%s_%s,%%g\\n\", %g + Nc_%s_%s * (%g))" % (s, e, Tinit, s, e, Tdr))

		ocn.append("close(p)")

		# Generate the output.
		return ("\n".join(scs), "\n".join(ocn))


class TsuhoRun(src.char.SimulationRun):
	def __init__(self, input, *args, **kwargs):
		super(TsuhoRun, self).__init__(input, *args, **kwargs)

	def params(self):
		return [("tslewck", self.input.tslewck), ("tslewpin", self.input.tslewpin)]


class TsuhoCombinedRun(src.char.Run):
	def __init__(self, tsu_input, tho_input, resultsName="results.csv", *args, **kwargs):
		super(TsuhoCombinedRun, self).__init__(*args, **kwargs)
		self.resultsName = resultsName
		tho_input.setupCsvName = self.workpath(tho_input.setupCsvName)
		self.su_run = TsuhoRun(tsu_input, *args, spectreInputName="setup.scs", oceanInputName="setup.ocn", **kwargs)
		self.ho_run = TsuhoRun(tho_input, *args, spectreInputName="hold.scs", oceanInputName="hold.ocn", **kwargs)

	def params(self):
		return self.su_run.params()

	def run(self):
		self.su_run.run()
		self.ho_run.run()
		self.storeResults()

	def storeResults(self):
		su_results = self.su_run.loadResults()
		ho_results = self.ho_run.loadResults()
		with open(self.workpath(self.resultsName), "w") as f:
			wr = csv.writer(f)
			for r in su_results.items():
				wr.writerow(r)
			for r in ho_results.items():
				wr.writerow(r)

	def loadResults(self):
		with open(self.workpath(self.resultsName)) as f:
			rd = csv.reader(f)
			return OrderedDict(list(rd))


def makeCombinedRun(macro, x, *args, **kwargs):
	su = Tsu(macro, *x)
	ho = Tho(macro, su.oceanOutputName, *x)
	return TsuhoCombinedRun(su, ho, *args, **kwargs)


class TsuhoSweepRun(src.char.SweepRun):
	def __init__(self, macro, tslewck, tslewpin, *args, **kwargs):
		super(TsuhoSweepRun, self).__init__(*args, **kwargs)
		self.macro = macro
		self.tslewck = tslewck
		self.tslewpin = tslewpin
		self.runs = [makeCombinedRun(macro, x, workdir=self.workpath("tslewck=%g,tslewpin=%g" % x)) for x in itertools.product(tslewck, tslewpin)]

	def run(self):
		for run in self.runs:
			if not os.path.exists(run.workdir):
				os.makedirs(run.workdir)
			run.run()
		self.storeResults()
