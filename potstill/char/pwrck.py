# Copyright (c) 2016 Fabian Schuiki
#
# This file implements input file generation and simulation execution for the
# internal power analysis of a full memory macro's clock pin. This essentially
# characterizes leakage power, idle, read, write, and read+write energy.

import sys, os
import potstill
from potstill.char import util
from potstill.char.util import ScsWriter, OcnWriter


class Input(util.Input):
	def __init__(self, macro, tslew):
		super(Input, self).__init__(macro)
		self.tslew = tslew
		self.T = 5e-9
		self.Tcycle = 3*self.T

		self.Tstart_idle  = 1*self.Tcycle
		self.Tstart_read  = 2*self.Tcycle
		self.Tstart_write = 4*self.Tcycle
		self.Tstart_rw    = 6*self.Tcycle

	def make_spectre(self):
		wr = ScsWriter()
		wr.comment("Internal clock power analysis for "+self.macro.name)
		self.write_spectre_prolog(wr)
		wr.stmt("parameters", ("tslew", self.tslew))
		wr.skip()

		wr.comment("Circuit Under Test")
		addrs = ["A"]*(self.macro.num_addr-1)
		self.write_spectre_cut(wr, RA=["0"]+addrs, WA=["VDD"]+addrs, WD="VDD")
		wr.vdc("VDD", "VDD")
		wr.skip()

		wr.comment("Stimuli Generation")
		wr.vpulse("VCK", "CK", 0, 0, "vdd",
			delay=1*self.T,
			width=str(1*self.T)+"-tslew",
			period=self.Tcycle)
		wr.vpulse("VA", "A", 0, 0, "vdd",
			delay=2*self.Tcycle,
			width=str(self.Tcycle)+"-tslew",
			period=2*self.Tcycle)
		wr.vpulse("VRE", "RE", 0, 0, "vdd",
			delay=self.Tstart_read,
			width=str(2*self.Tcycle)+"-tslew",
			period=4*self.Tcycle)
		wr.vpulse("VWE", "WE", 0, 0, "vdd",
			delay=self.Tstart_write)
		wr.skip()

		wr.comment("Analysis")
		wr.tran(8*self.Tcycle)
		wr.stmt("save VDD:p")
		wr.stmt("save CK A RD* RE WE")

		return wr.collect()

	def make_ocean(self):
		wr = OcnWriter()
		wr.comment("Internal clock power analysis for "+self.macro.name)
		self.write_ocean_prolog(wr)
		wr.skip()

		wr.comment("Calculate leakage power")
		wr.result("P_leak", "integ(-IT(\"VDD:p\") %g %g) / %g * VDD" % (
			0*self.T,
			1*self.T,
			1*self.T
		))
		wr.skip()

		wr.comment("Integrate energies")
		for (name, start, num_cycles) in [
			("idle", self.Tstart_idle, 1),
			("read", self.Tstart_read, 2),
			("write", self.Tstart_write, 2),
			("rw", self.Tstart_rw, 2)
		]:
			for (offset, edge) in [(0, "rise"), (1, "fall")]:
				stops = [start + (1+offset)*self.T + i*self.Tcycle for i in range(num_cycles)]
				parts = [
					"integ(-IT(\"VDD:p\") %g %g)" % (stop, stop+self.T)
					for stop in stops
				]
				joined = " + ".join(parts)
				if len(parts) > 1:
					joined = "("+joined+")"
				wr.result("E_%s_%s" % (name, edge), "%s*VDD/%d" % (
					joined,
					num_cycles
				))
		wr.skip()

		self.write_ocean_epilog(wr)
		return wr.collect()


class Run(util.RegularRun):
	pass
