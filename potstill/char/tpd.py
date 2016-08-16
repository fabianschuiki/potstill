# Copyright (c) 2016 Fabian Schuiki
#
# This file implements input file generation and simulation execution for the
# propagation and transition time analysis of a full memory macro.

import sys, os, subprocess
import potstill, potstill.nodeset, potstill.netlist
from potstill.char import util
from potstill.char.util import ScsWriter, OcnWriter


class Input(object):
	def __init__(self, macro, tslew, cload):
		super(Input, self).__init__()
		self.macro = macro
		self.tslew = tslew
		self.cload = cload
		self.T = 5e-9

	def write_spectre_prolog(self, wr):
		wr.include(os.path.dirname(__file__)+"/preamble.scs")
		wr.include("netlist.cir")
		wr.skip()

		wr.comment("Operating Conditions")
		wr.stmt("o1 options", ("temp", self.macro.temp), ("tnom", self.macro.temp))
		wr.stmt("parameters", ("vdd", self.macro.vdd), ("tslew", self.tslew), ("cload", self.cload))

	def write_spectre_cut(self, wr, CK="CK", RE="RE", RA=None, WE="WE", WA=None, WD=None, VDD="VDD", VSS="0"):
		ignore_counter = 0
		terms = list()
		for (t,n) in [
			(CK, 1),
			(RE, 1),
			(RA or ["RA%d" % i for i in range(self.macro.num_addr)], self.macro.num_addr),
			(["RD%d" % i for i in range(self.macro.num_bits)], self.macro.num_bits),
			(WE, 1),
			(WA or ["WA%d" % i for i in range(self.macro.num_addr)], self.macro.num_addr),
			(WD or ["WD%d" % i for i in range(self.macro.num_bits)], self.macro.num_bits)
		]:
			if isinstance(t, list):
				l = list(t)
				assert(len(l) == n)
				terms += l
			else:
				terms += [t]*n
		terms.append(VDD)
		terms.append(VSS)
		wr.instance("X", terms, self.macro.name)

	def make_spectre(self):
		wr = ScsWriter()
		wr.comment("Propagation and transition time analysis for "+self.macro.name)
		self.write_spectre_prolog(wr)
		wr.skip()

		wr.comment("Circuit Under Test")
		self.write_spectre_cut(wr, RA="RA", WA="VDD", WD="VDD")
		for i in range(self.macro.num_bits):
			wr.instance("C%d"%i, ["RD%d"%i,0], "capacitor c=cload")
		wr.vdc("VDD", "VDD")
		wr.skip()

		wr.comment("Stimuli Generation")
		wr.vpulse("VCK", "CK", 0, 0, "vdd", delay=str(1*self.T)+"-tslew/2", width=str(1*self.T)+"-tslew", period=2*self.T)
		wr.vpulse("VWE", "WE", 0, "vdd", 0, delay=str(2*self.T)+"-tslew/2")
		wr.vpulse("VRE", "RE", 0, 0, "vdd", delay=str(2*self.T)+"-tslew/2")
		wr.vpulse("VRA", "RA", 0, "vdd", 0, delay=str(4*self.T)+"-tslew/2")
		wr.skip()

		wr.comment("Analysis")
		wr.tran(3*2*self.T)
		wr.stmt("save CK RE RA RD0 WE")

		return wr.collect()

	def write_ocean_prolog(self, wr, psf_path="psf", output_path="results.csv"):
		wr.add("openResults(\"%s\")" % psf_path)
		wr.add("selectResult('tran)")
		wr.add("VDD = %g" % self.macro.vdd)
		wr.add("fd = outfile(\"%s\", \"w\")" % output_path)

	def write_ocean_epilog(self, wr):
		wr.add("close(fd)")

	def make_ocean(self):
		wr = OcnWriter()
		wr.comment("Propagation and transition time analysis for "+self.macro.name)
		self.write_ocean_prolog(wr)
		wr.skip()

		wr.comment("Calculate crossings")
		for (suffix,pct) in [("S", 0.1), ("M", 0.5), ("E", 0.9)]:
			wr.assign("X_RD_rise_"+suffix, "cross(VT(\"RD0\") VDD*%g 1 \"rising\")" % pct)
			wr.assign("X_RD_fall_"+suffix, "cross(VT(\"RD0\") VDD*%g 1 \"falling\")" % (1.0-pct))
		wr.skip()

		wr.comment("Calculate propagation times")
		wr.result("Tpd_RD_rise", "X_RD_rise_M - %g" % (3*self.T))
		wr.result("Tpd_RD_fall", "X_RD_fall_M - %g" % (5*self.T))
		wr.skip()

		wr.comment("Calculate transition times")
		wr.result("Ttran_RD_rise", "X_RD_rise_E - X_RD_rise_S")
		wr.result("Ttran_RD_fall", "X_RD_fall_E - X_RD_fall_S")
		wr.skip()

		self.write_ocean_epilog(wr)
		return wr.collect()


class Run(util.Run):
	def __init__(self, inp):
		super(Run, self).__init__(inp.macro)
		self.inp = inp

	def exec_spectre(self, filename, **kwargs):
		sys.stderr.write("Generating SPECTRE input %s\n" % filename)
		with open(filename, "w") as f:
			f.write(self.inp.make_spectre())
		super(Run, self).exec_spectre(filename, **kwargs)

	def exec_ocean(self, filename, **kwargs):
		sys.stderr.write("Generating OCEAN input %s\n" % filename)
		with open(filename, "w") as f:
			f.write(self.inp.make_ocean())
		super(Run, self).exec_ocean(filename, **kwargs)

	def run_spectre(self):
		self.make_netlist("netlist.cir")
		self.make_nodeset("nodeset.ns")
		self.exec_spectre("input.scs")

	def run_ocean(self):
		self.exec_ocean("analyze.ocn")

	def run(self):
		self.run_spectre()
		self.run_ocean()
