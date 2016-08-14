# Copyright (c) 2016 Fabian Schuiki
import potstill.char


class Pwrintcap(potstill.char.RunInput):
	def __init__(self, macro, tslew, *args, **kwargs):
		super(Pwrintcap, self).__init__(macro, *args, **kwargs)
		self.tslew = tslew

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

		pins_RA = ["RA%d" % i for i in range(num_addr)]
		pins_RD = ["RD%d" % i for i in range(num_bits)]
		pins_WA = ["WA%d" % i for i in range(num_addr)]
		pins_WD = ["WD%d" % i for i in range(num_bits)]

		terminals = ["CK","RE"]+pins_RA+pins_RD+["WE"]+pins_WA+pins_WD
		terminalIndices = dict()
		for idx, name in enumerate(terminals):
			terminalIndices[name] = idx + 1

		scs.append("X (%s VDD 0) %s" % (
			" ".join(terminals),
			self.macro.name
		))

		scs.append("parameters vdd=%g tslew=%g" % (self.macro.vdd, self.tslew))
		scs.append("VDD (VDD 0) vsource type=dc dc=vdd")

		all_pins = (["CK", "RE", "WE"]+pins_RA+pins_WA+pins_WD)
		x = 1
		i = 0
		for p in all_pins:
			scs.append("V%d (%s 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g-tslew rise=tslew fall=tslew" % (
				i, p, x*T, 1*T
			))
			ocn.append("printf(\"Characterizing pin %s\\n\")" % p)
			if p != "CK":
				ocn.append("fprintf(p, \"E_%s_rise,%%g\\n\", integ(-IT(\"VDD:p\") %g %g) * VDD)" % (p, x*T, (x+1)*T))
				ocn.append("fprintf(p, \"E_%s_fall,%%g\\n\", integ(-IT(\"VDD:p\") %g %g) * VDD)" % (p, (x+1)*T, (x+2)*T))
			ocn.append("fprintf(p, \"C_%s,%%g\\n\", integ(abs(IT(\"X:%d\")) %g %g) / VDD)" % (p, terminalIndices[p], x*T, (x+2)*T))
			x += 2
			i += 1

		scs.append("tran tran stop=%g errpreset=conservative readns=\"%s\"" % (x*T, self.nodesetName))

		# Specify what to save.
		scs.append("save VDD:p")
		scs.append("save CK RE WE")
		scs.append("save RA* depth=1")
		scs.append("save WA* depth=1")
		scs.append("save WD* depth=1")
		scs.append("save %s" % (" ".join(["X:"+s for s in all_pins])))

		ocn.append("close(p)")

		# Generate the output.
		return ("\n".join(scs), "\n".join(ocn))


class PwrintcapRun(potstill.char.SimulationRun):
	def __init__(self, input, *args, **kwargs):
		super(PwrintcapRun, self).__init__(input, *args, **kwargs)

	def params(self):
		return [("tslew", self.input.tslew)]


class PwrintcapSweepRun(potstill.char.SweepSimulationRun):
	def __init__(self, macro, tslew, *args, **kwargs):
		super(PwrintcapSweepRun, self).__init__(*args, **kwargs)
		self.macro = macro
		self.tslew = tslew
		self.runs = [PwrintcapRun(Pwrintcap(macro, x), workdir=self.workpath("tslew=%g" % x)) for x in tslew]
