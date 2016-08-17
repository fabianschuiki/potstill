# Copyright (c) 2016 Fabian Schuiki
#
# This file implements input file generation and simulation execution for the
# propagation and transition time analysis of a full memory macro.

import sys, os, subprocess
import potstill, potstill.nodeset, potstill.netlist
from potstill.char import util
from potstill.char.util import ScsWriter, OcnWriter


class Input(util.Input):
	def __init__(self, macro, tslew, cload):
		super(Input, self).__init__(macro)
		self.tslew = tslew
		self.cload = cload
		self.T = 5e-9

	def make_spectre(self):
		wr = ScsWriter()
		wr.comment("Propagation and transition time analysis for "+self.macro.name)
		self.write_spectre_prolog(wr)
		wr.stmt("parameters", ("tslew", self.tslew), ("cload", self.cload))
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


class Run(util.RegularRun):
	pass
