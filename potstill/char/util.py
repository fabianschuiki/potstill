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

	def argify(self, v):
		if isinstance(v, numbers.Integral):
			return "%d" % v
		elif isinstance(v, numbers.Real):
			return "%.8g" % v
		else:
			return str(v)

	def skip(self):
		self.lines.append("")

	def comment(self, *lines):
		self.lines += [("; " + (x or "")).strip() for x in lines]

	def add(self, *lines):
		for l in lines:
			assert(isinstance(l, str))
		self.lines += lines

	def assign(self, var, value):
		self.add(var+" = "+self.argify(value))

	def call(self, *args):
		self.add(self.callexpr(*args))

	def callexpr(self, name, *args):
		return name + "("+", ".join([self.argify(a) for a in args])+")"

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


class CommonArgs(object):
	def __init__(self, parser, no_spectre=False, no_ocean=False):
		super(CommonArgs, self).__init__()
		self.parser = parser
		self.args = None
		self.no_spectre = no_spectre
		self.no_ocean = no_ocean

		# Add arguments to specify the macro.
		argparse_init_macro(parser)

		# Add SPECTRE-specific options.
		if not no_spectre:
			parser.add_argument("--dump-spectre", action="store_true", help="write SPECTRE input file to stdout")
			parser.add_argument("--only-spectre", action="store_true", help="only run SPECTRE")

			parser.add_argument("--spectre", type=str, help="name of the SPECTRE input file")
			parser.add_argument("--netlist", type=str, help="name of the netlist file")
			parser.add_argument("--nodeset", type=str, help="name of the nodeset file")

			parser.add_argument("--keep-spectre", action="store_true", help="don't create new SPECTRE input file")
			parser.add_argument("--keep-netlist", action="store_true", help="don't create new netlist file")
			parser.add_argument("--keep-nodeset", action="store_true", help="don't create new nodeset file")

			parser.add_argument("-c", "--cut", type=str, help="name of the circuit to instantiate")

		# Add OCEAN-specific options.
		if not no_ocean:
			parser.add_argument("--dump-ocean", action="store_true", help="write OCEAN input file to stdout")
			parser.add_argument("--only-ocean", action="store_true", help="only run OCEAN")
			parser.add_argument("--ocean", type=str, help="name of the OCEAN input file")
			parser.add_argument("--keep-ocean", action="store_true", help="don't create new OCEAN input file")

	def parse(self, *args, **kwargs):
		self.args = self.parser.parse_args(*args, **kwargs)
		return self.args

	def get_macro(self):
		return argparse_get_macro(self.args)

	def get_input_kwargs(self):
		opts = dict()
		if not self.no_spectre:
			opts["netlist_name"] = self.args.netlist
			opts["nodeset_name"] = self.args.nodeset
			opts["cut_name"] = self.args.cut
		return opts

	def get_run_kwargs(self):
		opts = dict()
		if not self.no_spectre:
			opts["dont_netlist"] = self.args.keep_netlist
			opts["dont_nodeset"] = self.args.keep_nodeset
		return opts

	def handle_input(self, inp):
		if self.args.dump_spectre:
			sys.stdout.write(inp.make_spectre())
			sys.exit(0)
		if self.args.dump_ocean:
			sys.stdout.write(inp.make_ocean())
			sys.exit(0)
		pass

	# Acts upon a run object based on various switches and options parsed from
	# the command line. The function calls sys.exit(0) if the run has been
	# executed, otherwise it returns and it is up to the caller to perform the
	# run.
	def handle_run(self, run):
		if not self.no_spectre:
			if self.args.only_spectre:
				run.run_spectre()
				sys.exit(0)
		if not self.no_ocean:
			if self.args.only_ocean:
				run.run_ocean()
				sys.exit(0)


def add_common_args(parser):
	argparse_init_macro(parser)

def get_macro(args):
	return argparse_get_macro(args)

def get_input_kwargs(args):
	return dict()

def get_run_kwargs(args):
	return dict()


class Input(object):
	def __init__(self, macro, T=5e-9, cut_name=None, netlist_name=None, nodeset_name=None, results_name=None):
		super(Input, self).__init__()
		self.macro = macro
		self.T = T
		self.cut_name = cut_name or self.macro.name
		self.netlist_name = netlist_name or "netlist.cir"
		self.nodeset_name = nodeset_name or "nodeset.ns"
		self.results_name = results_name or "results.csv"
		self.desc = None

	def write_spectre_prolog(self, wr):
		wr.comment(
			None,
			self.cut_name,
			"%d words, %d bits, at %gV, %g°C" % (self.macro.num_words, self.macro.num_bits, self.macro.vdd, self.macro.temp),
			None
		)
		if self.desc is not None:
			wr.comment(self.desc, None)
		wr.include(os.path.dirname(__file__)+"/preamble.scs")
		wr.include(self.netlist_name)
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
			(RA or ["RA%d" % i for i in reversed(range(self.macro.num_addr))], self.macro.num_addr),
			(["RD%d" % i for i in reversed(range(self.macro.num_bits))], self.macro.num_bits),
			(WE, 1),
			(WA or ["WA%d" % i for i in reversed(range(self.macro.num_addr))], self.macro.num_addr),
			(WD or ["WD%d" % i for i in reversed(range(self.macro.num_bits))], self.macro.num_bits)
		]:
			if isinstance(t, list):
				l = list(t)
				assert(len(l) == n)
				terms += l
			else:
				terms += [t]*n
		terms.append(VDD)
		terms.append(VSS)
		wr.instance("X", terms, self.cut_name)

	def write_ocean_prolog(self, wr, psf_path="psf", output_path="results.csv"):
		wr.comment(
			None,
			self.cut_name,
			"%d words, %d bits, at %gV, %g°C" % (self.macro.num_words, self.macro.num_bits, self.macro.vdd, self.macro.temp),
			None
		)
		if self.desc is not None:
			wr.comment(self.desc, None)
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
	def __init__(self, inp, dont_netlist=False, dont_nodeset=False, **kwargs):
		super(RegularRun, self).__init__(inp.macro, **kwargs)
		self.inp = inp
		self.dont_netlist = dont_netlist
		self.dont_nodeset = dont_nodeset

	def make_spectre_input(self, filename, **kwargs):
		sys.stderr.write("Generating SPECTRE input %s\n" % filename)
		with open(filename, "w") as f:
			f.write(self.inp.make_spectre())

	def make_ocean_input(self, filename, **kwargs):
		sys.stderr.write("Generating OCEAN input %s\n" % filename)
		with open(filename, "w") as f:
			f.write(self.inp.make_ocean())

	def run_spectre(self):
		if not self.dont_netlist:
			self.make_netlist(self.inp.netlist_name)
		if not self.dont_nodeset:
			self.make_nodeset(self.inp.nodeset_name)
		self.make_spectre_input("input.scs")
		self.exec_spectre("input.scs")

	def run_ocean(self):
		self.make_ocean_input("analyze.ocn")
		self.exec_ocean("analyze.ocn")

	def run(self):
		self.run_spectre()
		self.run_ocean()
