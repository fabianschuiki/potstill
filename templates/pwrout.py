#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
# This script generates a SPECTRE input file to perform internal power analysis
# on the output pins of an SCM, and a corresponding OCEAN script to evaluate the
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
Cload = 10e-21

scs = open("%s.scs" % outname, "w")
ocn = open("%s.ocn" % outname, "w")

scs.write("// %s\n" % BASE)
scs.write("include \"%s/sim/preamble.scs\"\n" % BASE)
scs.write("include \"%s.cir\"\n" % cname)

ocn.write("openResults(\"./pwrout.psf\")\n")
ocn.write("selectResult('tran)\n")
ocn.write("p = outfile(\"pwrout.csv\", \"w\")\n")

pins_RA = ["RA%d" % i for i in range(num_addr)]
pins_RD = ["RD%d" % i for i in range(num_bits)]
pins_WA = ["WA%d" % i for i in range(num_addr)]
pins_WD = ["WD%d" % i for i in range(num_bits)]

scs.write("X (CK RE %s %s WE %s %s VDD 0) %s\n" % (
	" ".join(["RA" for i in range(num_addr)]),
	" ".join(["RD%d" % i for i in range(num_bits)]),
	" ".join(["VDD" for i in range(num_addr)]),
	" ".join(["VDD" for i in range(num_bits)]),
	cname
))
for i in range(num_bits):
	scs.write("C%d (RD%d 0) capacitor c=cload\n" % (i, i))

scs.write("parameters tslew=30p cload=%g\n" % Cload)
scs.write("VDD (VDD 0) vsource type=dc dc=%g\n" % VDD)
scs.write("VCK (CK, 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew period=%gn rise=tslew fall=tslew\n" % (VDD, 1*T, 1*T, 3*T))
scs.write("VWE (WE, 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew rise=tslew fall=tslew\n" % (VDD, 3*T, 3*T))
scs.write("VRE (RE, 0) vsource type=pulse val0=%g val1=0 delay=%gn width=%gn-tslew rise=tslew fall=tslew\n" % (VDD, 3*T, 3*T))
scs.write("VRA (RA, 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew rise=tslew fall=tslew\n" % (VDD, 6*T, 3*T))

# Calculate the energy consumed by the clock, which needs to be subtracted from
# the energy consumed by the circuit during a change in output.
ocn.write("E_CK = integ(-IT(\"VDD:p\") %gn %gn) * %g\n" % (1*T, 3*T, VDD))
ocn.write("printf(\"E_CK = %g\\n\", E_CK)\n")

# For each RD output pin, calculate the energy consumed by the circuit and
# subtract the energy due to the two clock edges and the energy that was
# deposited in the capacitor.
ocn.write("E_RD_rise = integ(-IT(\"VDD:p\") %gn %gn) * %g - E_CK - %g\n" % (7*T, 9*T, VDD, num_bits*0.5*Cload*(VDD**2)))
ocn.write("E_RD_fall = integ(-IT(\"VDD:p\") %gn %gn) * %g - E_CK\n" % (10*T, 12*T, VDD))

for i in range(num_bits):
	ocn.write("fprintf(p, \"E_RD%d_rise,%%g\\n\", E_RD_rise/%d)\n" % (i, num_bits))
	ocn.write("fprintf(p, \"E_RD%d_fall,%%g\\n\", E_RD_fall/%d)\n" % (i, num_bits))

# Specify the simulation to perform.
scs.write("tran tran stop=%gn errpreset=conservative write=\"spectre.ic\" readns=\"%s.ns\"\n" % (12*T, cname))

# Specify what to save.
scs.write("save VDD:p\n")
# scs.write("save CK RE WE\n")
# scs.write("save RD* depth=1\n")
# scs.write("save X:currents\n")

ocn.write("close(p)\n")

scs.close()
ocn.close()
