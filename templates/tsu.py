#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
# This script generates a SPECTRE input file to perform setup time analysis on
# the input pins of an SCM, and a corresponding OCEAN script to evaluate the
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

Tfrom = -150e-12
Tto = 150e-12
Ncycles = 100

Tinit = Tfrom
Tdr = (Tto-Tfrom)/(Ncycles-1)

scs = open("%s.scs" % outname, "w")
ocn = open("%s.ocn" % outname, "w")

scs.write("// %s\n" % BASE)
scs.write("include \"%s/sim/preamble.scs\"\n" % BASE)
scs.write("include \"%s.cir\"\n" % cname)

ocn.write("openResults(\"./tsu.psf\")\n")
ocn.write("selectResult('tran)\n")
ocn.write("p = outfile(\"tsu.csv\", \"w\")\n")

scs.write("X (CK B %s %s B %s %s VDD 0) %s\n" % (
	" ".join(["A" for i in range(num_addr)]),
	" ".join(["RD%d" % i for i in range(num_bits)]),
	" ".join(["A" for i in range(num_addr)]),
	" ".join(["A" for i in range(num_bits)]),
	cname
))

scs.write("parameters tsc=230p tsd=230p tinit=%g tdr=%g\n" % (Tinit, Tdr))
scs.write("VDD (VDD 0) vsource type=dc dc=%g\n" % VDD)

Tstart = 1
Tcycle = 16

# Generate two overlaid clock signals. The first clock impulse has a high rise
# time tsc. This is the critical edge for which setup time is measured. The
# second clock edge serves as a "safe" edge during which the content of the
# sequential cells is set to a known state in case of a setup violation.
scs.write("VCK0 (nCK1 0) vsource type=pulse val0=0 val1=%g delay=%gn width=%gn period=%gn\n" % (VDD, (Tstart+2)*T, 1*T, 4*T))
scs.write("VCK1 (CK nCK1) vsource type=pulse val0=0 val1=%g delay=%gn-0.5*tsc width=%gn-0.5*tsc period=%gn rise=tsc fall=10p\n" % (VDD, Tstart*T, 1*T, 4*T))

# Generate the input signal for the RA and WD pins.
scs.write("VA0 (A 0) vsource type=pulse val0=0 val1=%g delay=%gn-0.5*tsd+tinit width=%gn-tsd period=%gn+tdr rise=tsd fall=tsd\n" % (VDD, (Tstart+4)*T, 4*T, 16*T))

# Generate the input signal for the RE and WE pins, which need to be high during
# the testing of the other pins.
scs.write("VB0 (B 0) vsource type=pulse val0=0 val1=%g delay=%gn-0.5*tsd+tinit width=%gn-tsd period=%gn+tdr rise=tsd fall=tsd\n" % (VDD, Tstart*T, 12*T, 16*T))

# Specify the simulation to perform.
scs.write("tran tran stop=%gn readns=\"%s.ns\"\n" % ((Tstart+Ncycles*16)*T, cname))

# The following are the probing points to determine the propagation delay for
# the various inputs.
prb_RE = "X.XRWCKG.X0.n1"
prb_RA = "X.nRA0"
prb_WE = "X.XRWCKG.X1.n1"
prb_WA = "X.XAD.XCKG0.n1"
prb_WD = "X.nWD0"

# Specify what to save.
scs.write("save CK A B\n")
scs.write("save %s %s %s %s %s\n" % (prb_RE, prb_RA, prb_WE, prb_WA, prb_WD))
# scs.write("save RD* depth=1\n")
# scs.write("save X:currents\n")

# In the OCEAN script, calculate the rising and falling edges of the measured
# points such that the propagation delays can be calculated later.
for s in [("RE", prb_RE, True), ("WE", prb_WE, True), ("RA", prb_RA, False), ("WA", prb_WA, False), ("WD", prb_WD, False), ("A", "A", False), ("B", "B", False)]:
	ocn.write("X_%s_rise = cross(VT(\"%s\") %g 1 \"%s\" t \"cycle\")\n" % (s[0], s[1], VDD/2, "falling" if s[2] else "rising"))
	ocn.write("X_%s_fall = cross(VT(\"%s\") %g 1 \"%s\" t \"cycle\")\n" % (s[0], s[1], VDD/2, "rising" if s[2] else "falling"))

# For the level-triggered sequential elements, calculate the propagation delay
# as the time between the related signal's crossing and the probe's crossing.
for s in [("WA", "A"), ("RE", "B"), ("WE", "B")]:
	ocn.write("Tpd_%s_rise = (X_%s_rise - X_%s_rise)\n" % (s[0], s[0], s[1]))
	ocn.write("Tpd_%s_fall = (X_%s_fall - X_%s_fall)\n" % (s[0], s[0], s[1]))

# For the edge triggered sequential elements.
for s in [("RA", 4*T, 8*T), ("WD", 4*T, 8*T)]:
	ocn.write("Tpd_%s_rise = (X_%s_rise - int(X_%s_rise / %gn) * %gn - %gn)\n" % (s[0], s[0], s[0], Tcycle*T, Tcycle*T, s[1]+Tstart*T))
	ocn.write("Tpd_%s_fall = (X_%s_fall - int(X_%s_rise / %gn) * %gn - %gn)\n" % (s[0], s[0], s[0], Tcycle*T, Tcycle*T, s[2]+Tstart*T))

# Calculate the threshold values for the propagation delay which if crossed mark
# a setup violation.
for s in ["RE", "RA", "WE", "WA", "WD"]:
	for e in ["rise", "fall"]:
		ocn.write("Tpdth_%s_%s = value(Tpd_%s_%s 1) * %f\n" % (s, e, s, e, 1.05))

# Calculate the number of cycles after which the propagation delays cross the
# corresponding threshold value.
for s in ["RE", "RA", "WE", "WA", "WD"]:
	for e in ["rise", "fall"]:
		# Be careful to subtract 1, since the cycle count starts at 1. However,
		# the first cycle represents tsu=tinit, not tsu=tinit+tdr.
		ocn.write("Nc_%s_%s = int(cross(Tpd_%s_%s Tpdth_%s_%s 1 \"rising\")) - 1\n" % (s, e, s, e, s, e))
		ocn.write("fprintf(p, \"Tsu_%s_%s,%%g\\n\", %g - Nc_%s_%s * %g)\n" % (s, e, -Tinit, s, e, Tdr))

ocn.write("close(p)\n")

scs.close()
ocn.close()
