# Copyright (c) 2016 Fabian Schuiki
import os

BASE = os.path.dirname(__file__)+"/.."

def generate(size, bits):
	lines = list()
	lines.append(".SUBCKT PS%dX%d CK RE %s %s WE %s %s VDD VSS" % (
		2**size, bits,
		" ".join(["RA%d" % i for i in reversed(range(size))]),
		" ".join(["RD%d" % i for i in reversed(range(bits))]),
		" ".join(["WA%d" % i for i in reversed(range(size))]),
		" ".join(["WD%d" % i for i in reversed(range(bits))]),
	))

	netsRA = " ".join(["nRA%d" % i for i in range(size)])
	netsWA = " ".join(["WA%d" % i for i in range(size)])
	netsSGPGN = " ".join(["nS%d nGP%d nGN%d" % (i,i,i) for i in range(2**size)])

	# Add the root clock gates.
	lines.append("XRWCKG RE WE CK nRCKP nRCKN nWCKP nWCKN VDD VSS PSRWCKG")

	# Instantiate the address decoder.
	lines.append("XAD nWCKP nWCKN %s %s %s VDD VSS PSAD%d" % (
		netsRA, netsWA, netsSGPGN, 2**size
	))

	# Instantiate the write data registers.
	for i in range(bits):
		lines.append("XWDREG%d WD%d nWCKP nWCKN nWD%d iw%d VDD VSS PSREG" % (
			i, i, i, i
		))

	# Instantiate the read address registers.
	for i in range(size):
		lines.append("XRAREG%d RA%d nRCKP nRCKN nRA%d ir%d VDD VSS PSREG" % (
			i, i, i, i
		))

	# Instantiate the bit arrays.
	for i in range(bits):
		lines.append("XBA%d nWD%d %s RD%d VDD VSS PSBA%d" % (
			i, i, netsSGPGN, i, 2**size
		))

	lines.append(".ENDS")

	with open("%s/umc65/netlists/components.cir" % BASE, "r") as f:
		netlistPrefix = f.read()

	return "\n\n".join([
		netlistPrefix,
		generateAD(size),
		generateBA(size),
		"\n".join(lines)+"\n"
	])


# Generate the netlist for a bit array.
def generateBA(size):
	lines = list()
	lines.append(".SUBCKT PSBA%d D %s Q VDD VSS" % (
		2**size,
		" ".join(["S%d GP%d GN%d" % (i,i,i) for i in range(2**size)])
	))
	for i in range(2**size):
		lines.append("X%d D GP%d GN%d S%d nL0Q%d VDD VSS PSBA1" % (
			i, i, i, i, i
		))
	if size % 2 == 0:
		outName = "nQ"
		lines.append("XINV nQ Q VDD VSS PSRMINV")
	else:
		outName = "nQ"
		lines.append("XBUF nQ Q VDD VSS PSRMBUF")
	for i in range(size):
		for n in range(2**(size-i-1)):
			lines.append("XL%dQ%d nL%dQ%d nL%dQ%d %s VDD VSS %s" % (
				i+1, n,
				i, n*2+0,
				i, n*2+1,
				("nL%dQ%d" % (i+1, n)) if i < size-1 else outName,
				"PSRMND" if i % 2 == 0 else "PSRMNR"
			))
	lines.append(".ENDS")
	return "\n".join(lines)


# Generate the netlist for an address decoder.
def generateAD(size):
	lines = list()
	lines.append(".SUBCKT PSAD%d CKP CKN %s %s %s VDD VSS" % (2**size,
		" ".join(["RA%d" % i for i in range(size)]),
		" ".join(["WA%d" % i for i in range(size)]),
		" ".join(["S%d GP%d GN%d" % (i,i,i) for i in range(2**size)])
	))

	# Instantiate the clock gates that generate the WWL.
	for i in range(2**size):
		lines.append("XCKG%d nWE%d CKP CKN GP%d GN%d VDD VSS PSADCKG " % (
			i, i, i, i,
		))

	# Instantiate the one-hot decoder for the read and write address.
	lines.append("XRAD %s %s VDD VSS PSADOH%d" % (
		" ".join(["RA%d" % i for i in range(size)]),
		" ".join(["S%d"  % i for i in range(2**size)]),
		2**size
	))
	lines.append("XWAD %s %s VDD VSS PSADOH%d" % (
		" ".join(["WA%d"  % i for i in range(size)]),
		" ".join(["nWE%d" % i for i in range(2**size)]),
		2**size
	))

	lines.append(".ENDS")
	return generateADOH(size) + "\n\n" + "\n".join(lines)


# Generate the netlist for the one-hot decoder used in address decoders.
def generateADOH(size):
	lines = list()
	with open(BASE+"/umc65/netlists/PSADOH.cir") as f:
		lines.append(f.read())

	lines.append(".SUBCKT PSADOH%d %s %s VDD VSS" % (2**size,
		" ".join(["A%d" % i for i in range(size)]),
		" ".join(["Z%d" % i for i in range(2**size)])
	))
	N = 0
	for i in range(size):
		lines.append("XI%d A%d N%d VDD VSS PSADINV" % (N, i, i))
		N += 1
	N = 0
	actHiInputs = (size > 3)
	flipped_lines = set()
	for i in range(2**size):
		lines.append("X%d %s Z%d VDD VSS PSADOH%dR" % (N,
			" ".join([("A%d" if (i if actHiInputs and n != 6 else ~i) & (1 << n) else "N%d") % n for n in range(size)]),
			i,
			2**size
		))
		N += 1
	lines.append(".ENDS")
	return "\n".join(lines)

# class Netlist(object):
# 	def __init__(self):
# 		super(Netlist, self).__init__()
# 		self.circuits = dict()

# 	def make(name, *args,):
# 		if name is in self.circuits:
# 			return self.circuits[name]
# 		else:
# 			funcName = "generateNetlistFor"
# 			subckt = globals()

# class NetlistSubcircuit(object):
# 	def __init__(self):
# 		super(NetlistSubcircuit, self).__init__()


def generateMacro(macro):
	return generate(macro.num_addr, macro.num_bits)


# class AdohNetlist(object):
# 	def __init__(self):
# 		super(AdohNetlist, self).__init__()

# 		lines = list()
# 		with open("%s/umc65/netlists/PSADOH%dR.cir" % (BASE, 2**size), "r") as f:
# 			lines.append(f.read())

# 		lines.append(".SUBCKT PSADOH%d %s %s VDD VSS" % (2**size,
# 			" ".join(["A%d" % i for i in range(size)]),
# 			" ".join(["Z%d" % i for i in range(2**size)])
# 		))
# 		N = 0
# 		for i in range(size):
# 			lines.append("XI%d A%d N%d VDD VSS PSADINV" % (N, i, i))
# 			N += 1
# 		N = 0
# 		actHiInputs = (size > 3)
# 		for i in range(2**size):
# 			lines.append("X%d %s Z%d VDD VSS PSADOH%dR" % (N,
# 				" ".join([("A%d" if (i if actHiInputs else ~i) & (1 << n) else "N%d") % n for n in range(size)]),
# 				i,
# 				2**size
# 			))
# 			N += 1
# 		lines.append(".ENDS")
# 		return "\n".join(lines)
