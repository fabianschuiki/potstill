# Copyright (c) 2016 Fabian Schuiki
import os
import subprocess
import src.macro
import src.netlist

BASE = os.path.dirname(__file__)+"/.."


class Pwrck(object):
	def __init__(self, macro, vdd, tslew, spectreOutputName="psf", oceanOutputName="results.csv", netlistName=None, nodesetName=None):
		super(Pwrck, self).__init__()
		self.macro = macro
		self.vdd = vdd
		self.tslew = tslew
		self.spectreOutputName = spectreOutputName
		self.oceanOutputName = oceanOutputName
		self.netlistName = netlistName or (macro.name+".cir")
		self.nodesetName = nodesetName or (macro.name+".ns")

	def generateSpectreInput(self):
		return self.generateInputs()[0]

	def generateOceanInput(self):
		return self.generateInputs()[1]

	def generateInputs(self):
		num_addr = self.macro.num_addr
		num_bits = self.macro.num_bits
		cname = self.macro.name
		VDD = self.vdd
		T = 5

		scs = list()
		ocn = list()

		scs.append("// %s" % cname)
		scs.append("include \"%s/sim/preamble.scs\"" % BASE)
		scs.append("include \"%s.cir\"" % cname)

		scs.append("X (CK RE %s %s WE %s %s VDD 0) %s" % (
			" ".join(["A%d" % i for i in range(num_addr)]),
			" ".join(["RD%d" % i for i in range(num_bits)]),
			" ".join(["A%d" % i for i in range(num_addr)]),
			" ".join(["WD%d" % i for i in range(num_bits)]),
			cname
		))

		scs.append("parameters tslew=%g" % self.tslew)
		scs.append("VDD (VDD 0) vsource type=dc dc=%g" % VDD)
		scs.append("VCK (CK 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew period=%gn rise=tslew fall=tslew" % (VDD, T, T, 3*T))

		Tswp = (2**num_addr) * 3
		Ts_rd = 3
		Ts_wr = Ts_rd + Tswp
		Ts_rw = Ts_wr + Tswp
		Ts_done = Ts_rw + Tswp

		scs.append("VRE (RE 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew period=%gn rise=tslew fall=tslew" % (
			VDD, Ts_rd*T, Tswp*T, 2*Tswp*T
		))
		scs.append("VWE (WE 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew rise=tslew fall=tslew" % (
			VDD, Ts_wr*T, 2*Tswp*T
		))

		for i in range(num_addr):
			scs.append("VA%d (A%d 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew period=%gn rise=tslew fall=tslew" % (
				i, i, VDD,
				(Ts_rd + (2**i)*3)*T,
				(2**i*3)*T,
				(2**i*6)*T
			))

		for i in range(num_bits):
			scs.append("VWD%d (WD%d 0) vsource type=dc dc=0" % (i,i))

		# Specify the transient analysis to perform.
		scs.append("tran tran stop=%gn errpreset=conservative readns=\"%s.ns\"" % ((Ts_done+1)*T, cname))

		# Specify what to save.
		scs.append("save VDD:p")
		scs.append("save CK RE WE")
		scs.append("save A* depth=1")
		scs.append("save RD* depth=1")
		scs.append("save WD* depth=1")

		# Generate the OCEAN script commands to analyze the power consumed.
		ocn.append("openResults(\"%s\")" % self.spectreOutputName)
		ocn.append("selectResult('tran)")

		ocn.append("p = outfile(\"%s\", \"w\")" % self.oceanOutputName)
		ocn.append("fprintf(p, \"P_leak,%%g\\n\", integ(-IT(\"VDD:p\") 0n %gn) / %gn * 1.2)" % (1*T, 1*T))
		ocn.append("fprintf(p, \"E_idle_rise,%%g\\n\", integ(-IT(\"VDD:p\") %gn %gn) * 1.2)" % (1*T, 2*T))
		ocn.append("fprintf(p, \"E_idle_fall,%%g\\n\", integ(-IT(\"VDD:p\") %gn %gn) * 1.2)" % (2*T, 3*T))

		for p in [
				("read_rise",  0, 1), ("read_fall",  0, 2),
				("write_rise", 1, 1), ("write_fall", 1, 2),
				("rw_rise",    2, 1), ("rw_fall",    2, 2),
			]:
			ocn.append("fprintf(p, \"E_%s,%%g\\n\", (%s) / %d * 1.2)" % (
				p[0],
				" + ".join(["integ(-IT(\"VDD:p\") %gn %gn)" % (
					((i+1)*3 + p[1]*Tswp + p[2]+0)*T,
					((i+1)*3 + p[1]*Tswp + p[2]+1)*T
				) for i in range(2**num_addr)]),
				2**num_addr
			))

		ocn.append("close(p)")

		# Generate the output.
		return ("\n".join(scs), "\n".join(ocn))


