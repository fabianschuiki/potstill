# Copyright (c) 2016 Fabian Schuiki

def generateADCKG(prefix, value):
	return prefix+".X1.n1 %g\n" % value


def generateAD(prefix, num_addr):
	res = ""
	for i in range(2**num_addr):
		res += generateADCKG(prefix+".XCKG%d" % i, 0)
	return res


def generateREGLA(prefix, value):
	return prefix+".n1 %g\n" % value


def generateREG(prefix, value):
	return generateREGLA(prefix+".XI0", value) + generateREGLA(prefix+".XI1", 1.2-value)


def generateBA1(prefix, value):
	return prefix+".nFB %g\n" % (1.2-value)


def generateBT(prefix, num_addr, value):
	res = ""
	for i in range(2**num_addr):
		res += generateBA1(prefix+".X%d" % i, value)
	return res


def generate(prefix, num_addr, num_bits):
	res = ""

	# Global clock gate.
	res += generateADCKG(prefix+".XRWCKG.X0", 0)
	res += generateADCKG(prefix+".XRWCKG.X1", 0)

	# Address decoder.
	res += generateAD(prefix+".XAD", num_addr)

	# Write data and read address registers.
	for i in range(num_addr):
		res += generateREG(prefix+".XRAREG%d" % i, 0)
	for i in range(num_bits):
		res += generateREG(prefix+".XWDREG%d" % i, 0)

	# Memory columns.
	for i in range(num_bits):
		res += generateBT(prefix+".XBA%d" % i, num_addr, 0)

	return res


def generateMacro(prefix, macro):
	return generate(prefix, macro.num_addr, macro.num_bits)
