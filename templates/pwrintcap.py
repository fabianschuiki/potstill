#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
# This script generates a SPECTRE input file to perform internal power analysis
# on the input pins of an SCM, and a corresponding OCEAN script to evaluate the
# results and dump them into a CSV file.

import sys, os
BASE = sys.path[0]+"/.."

if len(sys.argv) != 4:
	sys.stderr.write("usage: %s NADDR NBITS OUTNAME\n" % sys.argv[0])
	sys.exit(1)

num_addr = int(sys.argv[1])
num_bits = int(sys.argv[2])
outname = sys.argv[3]
cname = "PS%dX%d" % (2**num_addr, num_bits)
VDD = 1.2
T = 1

scs = open("%s.scs" % outname, "w")
ocn = open("%s.ocn" % outname, "w")

scs.write("// %s\n" % BASE)
scs.write("include \"%s/sim/preamble.scs\"\n" % BASE)
scs.write("include \"%s.cir\"\n" % cname)

ocn.write("openResults(\"./pwrintcap.psf\")\n")
ocn.write("selectResult('tran)\n")
ocn.write("p = outfile(\"pwrintcap.csv\", \"w\")\n")

pins_RA = ["RA%d" % i for i in range(num_addr)]
pins_RD = ["RD%d" % i for i in range(num_bits)]
pins_WA = ["WA%d" % i for i in range(num_addr)]
pins_WD = ["WD%d" % i for i in range(num_bits)]

terminals = ["CK","RE"]+pins_RA+pins_RD+["WE"]+pins_WA+pins_WD
terminalIndices = dict()
for idx, name in enumerate(terminals):
	terminalIndices[name] = idx + 1

scs.write("X (%s VDD 0) %s\n" % (
	" ".join(terminals),
	cname
))

scs.write("parameters tslew=30p\n")
scs.write("VDD (VDD 0) vsource type=dc dc=%g\n" % VDD)

all_pins = (["CK", "RE", "WE"]+pins_RA+pins_WA+pins_WD)
x = 1
i = 0
for p in all_pins:
	scs.write("V%d (%s 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew rise=tslew fall=tslew\n" % (
		i, p, VDD, x*T, 1*T
	))
	ocn.write("printf(\"Characterizing pin %s\\n\")\n" % p)
	if p != "CK":
		ocn.write("fprintf(p, \"E_%s_rise,%%g\\n\", integ(-IT(\"VDD:p\") %gn %gn) * %g)\n" % (p, x*T, (x+1)*T, VDD))
		ocn.write("fprintf(p, \"E_%s_fall,%%g\\n\", integ(-IT(\"VDD:p\") %gn %gn) * %g)\n" % (p, (x+1)*T, (x+2)*T, VDD))
	ocn.write("fprintf(p, \"C_%s,%%g\\n\", integ(abs(IT(\"X:%d\")) %gn %gn) / %g)\n" % (p, terminalIndices[p], x*T, (x+2)*T, VDD))
	x += 2
	i += 1

scs.write("tran tran stop=%gn errpreset=conservative readns=\"%s.ns\"\n" % (x*T, cname))

# Specify what to save.
scs.write("save VDD:p\n")
scs.write("save CK RE WE\n")
scs.write("save RA* depth=1\n")
scs.write("save WA* depth=1\n")
scs.write("save WD* depth=1\n")
scs.write("save %s\n" % (" ".join(["X:"+s for s in all_pins])))

ocn.write("close(p)\n")

scs.close()
ocn.close()
