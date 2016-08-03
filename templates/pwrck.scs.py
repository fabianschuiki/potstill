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
T = 5

print("// %s" % cname)
print("include \"%s/sim/preamble.scs\"" % BASE)
print("include \"%s.cir\"" % cname)

print("X (CK RE %s %s WE %s %s VDD 0) %s" % (
	" ".join(["RA%d" % i for i in range(num_addr)]),
	" ".join(["RD%d" % i for i in range(num_bits)]),
	" ".join(["WA%d" % i for i in range(num_addr)]),
	" ".join(["WD%d" % i for i in range(num_bits)]),
	cname
))

print("parameters tslew=30p")
print("VDD (VDD 0) vsource type=dc dc=%g" % VDD)
print("VCK (CK 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew period=%gn rise=tslew fall=tslew" % (VDD, T, T, 3*T))

Tswp = (2**num_addr) * 3
Ts_rd = 3
Ts_wr = Ts_rd + Tswp
Ts_rw = Ts_wr + Tswp
Ts_done = Ts_rw + Tswp

print("VRE (RE 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew period=%gn rise=tslew fall=tslew" % (
	VDD, Ts_rd*T, Tswp*T, 2*Tswp*T
))
print("VWE (WE 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew rise=tslew fall=tslew" % (
	VDD, Ts_wr*T, 2*Tswp*T
))

for i in range(num_addr):
	print("VWA%d (WA%d 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn-tslew period=%gn rise=tslew fall=tslew" % (
		i, i, VDD,
		(Ts_rd + (2**i)*3)*T,
		(2**i*3)*T,
		(2**i*6)*T
	))

for i in range(num_addr):
	print("VRA%d (RA%d 0) vsource type=dc dc=0" % (i,i))
for i in range(num_bits):
	print("VWD%d (WD%d 0) vsource type=dc dc=0" % (i,i))

# Specify the transient analysis to perform.
print("tran tran stop=%gn errpreset=liberal readns=\"%s.ns\"" % ((Ts_done+1)*T, cname))

# Specify what to save.
print("save VDD:p")
print("save CK RE WE")
print("save RA* depth=1")
print("save RD* depth=1")
print("save WA* depth=1")
print("save WD* depth=1")
