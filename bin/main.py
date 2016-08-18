#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
#
# TODO: Get rid of this file. It is only used to run the pwrintcap, pwrout, and
#       trdwr characterizations. These better be implemented as
#       commands/char-*.py files. Eventually this file disappears.

import sys, os
import math
import argparse
import yaml
import subprocess
import potstill.macro
import potstill.pwrintcap
import potstill.pwrout
import potstill.trdwr

BASE = sys.path[0]+"/.."


def mainChar(argv):

	parser = argparse.ArgumentParser(
		description="Perform characterization for memory macros.",
		prog="char"
	)
	parser.add_argument("num_addr", metavar="NADDR", type=int, help="number of address lines")
	parser.add_argument("num_bits", metavar="NBITS", type=int, help="number of bits")
	parser.add_argument("char", metavar="CHAR", type=str, help="characterization to perform")
	parser.add_argument("--vdd", metavar="VDD", type=float, default=1.2, help="supply voltage [V]")
	parser.add_argument("--temp", metavar="T", type=float, default=25, help="junction temperature [°C]")
	parser.add_argument("args", nargs=argparse.REMAINDER)
	args = parser.parse_args(argv)

	macro = potstill.macro.MacroConditions(args.num_addr, args.num_bits, vdd=args.vdd, temp=args.temp)

	if args.char == "all":
		mainCharMacroAll(macro, args.args)
	else:
		mainCharMacro(macro, args.char, args.args)


def mainCharMacroAll(macro, argv):
	parser = argparse.ArgumentParser(description="Characterize all aspects of a macro.", prog="all")
	parser.add_argument("--tslew", metavar="TSLEW", type=float, nargs="+", help="input transition times to evaluate", required=True)
	parser.add_argument("--cload", metavar="CLOAD", type=float, nargs="+", help="output pin load capacitance to evaluate", required=True)
	args = parser.parse_args(argv)

	run = potstill.char.MacroRun(macro, args.tslew, args.cload)
	run.run()


def mainCharMacro(macro, charName, argv):
	mainName = "mainChar" + charName.capitalize()
	if mainName not in globals():
		sys.stderr.write("Unknown characterization command \"%s\"\n\n" % charName)
		printCharUsage()
		sys.exit(1)

	parser = argparse.ArgumentParser()
	parser.add_argument("-r", "--run", action="store_true", help="implies -isac")
	parser.add_argument("-i", "--inputs", action="store_true", dest="generateInputs", help="generate SPECTRE and OCEAN input files")
	parser.add_argument("-s", "--simulate", action="store_true", dest="runSpectre", help="run SPECTRE simulation")
	parser.add_argument("-a", "--analyze", action="store_true", dest="runOcean", help="run OCEAN analysis")
	parser.add_argument("-c", "--results", action="store_true", dest="storeResults", help="collect results of individual runs")
	parser.add_argument("--dump-spectre", action="store_true", dest="dumpSpectreInput", help="write SPECTRE input to stdout")
	parser.add_argument("--dump-ocean", action="store_true", dest="dumpOceanInput", help="write OCEAN input to stdout")
	parser.add_argument("--dump-results", action="store_true", help="write results to stdout")

	(args, input, run) = globals()[mainName](macro, parser, argv)

	if args.dumpSpectreInput:
		print(input.generateSpectreInput())
		sys.exit(0)
	if args.dumpOceanInput:
		print(input.generateOceanInput())
		sys.exit(0)

	if args.generateInputs:
		run.generateInputs()
	if args.runSpectre:
		run.runSpectre()
	if args.runOcean:
		run.runOcean()
	if args.run:
		run.run()
	if args.storeResults:
		run.storeResults()
	if args.dump_results:
		print(run.loadResults())


def mainCharPwrintcap(macro, parentParser, argv):
	parser = argparse.ArgumentParser(description="Perform internal power and pin capacitance characterization for all inputs, excluding the clock.", prog="pwrintcap", parents=[parentParser], add_help=False)
	parser.add_argument("tslew", metavar="TSLEW", type=float, nargs="+", help="transition time of the input signals")
	args = parser.parse_args(argv)

	if len(args.tslew) == 1:
		input = potstill.pwrintcap.Pwrintcap(macro, args.tslew[0])
		run = potstill.pwrintcap.PwrintcapRun(input)
		return (args, input, run)
	else:
		run = potstill.pwrintcap.PwrintcapSweepRun(macro, args.tslew)
		return (args, None, run)


def mainCharPwrout(macro, parentParser, argv):
	parser = argparse.ArgumentParser(description="Perform internal power characterization for all outputs.", prog="pwrout", parents=[parentParser], add_help=False)
	parser.add_argument("--tslew", metavar="TSLEW", type=float, nargs="+", help="transition time of the input signals", required=True)
	parser.add_argument("--cload", metavar="CLOAD", type=float, nargs="+", help="output pin load capacitance", required=True)
	args = parser.parse_args(argv)

	if len(args.tslew) == 1 and len(args.cload) == 1:
		input = potstill.pwrout.Pwrout(macro, args.tslew[0], args.cload[0])
		run = potstill.pwrout.PwroutRun(input)
		return (args, input, run)
	else:
		run = potstill.pwrout.PwroutSweepRun(macro, args.tslew, args.cload)
		return (args, None, run)


def mainCharTrdwr(macro, parentParser, argv):
	parser = argparse.ArgumentParser(
		description="Perform read and write time characterization.",
		prog="trdwr",
		parents=[parentParser],
		add_help=False)
	parser.add_argument("--tslew", metavar="TSLEW", type=float, nargs="+", help="transition time of the input signals", required=True)
	parser.add_argument("--cload", metavar="CLOAD", type=float, nargs="+", help="output pin load capacitance", required=True)
	args = parser.parse_args(argv)

	if len(args.tslew) == 1 and len(args.cload) == 1:
		input = potstill.trdwr.Trdwr(macro, args.tslew[0], args.cload[0])
		run = potstill.trdwr.TrdwrRun(input)
		return (args, input, run)
	else:
		run = potstill.trdwr.TrdwrSweepRun(macro, args.tslew, args.cload)
		return (args, None, run)


def printUsage():
	sys.stderr.write("usage: potstill -h\n")
	sys.stderr.write("   or: potstill netlist COMPONENT SIZE\n")
	sys.stderr.write("   or: potstill nodeset PREFIX NADDR NBITS\n")
	sys.stderr.write("   or: potstill layout ADDRWIDTH DATAWIDTH OUTFILE\n")

def printCharUsage():
	sys.stderr.write("usage: potstill char -h\n")
	sys.stderr.write("   or: potstill char AW DW COMMAND [OPTIONS]\n\n")
	sys.stderr.write("Where the most common commands are:\n")
	sys.stderr.write("   pwrck\n")
	sys.stderr.write("   pwrintcap\n")
	sys.stderr.write("   pwrout\n")
	sys.stderr.write("   trdwr\n")
	sys.stderr.write("   tsuho\n")

def main(argv):
	if len(argv) == 0 or argv[0] == "-h" or argv[0] == "--help":
		printUsage()
		sys.exit(1)
	mainName = "main" + argv[0].capitalize()
	if mainName not in globals():
		sys.stderr.write("Unknown command \"%s\"\n" % argv[0])
		printUsage()
		sys.exit(1)
	else:
		globals()[mainName](argv[1:])

if __name__ == "__main__":
	main(sys.argv[1:])
