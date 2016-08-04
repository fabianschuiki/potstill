#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki

import sys, os
BASE = sys.path[0]+"/.."

if len(sys.argv) != 3:
	sys.stderr.write("usage: %s NADDR NBITS\n" % sys.argv[0])
	sys.exit(1)

num_addr = int(sys.argv[1])
num_bits = int(sys.argv[2])
cname = "PS%dX%d" % (2**num_addr, num_bits)
VDD = 1.2
T = 1
Cload = 10e-15

print("// %s" % BASE)
print("include \"%s/sim/preamble.scs\"" % BASE)
print("include \"%s.cir\"" % cname)

print("X (CK RE %s %s WE %s %s VDD 0) %s" % (
	" ".join(["VDD" for i in range(num_addr)]),
	" ".join(["RD%d" % i for i in range(num_bits)]),
	" ".join(["VDD" for i in range(num_addr)]),
	" ".join(["VDD" for i in range(num_bits)]),
	cname
))
for i in range(num_bits):
	print("C%d (RD%d 0) capacitor c=cload\n" % (i, i))

print("parameters tslew=30p cload=%g\n" % Cload)
print("VDD (VDD 0) vsource type=dc dc=%g" % VDD)
print("VCK (CK 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew period=%gn rise=tslew fall=tslew" % (VDD, 1*T, 1*T, 3*T))
print("VWE (WE 0) vsource type=pulse val0=%g val1=0 delay=%gn rise=tslew fall=tslew" % (VDD, 3*T))
print("VRE (RE 0) vsource type=pulse val0=0 val1=%g delay=%gn rise=tslew fall=tslew" % (VDD, 3*T))

print("tran tran stop=%gn errpreset=conservative readns=\"%s.ns\"" % (6*T, cname))

# Save CK, RD, and the internal memory latch outputs such that we can analyze the delays.
print("save CK RE WE")
print("save RD* depth=1")
print("save X.XBA*.X%d.nZ" % (2**num_addr-1))
