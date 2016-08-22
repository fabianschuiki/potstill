# Copyright (c) 2016 Fabian Schuiki
#
# This file implements input file generation and simulation execution for the
# internal power analysis of a full memory macro's clock pin. This essentially
# characterizes leakage power, idle, read, write and read+write energy. This
# setup differs from pwrck insofar that it causes the output pins to toggle,
# thus providing more realistic figures for comparison. pwrck is inteded for LIB
# file data generation.

import sys, os, potstill

from potstill.char import util
from potstill.char.util import ScsWriter, OcnWriter


class Input(util.Input):
	def __init__(self, macro, tslew, cload, **kwargs):
		super(Input, self).__init__(macro, **kwargs)
		self.desc = "Idle, read, write, and read/write power analysis"
		self.tslew = tslew
		self.cload = cload
		self.T = 5e-9
		self.Tcycle = 3*self.T

		self.Tstart_prep  =  0*self.Tcycle
		self.Tstart_idle  =  1*self.Tcycle
		self.Tstart_read  =  2*self.Tcycle
		self.Tstart_write =  4*self.Tcycle
		self.Tstart_rw    =  8*self.Tcycle
		self.Tend         = 12*self.Tcycle

	def make_spectre(self):
		wr = ScsWriter()
		self.write_spectre_prolog(wr)
		wr.stmt("parameters", ("tslew", self.tslew), ("cload", self.cload))
		wr.skip()

		wr.comment("Circuit Under Test")
		addrs = ["A"]*(self.macro.num_addr-1)
		self.write_spectre_cut(wr, RA=["0"]+addrs, WA=["WAH"]+addrs, WD="WD")
		for i in range(self.macro.num_bits):
			wr.instance("C%d"%i, ["RD%d"%i,0], "capacitor c=cload")
		wr.vdc("VDD", "VDD")
		wr.skip()

		wr.comment("Stimuli Generation")
		wr.vpulse("VCK", "CK", 0, 0, "vdd",
			delay=1*self.T,
			width=str(1*self.T)+"-tslew",
			period=self.Tcycle)

		wr.vpulse("VA", "A", 0, "vdd", 0,
			delay=self.Tstart_idle,
			width=str(self.Tcycle)+"-tslew",
			period=2*self.Tcycle)
		wr.vpulse("VWAH", "WAH", 0, 0, "vdd",
			delay=self.Tstart_idle)

		wr.vpulse("VRE0", "nRE1", 0, 0, "vdd",
			delay=self.Tstart_read,
			width=str(2*self.Tcycle)+"-tslew")
		wr.vpulse("VRE1", "RE", "nRE1", 0, "vdd",
			delay=self.Tstart_rw)

		wr.vpulse("VWE", "WE", 0, "vdd", 0,
			delay=self.Tstart_idle,
			width=str(self.Tstart_write-self.Tstart_idle)+"-tslew")

		wr.vpulse("VWD", "WD", 0, "vdd", 0,
			delay=self.Tstart_write+2*self.Tcycle,
			width=str(2*self.Tcycle)+"-tslew",
			period=4*self.Tcycle)
		wr.skip()

		wr.comment("Analysis")
		wr.tran(self.Tend) # needs errpreset=conservative, lest trapezoidal ringing
		wr.stmt("save VDD:p")
		wr.stmt("save CK A WAH RD0 RE WE WD")

		return wr.collect()

	def make_ocean(self):
		wr = OcnWriter()
		self.write_ocean_prolog(wr)
		wr.skip()

		wr.comment("Total energy deposited in the load capacitances during RD rising edge")
		wr.assign("E_cload", self.macro.num_bits * 0.5 * self.cload * self.macro.vdd**2)
		wr.skip()

		wr.comment("Calculate leakage power")
		wr.result("P_leak", "integ(-IT(\"VDD:p\") %g %g) / %g * VDD" % (
			0.75*self.T,
			1.00*self.T,
			0.25*self.T
		))
		wr.skip()

		wr.comment("Integrate energies")
		for (name, start, num_cycles, rd_toggle) in [
			("idle",  self.Tstart_idle,  1, False),
			("read",  self.Tstart_read,  2, True),
			("write", self.Tstart_write, 4, False),
			("rw",    self.Tstart_rw,    4, True)
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
				energy_expr = "%s*VDD/%d" % (
					joined,
					num_cycles
				)
				if rd_toggle and edge == "rise":
					energy_expr = "%s - %d*E_cload" % (energy_expr, num_cycles/2)
				wr.result("E_%s_%s" % (name, edge), energy_expr)
		wr.skip()

		self.write_ocean_epilog(wr)
		return wr.collect()


class Run(util.RegularRun):
	pass
