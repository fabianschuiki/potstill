# Copyright (c) 2016 Fabian Schuiki
import potstill.char
import itertools


class Trdwr(potstill.char.RunInput):
	def __init__(self, macro, tslew, cload, *args, **kwargs):
		super(Trdwr, self).__init__(macro, *args, **kwargs)
		self.tslew = tslew
		self.cload = cload

	def generateInputs(self):
		num_addr = self.macro.num_addr
		num_bits = self.macro.num_bits
		T = 1e-9

		scs = list()
		ocn = list()

		scs.append("// %s" % self.macro.name)
		scs.append("include \"%s/sim/preamble.scs\"" % potstill.char.BASE)
		scs.append("include \"%s\"" % self.netlistName)
		scs.append("o1 options temp=%g tnom=%g" % (self.macro.temp, self.macro.temp))

		ocn.append("openResults(\"%s\")" % self.spectreOutputName)
		ocn.append("selectResult('tran)")
		ocn.append("VDD = %g" % self.macro.vdd)
		ocn.append("p = outfile(\"%s\", \"w\")" % self.oceanOutputName)

		scs.append("X (CK RE %s %s WE %s %s VDD 0) %s" % (
			" ".join(["VDD" for i in range(num_addr)]),
			" ".join(["RD%d" % i for i in range(num_bits)]),
			" ".join(["VDD" for i in range(num_addr)]),
			" ".join(["VDD" for i in range(num_bits)]),
			self.macro.name
		))
		for i in range(num_bits):
			scs.append("C%d (RD%d 0) capacitor c=cload\n" % (i, i))

		scs.append("parameters vdd=%g tslew=%g cload=%g" % (self.macro.vdd, self.tslew, self.cload))
		scs.append("VDD (VDD 0) vsource type=dc dc=vdd")
		scs.append("VCK (CK 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g-tslew period=%g rise=tslew fall=tslew" % (1*T, 1*T, 3*T))
		scs.append("VWE (WE 0) vsource type=pulse val0=vdd val1=0 delay=%g rise=tslew fall=tslew" % (3*T))
		scs.append("VRE (RE 0) vsource type=pulse val0=0 val1=vdd delay=%g rise=tslew fall=tslew" % (3*T))

		scs.append("tran tran stop=%g errpreset=conservative readns=\"%s\"" % (6*T, self.nodesetName))

		# Save CK, RD, and the internal memory latch outputs such that we can analyze the delays.
		scs.append("save CK RE WE")
		scs.append("save RD* depth=1")
		scs.append("save X.XBA*.X%d.nZ" % (2**num_addr-1))

		# Generate the OCEAN script.
		ocn.append("fprintf(p, \"t_wr,%%g\\n\", cross(VT(\"X.XBA0.X%d.nZ\") VDD/2 1) - cross(VT(\"CK\") VDD/2 1))" % (2**num_addr-1))
		ocn.append("fprintf(p, \"t_rd,%g\\n\", cross(VT(\"RD0\") VDD/2 1) - cross(VT(\"CK\") VDD/2 3))")
		ocn.append("close(p)")

		# Generate the output.
		return ("\n".join(scs), "\n".join(ocn))


class TrdwrRun(potstill.char.SimulationRun):
	def __init__(self, input, *args, **kwargs):
		super(TrdwrRun, self).__init__(input, *args, **kwargs)

	def params(self):
		return [("tslew", self.input.tslew), ("cload", self.input.cload)]


class TrdwrSweepRun(potstill.char.SweepSimulationRun):
	def __init__(self, macro, tslew, cload, *args, **kwargs):
		super(TrdwrSweepRun, self).__init__(*args, **kwargs)
		self.macro = macro
		self.tslew = tslew
		self.cload = cload
		self.runs = [TrdwrRun(Trdwr(macro, *x), workdir=self.workpath("tslew=%g,cload=%g" % x)) for x in itertools.product(tslew, cload)]
