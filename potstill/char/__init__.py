# Copyright (c) 2016 Fabian Schuiki
import sys, os, subprocess, csv
from collections import OrderedDict
import potstill.macro
import potstill.netlist
import potstill.nodeset


BASE = os.path.dirname(__file__)+"/../.."


def merge_dict(d, *args):
	r = OrderedDict(d)
	for x in args:
		r.update(x)
	return r


class RunInput(object):
	def __init__(self, macro, spectreOutputName="psf", oceanOutputName="results.csv", netlistName=None, nodesetName=None):
		super(RunInput, self).__init__()
		self.macro = macro
		self.spectreOutputName = spectreOutputName
		self.oceanOutputName = oceanOutputName
		self.netlistName = netlistName or (macro.name+".cir")
		self.nodesetName = nodesetName or (macro.name+".ns")

	def generateSpectreInput(self):
		return self.generateInputs()[0]

	def generateOceanInput(self):
		return self.generateInputs()[1]


class Run(object):
	def __init__(self, workdir=None):
		super(Run, self).__init__()
		self.workdir = workdir

	def workpath(self, path):
		return self.workdir+"/"+path if self.workdir is not None and not path.startswith("/") else path

	def run(self):
		self.generateInputs()
		self.runSpectre()
		self.runOcean()
		self.storeResults()


class SimulationRun(Run):
	def __init__(self, input, spectreInputName="input.scs", oceanInputName="analyze.ocn", *args, **kwargs):
		super(SimulationRun, self).__init__(*args, **kwargs)
		self.input = input
		self.spectreInputName = spectreInputName
		self.oceanInputName = oceanInputName

	def generateInputs(self):
		# Netlist
		with open(self.workpath(self.input.netlistName), "w") as f:
			f.write(potstill.netlist.generateMacro(self.input.macro))

		# Nodeset
		with open(self.workpath(self.input.nodesetName), "w") as f:
			f.write(potstill.nodeset.generateMacro("X", self.input.macro))

		# SPECTRE and OCEAN inputs
		inputs = self.input.generateInputs()
		with open(self.workpath(self.spectreInputName), "w") as f:
			f.write(inputs[0])
		with open(self.workpath(self.oceanInputName), "w") as f:
			f.write(inputs[1])

	def runSpectre(self):
		subprocess.check_call(["cds_mmsim", "spectre", self.spectreInputName, "+escchars", "+log", "spectre.out", "-format", "psfxl", "-raw", self.input.spectreOutputName, "++aps"], cwd=self.workdir)

	def runOcean(self):
		with subprocess.Popen(["cds_ic6", "ocean", "-log", "CDS.log", "-nograph"], stdin=subprocess.PIPE, universal_newlines=True, cwd=self.workdir) as ocean:
			ocean.stdin.write("load(\"%s\")\n" % self.oceanInputName)
			ocean.stdin.write("exit\n")
			ocean.stdin.flush()
			ocean.wait()
			if ocean.returncode != 0:
				sys.stderr.write("OCEAN script execution failed\n")
				sys.exit(ocean.returncode)

	def storeResults(self):
		pass

	def loadResults(self):
		with open(self.workpath(self.input.oceanOutputName)) as f:
			rd = csv.reader(f)
			return OrderedDict(list(rd))


class SweepRun(Run):
	def __init__(self, resultsName="results.csv", *args, **kwargs):
		super(SweepRun, self).__init__(*args, **kwargs)
		self.resultsName = resultsName

	# Collects the results of all runs in this sweep into a combined results
	# file.
	def storeResults(self):
		results = [potstill.char.merge_dict(run.params(), run.loadResults()) for run in self.runs]

		# Make a list of columns.
		columns = list()
		for r in results:
			for k in r.keys():
				if k not in columns:
					columns.append(k)

		# Store the results as CSV.
		with open(self.workpath(self.resultsName), "w") as f:
			wr = csv.writer(f)
			wr.writerow(columns)
			for r in results:
				row = [(r[k] if k in r else None) for k in columns]
				wr.writerow(row)

	# Returns all results of this sweep as an array of dictionaries.
	def loadResults(self):
		with open(self.workpath(self.resultsName)) as f:
			rd = csv.reader(f)
			columns = next(rd)
			return [OrderedDict(zip(columns, x)) for x in rd]


class SweepSimulationRun(SweepRun):
	def __init__(self, *args, **kwargs):
		super(SweepSimulationRun, self).__init__(*args, **kwargs)

	def generateInputs(self):
		for run in self.runs:
			if not os.path.exists(run.workdir):
				os.makedirs(run.workdir)
			run.generateInputs()

	def runSpectre(self):
		for run in self.runs:
			run.runSpectre()

	def runOcean(self):
		with subprocess.Popen(["cds_ic6", "ocean", "-log", "CDS.log", "-nograph"], stdin=subprocess.PIPE, universal_newlines=True, cwd=self.workdir) as ocean:
			for run in self.runs:
				ocean.stdin.write("cd(\"%s\")\n" % (os.getcwd()+"/"+run.workdir))
				ocean.stdin.write("load(\"%s\")\n" % run.oceanInputName)
				ocean.stdin.write("cd(\"%s\")\n" % os.getcwd())
			ocean.stdin.write("exit\n")
			ocean.stdin.flush()
			ocean.wait()
			if ocean.returncode != 0:
				sys.stderr.write("OCEAN script execution failed\n")
				sys.exit(ocean.returncode)


class MacroRun(Run):
	def __init__(self, macro, tslew, cload, *args, **kwargs):
		super(MacroRun, self).__init__(*args, **kwargs)
		self.macro = macro
		self.tslew = tslew
		self.cload = cload

		self.runs = list()
		self.runs.append(potstill.pwrck.PwrckSweepRun(macro, tslew, workdir="pwrck"))
		self.runs.append(potstill.pwrintcap.PwrintcapSweepRun(macro, tslew, workdir="pwrintcap"))
		self.runs.append(potstill.pwrout.PwroutSweepRun(macro, tslew, cload, workdir="pwrout"))
		self.runs.append(potstill.trdwr.TrdwrSweepRun(macro, tslew, cload, workdir="trdwr"))
		self.runs.append(potstill.tsuho.TsuhoSweepRun(macro, tslew, cload, workdir="tsuho"))

	def run(self):
		for run in self.runs:
			if not os.path.exists(run.workdir):
				os.makedirs(run.workdir)
			run.run()
