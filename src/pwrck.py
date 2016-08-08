# Copyright (c) 2016 Fabian Schuiki
import src.char


class Pwrck(src.char.RunInput):
	def __init__(self, macro, tslew, *args, **kwargs):
		super(Pwrck, self).__init__(macro, *args, **kwargs)
		self.tslew = tslew

	def generateInputs(self):
		num_addr = self.macro.num_addr
		num_bits = self.macro.num_bits
		T = 5e-9

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
			" ".join(["A%d" % i for i in range(num_addr)]),
			" ".join(["RD%d" % i for i in range(num_bits)]),
			" ".join(["A%d" % i for i in range(num_addr)]),
			" ".join(["WD" for i in range(num_bits)]),
			self.macro.name
		))

		scs.append("parameters vdd=%g tslew=%g" % (self.macro.vdd, self.tslew))
		scs.append("VDD (VDD 0) vsource type=dc dc=vdd")
		scs.append("VCK (CK 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g-tslew period=%g rise=tslew fall=tslew" % (T, T, 3*T))

		Tswp = (2**num_addr) * 3
		Ts_rd = 3
		Ts_wr = Ts_rd + Tswp
		Ts_rw = Ts_wr + Tswp
		Ts_done = Ts_rw + Tswp

		scs.append("VRE (RE 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g-tslew period=%g rise=tslew fall=tslew" % (
			Ts_rd*T, Tswp*T, 2*Tswp*T
		))
		scs.append("VWE (WE 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g-tslew rise=tslew fall=tslew" % (
			Ts_wr*T, 2*Tswp*T
		))

		for i in range(num_addr):
			scs.append("VA%d (A%d 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g-tslew period=%g rise=tslew fall=tslew" % (
				i, i,
				(Ts_rd + (2**i)*3)*T,
				(2**i*3)*T,
				(2**i*6)*T
			))

		scs.append("VWD (WD 0) vsource type=pulse val0=0 val1=vdd delay=%g width=%g-tslew period=%g rise=tslew fall=tslew" % (
			(Ts_wr)*T,
			3*T,
			6*T,
		))

		# Specify the transient analysis to perform.
		scs.append("tran tran stop=%g errpreset=conservative readns=\"%s\"" % ((Ts_done+1)*T, self.nodesetName))

		# Specify what to save.
		scs.append("save VDD:p")
		scs.append("save CK RE WE")
		scs.append("save A* depth=1")
		scs.append("save RD* depth=1")
		scs.append("save WD depth=1")

		# Generate the OCEAN script commands to analyze the power consumed.
		ocn.append("fprintf(p, \"P_leak,%%g\\n\", integ(-IT(\"VDD:p\") 0n %g) / %g * VDD)" % (1*T, 1*T))
		ocn.append("fprintf(p, \"E_idle_rise,%%g\\n\", integ(-IT(\"VDD:p\") %g %g) * VDD)" % (1*T, 2*T))
		ocn.append("fprintf(p, \"E_idle_fall,%%g\\n\", integ(-IT(\"VDD:p\") %g %g) * VDD)" % (2*T, 3*T))

		for p in [
				("read_rise",  0, 1), ("read_fall",  0, 2),
				("write_rise", 1, 1), ("write_fall", 1, 2),
				("rw_rise",    2, 1), ("rw_fall",    2, 2),
			]:
			ocn.append("fprintf(p, \"E_%s,%%g\\n\", (%s) / %d * VDD)" % (
				p[0],
				" + ".join(["integ(-IT(\"VDD:p\") %g %g)" % (
					((i+1)*3 + p[1]*Tswp + p[2]+0)*T,
					((i+1)*3 + p[1]*Tswp + p[2]+1)*T
				) for i in range(2**num_addr)]),
				2**num_addr
			))

		ocn.append("close(p)")

		# Generate the output.
		return ("\n".join(scs), "\n".join(ocn))


class PwrckRun(src.char.SimulationRun):
	def __init__(self, input, *args, **kwargs):
		super(PwrckRun, self).__init__(input, *args, **kwargs)

	def params(self):
		return [("tslew", self.input.tslew)]


class PwrckSweepRun(src.char.SweepSimulationRun):
	def __init__(self, macro, tslew, *args, **kwargs):
		super(PwrckSweepRun, self).__init__(*args, **kwargs)
		self.macro = macro
		self.tslew = tslew
		self.runs = [PwrckRun(Pwrck(macro, x), workdir=self.workpath("tslew=%g" % x)) for x in tslew]
