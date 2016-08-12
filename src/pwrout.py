# Copyright (c) 2016 Fabian Schuiki
import src.char
import itertools


class Pwrout(src.char.RunInput):
	def __init__(self, macro, tslew, cload, *args, **kwargs):
		super(Pwrout, self).__init__(macro, *args, **kwargs)
		self.tslew = tslew
		self.cload = cload

	def generateInputs(self):
		num_addr = self.macro.num_addr
		num_bits = self.macro.num_bits
		T = 1e-9
		Ecap = 0.5*self.cload*(self.macro.vdd**2) # energy stored in load capacitance

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
			" ".join(["VDD" for i in range(num_addr)]),
			" ".join(["VDD" for i in range(num_bits)]),
			self.macro.name
		))
		for i in range(num_bits):
			scs.append("C%d (RD%d 0) capacitor c=cload" % (i, i))

		scs.append("parameters vdd=%g tslew=%g cload=%g" % (self.macro.vdd, self.tslew, self.cload))
		scs.append("VDD (VDD 0) vsource type=dc dc=vdd")
		scs.append("VCK (CK 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g-tslew period=%g rise=tslew fall=tslew" % (1*T, 1*T, 3*T))
		scs.append("VWE (WE 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g-tslew rise=tslew fall=tslew" % (3*T, 3*T))
		scs.append("VRE (RE 0) vsource type=pulse val0=vdd val1=0 delay=%g width=%g-tslew rise=tslew fall=tslew" % (3*T, 3*T))
		scs.append("VRA (RA 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g-tslew rise=tslew fall=tslew" % (6*T, 3*T))

		# Calculate the energy consumed by the clock, which needs to be subtracted from
		# the energy consumed by the circuit during a change in output.
		ocn.append("E_CK = integ(-IT(\"VDD:p\") %g %g) * VDD" % (1*T, 3*T))
		ocn.append("printf(\"E_CK = %g\\n\", E_CK)")

		# For each RD output pin, calculate the energy consumed by the circuit and
		# subtract the energy due to the two clock edges and the energy that was
		# deposited in the capacitor.
		ocn.append("E_RD_rise = integ(-IT(\"VDD:p\") %g %g) * VDD - E_CK - %g" % (7*T, 9*T, num_bits*Ecap))
		ocn.append("E_RD_fall = integ(-IT(\"VDD:p\") %g %g) * VDD - E_CK" % (10*T, 12*T))

		for i in range(num_bits):
			ocn.append("fprintf(p, \"E_RD%d_rise,%%g\\n\", E_RD_rise/%d)" % (i, num_bits))
			ocn.append("fprintf(p, \"E_RD%d_fall,%%g\\n\", E_RD_fall/%d)" % (i, num_bits))

		# Specify the simulation to perform.
		scs.append("tran tran stop=%g errpreset=conservative readns=\"%s\"" % (12*T, self.nodesetName))

		# Specify what to save.
		scs.append("save VDD:p")
		# scs.append("save CK RE WE")
		# scs.append("save RD* depth=1")
		# scs.append("save X:currents")

		ocn.append("close(p)")

		# Generate the output.
		return ("\n".join(scs), "\n".join(ocn))


class PwroutRun(src.char.SimulationRun):
	def __init__(self, input, *args, **kwargs):
		super(PwroutRun, self).__init__(input, *args, **kwargs)

	def params(self):
		return [("tslew", self.input.tslew), ("cload", self.input.cload)]


class PwroutSweepRun(src.char.SweepSimulationRun):
	def __init__(self, macro, tslew, cload, *args, **kwargs):
		super(PwroutSweepRun, self).__init__(*args, **kwargs)
		self.macro = macro
		self.tslew = tslew
		self.cload = cload
		self.runs = [PwroutRun(Pwrout(macro, *x), workdir=self.workpath("tslew=%g,cload=%g") % x) for x in itertools.product(tslew, cload)]