class PwrckRun(object):
	def __init__(self, pwrck, spectreInputName="input.scs", oceanInputName="analyze.ocn"):
		super(PwrckRun, self).__init__()
		self.pwrck = pwrck
		self.spectreInputName = spectreInputName
		self.oceanInputName = oceanInputName

	def generateInputs(self):
		with open(self.pwrck.netlistName, "w") as f:
			f.write(src.netlist.generateMacro(self.pwrck.macro))
		with open(self.pwrck.nodesetName, "w") as f:
			f.write(src.nodeset.generateMacro("X", self.pwrck.macro))
		inputs = self.pwrck.generateInputs()
		with open(self.spectreInputName, "w") as f:
			f.write(inputs[0])
		with open(self.oceanInputName, "w") as f:
			f.write(inputs[1])

	def runSpectre(self):
		subprocess.check_call(["cds_mmsim", "spectre", self.spectreInputName, "+escchars", "+log", "spectre.out", "-format", "psfxl", "-raw", self.pwrck.spectreOutputName, "++aps"])

	def runOcean(self):
		with subprocess.Popen(["cds_ic6", "ocean", "-nograph"], stdin=subprocess.PIPE, universal_newlines=True) as ocean:
			ocean.stdin.write("load(\"%s\")\n" % self.oceanInputName)
			ocean.stdin.write("exit\n")
			ocean.stdin.flush()
			ocean.wait()
			if ocean.returncode != 0:
				sys.stderr.write("OCEAN script execution failed\n")
				sys.exit(ocean.returncode)

	def run(self):
		self.generateInputs()
		self.runSpectre()
		self.runOcean()


class PwrckSweepRun(object):
	def __init__(self, macro, vdd, tslew):
		super(PwrckSweepRun, self).__init__()
		self.macro = macro
		self.vdd = vdd
		self.tslew = tslew
		self.runs = [(
			"tslew=%g" % x,
			PwrckRun(Pwrck(macro, vdd, x))
		) for x in tslew]

	def generateInputs(self):
		for name, run in self.runs:
			if not os.path.exists(name):
				os.makedirs(name)
			pwd = os.getcwd()
			os.chdir(name)
			run.generateInputs()
			os.chdir(pwd)

	def runSpectre(self):
		for name, run in self.runs:
			pwd = os.getcwd()
			os.chdir(name)
			run.runSpectre()
			os.chdir(pwd)

	def runOcean(self):
		with subprocess.Popen(["cds_ic6", "ocean", "-nograph"], stdin=subprocess.PIPE, universal_newlines=True) as ocean:
			for name, run in self.runs:
				ocean.stdin.write("cd(\"%s\")\n" % name)
				ocean.stdin.write("load(\"%s\")\n" % run.oceanInputName)
				ocean.stdin.write("cd(\"%s\")\n" % os.getcwd())
			ocean.stdin.write("exit\n")
			ocean.stdin.flush()
			ocean.wait()
			if ocean.returncode != 0:
				sys.stderr.write("OCEAN script execution failed\n")
				sys.exit(ocean.returncode)

	def run(self):
		self.generateInputs()
		self.runSpectre()
		self.runOcean()
