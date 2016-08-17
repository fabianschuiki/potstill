# Copyright (c) 2016 Fabian Schuiki
#
# Various utilities to produce SPECTRE and OCEAN input files.

import sys, os, subprocess, numbers, collections
import potstill.netlist, potstill.nodeset
from potstill.macro import Macro


# Writer that generates SPECTRE input text.
class ScsWriter(object):
	def __init__(self):
		super(ScsWriter, self).__init__()
		self.lines = list()

	def skip(self):
		self.lines.append("")

	def comment(self, *lines):
		self.lines += [("// " + (x or "")).strip() for x in lines]

	def include(self, *files):
		self.lines += ["include \"%s\""%x for x in files]

	def stmt(self, *args):
		self.lines.append(" ".join([x for x in [self.argify(a) for a in args] if x is not None]))

	def argify(self, v):
		if isinstance(v, (list,tuple)) and len(v) == 2:
			return v[0]+"="+self.argify(v[1]) if v[1] is not None else None
		if isinstance(v, numbers.Integral):
			return "%d" % v
		elif isinstance(v, numbers.Real):
			return "%.8g" % v
		else:
			return str(v)

	def tran(self, stop, *args, errpreset="conservative", readns="nodeset.ns"):
		self.stmt("tran", "tran", ("stop", stop), ("errpreset", errpreset), ("readns", readns), *args)

	def instance(self, name, terminals, *args):
		self.stmt(name, "("+" ".join([self.argify(t) for t in terminals])+")", *args)

	def vsource(self, name, out, gnd, ty, *args):
		self.instance(name, [out,gnd], "vsource", ("type", ty), *args)

	def vdc(self, name, out, *args, V="vdd", gnd=0):
		self.vsource(name, out, gnd, "dc", ("dc", V), *args)

	def vpulse(self, name, out, gnd, val0, val1, *args, delay=None, width=None, period=None, rise="tslew", fall="tslew"):
		self.vsource(name, out, gnd, "pulse", ("val0", val0), ("val1", val1), ("delay", delay), ("width", width), ("period", period), ("rise", rise), ("fall", fall), *args)

	def collect(self):
		return "\n".join([x.replace("\n", " \\\n") for x in self.lines])+"\n"


# Writer that generates OCEAN input text.
class OcnWriter(object):
	def __init__(self):
		super(OcnWriter, self).__init__()
		self.lines = list()

	def skip(self):
		self.lines.append("")

	def comment(self, *lines):
		self.lines += [("; " + (x or "")).strip() for x in lines]

	def add(self, *lines):
		for l in lines:
			assert(isinstance(l, str))
		self.lines += lines

	def assign(self, var, value):
		self.add(var+" = "+value)

	def call(self, *args):
		self.add(self.callexpr(*args))

	def callexpr(self, name, *args):
		return name + "("+", ".join(args)+")"

	def result(self, name, value, fd="fd"):
		self.call("fprintf", fd, "\"%s,%%g\\n\"" % name, value)

	def collect(self):
		return "\n".join([x.replace("\n", " \\\n") for x in self.lines])+"\n"


def argparse_init_macro(parser):
	parser.add_argument("NADDR", type=int, help="number of address lines")
	parser.add_argument("NBITS", type=int, help="number of bits per word")
	parser.add_argument("VDD", type=float, help="supply voltage [V]")
	parser.add_argument("TEMP", type=float, help="junction temperature [°C]")

def argparse_get_macro(args):
	return Macro(args.NADDR, args.NBITS, args.VDD, args.TEMP)


class Input(object):
	def __init__(self, macro, T=5e-9):
		super(Input, self).__init__()
		self.macro = macro
		self.T = T

	def write_spectre_prolog(self, wr):
		wr.include(os.path.dirname(__file__)+"/preamble.scs")
		wr.include("netlist.cir")
		wr.skip()

		wr.comment("Operating Conditions")
		wr.stmt("o1 options", ("temp", self.macro.temp), ("tnom", self.macro.temp))
		wr.stmt("parameters", ("vdd", self.macro.vdd))

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

	def write_ocean_prolog(self, wr, psf_path="psf", output_path="results.csv"):
		wr.add("openResults(\"%s\")" % psf_path)
		wr.add("selectResult('tran)")
		wr.add("VDD = %.8g" % self.macro.vdd)
		wr.add("fd = outfile(\"%s\", \"w\")" % output_path)

	def write_ocean_epilog(self, wr):
		wr.add("close(fd)")



class Run(object):
	def __init__(self, macro):
		super(Run, self).__init__()
		self.macro = macro

	def make_netlist(self, filename):
		sys.stderr.write("Generating netlist %s\n" % filename)
		with open(filename, "w") as f:
			f.write(potstill.netlist.generate(self.macro.num_addr, self.macro.num_bits))

	def make_nodeset(self, filename):
		sys.stderr.write("Generating nodeset %s\n" % filename)
		with open(filename, "w") as f:
			f.write(potstill.nodeset.generate("X", self.macro.num_addr, self.macro.num_bits))

	def exec_spectre(self, filename, output="psf", log="spectre.out", aps=True, format="psfxl", quiet=False):
		sys.stderr.write("Executing SPECTRE input %s\n" % filename)
		cmd = ["cds_mmsim", "spectre", filename, "+escchars", "+log", log, "-format", format, "-raw", output]
		if aps:
			cmd.append("+aps")
		subprocess.check_call(cmd, stdout=(subprocess.DEVNULL if quiet else None))

	def exec_ocean(self, filename, log="CDS.log"):
		sys.stderr.write("Executing OCEAN input %s\n" % filename)
		subprocess.check_call(["cds_ic6", "ocean", "-nograph", "-log", log, "-replay", filename])


class RegularRun(Run):
	def __init__(self, inp):
		super(RegularRun, self).__init__(inp.macro)
		self.inp = inp

	def make_spectre_input(self, filename, **kwargs):
		sys.stderr.write("Generating SPECTRE input %s\n" % filename)
		with open(filename, "w") as f:
			f.write(self.inp.make_spectre())

	def make_ocean_input(self, filename, **kwargs):
		sys.stderr.write("Generating OCEAN input %s\n" % filename)
		with open(filename, "w") as f:
			f.write(self.inp.make_ocean())

	def run_spectre(self):
		self.make_netlist("netlist.cir")
		self.make_nodeset("nodeset.ns")
		self.make_spectre_input("input.scs")
		self.exec_spectre("input.scs")

	def run_ocean(self):
		self.make_ocean_input("analyze.ocn")
		self.exec_ocean("analyze.ocn")

	def run(self):
		self.run_spectre()
		self.run_ocean()
