#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki

import sys, os
import math
import argparse
import yaml
import subprocess
sys.path.insert(0, sys.path[0]+"/..")
import potstill.macro
import potstill.pwrck
import potstill.pwrintcap
import potstill.pwrout
import potstill.trdwr
import potstill.tsuho
from potstill import nodeset
from potstill import netlist

BASE = sys.path[0]+"/.."


def generateLayout(size, bits, outfile):

	# Read the configuration file for the technology.
	with open("%s/umc65/config.yml" % BASE, "r") as stream:
		config = yaml.load(stream)
	# print(config)

	cmds = list()

	# Load the input GDS data.
	for s in config["import"]["gds"]:
		cmds.append("load_gds \"%s/umc65/%s\";" % (BASE, s))

	num_bits_left   = int(bits/2)
	num_bits_right  = bits - num_bits_left
	num_addrs_left  = int(size/2)
	num_addrs_right = size - num_addrs_left

	G = config["track"]
	row_height = config["row-height"]*G
	bitarray_cell = "PSBT%d" % (2**size)

	bit_width = config["widths"]["bitarray"]*G
	rwckg_width = config["widths"]["rwckg"]*G
	addrdec_width = config["widths"]["addrdec"][2**size]*G
	rareg_width = config["widths"]["rareg"]*G

	# Assemble the root cell.
	x = 0
	cmds.append("cell \"PS%dX%d\" {" % (2**size, bits))
	cmds.append("set_size %g %g;" % (bits*bit_width+addrdec_width, (2**size + 1)*row_height))
	for i in range(num_bits_left):
		cmds.append("inst %s \"XBA%d\" {" % (bitarray_cell, i))
		cmds.append("set_orientation MX;")
		cmds.append("set_position %g 0;" % (x+bit_width))
		cmds.append("}")
		x += bit_width

	xral = x
	cmds.append("inst PSAD%d \"XAD\" {" % (2**size))
	cmds.append("set_position %g 0;" % x)
	cmds.append("}")
	x += addrdec_width
	xrar = x

	rwckg_x = x-rwckg_width
	rwckg_y = (2**size)*row_height
	cmds.append("inst PSRWCKG \"XRWCKG\" {")
	cmds.append("set_position %g %g;" % (rwckg_x, rwckg_y))
	cmds.append("}")

	for i in range(num_bits_right):
		cmds.append("inst %s \"XBA%d\" {" % (bitarray_cell, i+num_bits_left))
		cmds.append("set_position %g 0;" % x)
		cmds.append("}")
		x += bit_width

	x = xral - (num_addrs_left-1)*rareg_width
	for i in range(num_addrs_left):
		cmds.append("inst PSREGRA \"XRA%d\" {" % i)
		cmds.append("set_orientation R180;")
		cmds.append("set_position %g %g;" % (x, (2**size+2)*row_height))
		cmds.append("}")
		x += rareg_width

	x = xrar
	for i in range(num_addrs_right):
		cmds.append("inst PSREGRA \"XRA%d\" {" % (num_addrs_left+i))
		cmds.append("set_orientation MY;")
		cmds.append("set_position %g %g;" % (x, (2**size+2)*row_height))
		cmds.append("}")
		x += rareg_width

	# Add the power pins.
	pwr_pin_layer = int(config["pins"]["power"]["layer"])
	for i in range(0, 2**size+3, 2):
		cmds.append("add_gds_text %d %d %g %g VSS;" % (pwr_pin_layer, 0, xral+1*G, i*row_height))
	for i in range(1, 2**size+2, 2):
		cmds.append("add_gds_text %d %d %g %g VDD;" % (pwr_pin_layer, 0, xral+1*G, i*row_height))

	# Add the write address pins.
	addr_pin_layer = int(config["pins"]["addrdec"]["layer"])
	addr_vtracks = [int(x) for x in config["pins"]["addrdec"]["vtracks"][2**size]]
	N = 0
	for x in addr_vtracks:
		cmds.append("add_gds_text %d %d %g %g WA%d;" % (
			addr_pin_layer, 0,
			xral + (x+0.5)*G, (2**size)*row_height,
			N
		))
		N += 1

	# Add the global clock gate pins.
	rwckg_pins = config["pins"]["rwckg"]
	for (name,pin) in rwckg_pins.items():
		cmds.append("add_gds_text %d %d %g %g %s;" % (
			int(pin[2]), 0,
			rwckg_x + (int(pin[0])+0.5)*G, rwckg_y + int(pin[1])*G,
			name
		))

	# Add the bit array pins.
	bitarray_pins = config["pins"]["bitarray"]
	for (name,pin) in bitarray_pins.items():
		for i in range(num_bits_left):
			cmds.append("add_gds_text %d %d %g %g %s%d;" % (
				int(pin[2]), 0,
				(i+1)*bit_width - (int(pin[0])+0.5)*G, (2**size)*row_height + int(pin[1])*G,
				name, i
			))
		for i in range(num_bits_right):
			cmds.append("add_gds_text %d %d %g %g %s%d;" % (
				int(pin[2]), 0,
				xrar+i*bit_width + (int(pin[0])+0.5)*G, (2**size)*row_height + int(pin[1])*G,
				name, i + num_bits_left
			))

	cmds.append("}")

	# Create some GDS output from the cells generated above.
	cmds.append("gds \"PS%dX%d\" {" % (2**size, bits))
	# cmds.append("copy_cell_gds \"%s\";" % bitarray_cell)
	# cmds.append("copy_cell_gds \"PSAD%d\";" % (2**size))
	# for i in range(size):
	# 	cmds.append("copy_cell_gds \"PSBA%d\";" % (2**i))
	# for s in ["PSRMND", "PSRMNR"]:
	# 	cmds.append("copy_cell_gds \"%s\";" % s)
	cmds.append("make_gds_for_cell \"PS%dX%d\";" % (2**size, bits))
	cmds.append("write_gds \"%s\";" % outfile)
	cmds.append("}")

	print("\n".join(cmds))

	# Start phalanx and execute the commands.
	with subprocess.Popen(["phalanx"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as proc:
		(proc_out, proc_err) = proc.communicate(input="\n".join(cmds))
		sys.stderr.write(proc_err)
		if proc.returncode != 0:
			sys.stderr.write("Phalanx failed to generate GDS data.\n")
			sys.exit(1)


def mainNetlist(argv):
	if len(argv) < 2 or argv[0] == "-h" or argv[0] == "--help":
		printUsage()
		sys.exit(1)
	if argv[0].upper() == "TOP":
		if len(argv) < 3:
			sys.stderr.write("Top-level cell requires number of address lines and number of bits.\n")
			printUsage()
			sys.exit(1)
		print(netlist.generate(int(argv[1]), int(argv[2])))
	else:
		funcName = "generate" + argv[0].upper()
		if not hasattr(netlist, funcName):
			sys.stderr.write("Unknown component \"%s\"\n" % argv[0])
			printUsage()
			sys.exit(1)
		print(getattr(netlist, funcName)(int(argv[1])))


def mainNodeset(argv):
	if len(argv) < 3:
		printUsage()
		sys.exit(1)
	sys.stdout.write(nodeset.generate(argv[0], int(argv[1]), int(argv[2])))


def mainLayout(argv):
	if len(argv) < 3 or argv[0] == "-h" or argv[0] == "--help":
		printUsage()
		sys.exit(1)
	generateLayout(int(argv[0]), int(argv[1]), argv[2])


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


def mainCharPwrck(macro, parentParser, argv):
	parser = argparse.ArgumentParser(description="Perform internal power characterization for the clock.", prog="pwrck", parents=[parentParser], add_help=False)
	parser.add_argument("tslew", metavar="TSLEW", type=float, nargs="+", help="transition time of the clock input signal")
	args = parser.parse_args(argv)

	if len(args.tslew) == 1:
		input = potstill.pwrck.Pwrck(macro, args.tslew[0])
		run = potstill.pwrck.PwrckRun(input)
		return (args, input, run)
	else:
		run = potstill.pwrck.PwrckSweepRun(macro, args.tslew)
		return (args, None, run)


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


def mainCharTsuho(macro, parentParser, argv):
	parser = argparse.ArgumentParser(description="Perform setup and hold time characterization.", prog="tsuho", parents=[parentParser], add_help=False)
	parser.add_argument("--tslewck", metavar="TSLEWCK", type=float, nargs="+", help="transition time of the clock signal", required=True)
	parser.add_argument("--tslewpin", metavar="TSLEWPIN", type=float, nargs="+", help="transition time of the input signal", required=True)
	parser.add_argument("--setup", action="store_true", help="only perform setup time analysis")
	parser.add_argument("--hold", action="store_true", help="only perform hold time analysis")
	args = parser.parse_args(argv)

	if len(args.tslewck) == 1 and len(args.tslewpin) == 1:
		tsu_input = potstill.tsuho.Tsu(macro, args.tslewck[0], args.tslewpin[0])
		tho_input = potstill.tsuho.Tho(macro, tsu_input.oceanOutputName, args.tslewck[0], args.tslewpin[0])

		run = potstill.tsuho.TsuhoCombinedRun(tsu_input, tho_input)
		if args.setup:
			return (args, tsu_input, run.su_run)
		if args.hold:
			return (args, tho_input, run.ho_run)
		return (args, None, run)
	else:
		run = potstill.tsuho.TsuhoSweepRun(macro, args.tslewck, args.tslewpin)
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
