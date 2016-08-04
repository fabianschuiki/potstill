#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki
# This script generates a SPECTRE input file to perform hold time analysis on
# the input pins of an SCM, and a corresponding OCEAN script to evaluate the
# results and dump them into a CSV file.

import sys, os, csv
BASE = sys.path[0]+"/.."

if len(sys.argv) != 5:
	sys.stderr.write("usage: %s NADDR NBITS SETUPCSV OUTNAME\n" % sys.argv[0])
	sys.exit(1)

num_addr = int(sys.argv[1])
num_bits = int(sys.argv[2])
setupcsv = sys.argv[3]
outname = sys.argv[4]
cname = "PS%dX%d" % (2**num_addr, num_bits)
VDD = 1.2
T = 1e-9

# Read the CSV file containing the setup times.
with open(setupcsv, "r") as f:
	rd = csv.reader(f)
	setupTimes = dict([(a[0], float(a[1])) for a in rd])

Tfrom = 400e-12
Tto = -100e-12
Ncycles = 100

Tinit = Tfrom
Tdr = (Tto-Tfrom)/(Ncycles-1)

scs = open("%s.scs" % outname, "w")
ocn = open("%s.ocn" % outname, "w")

scs.write("// %s\n" % BASE)
scs.write("include \"%s/sim/preamble.scs\"\n" % BASE)
scs.write("include \"%s.cir\"\n" % cname)

ocn.write("openResults(\"./tho.psf\")\n")
ocn.write("selectResult('tran)\n")
ocn.write("p = outfile(\"tho.csv\", \"w\")\n")

scs.write("X (CK RE %s %s WE %s %s VDD 0) %s\n" % (
	" ".join(["RA" for i in range(num_addr)]),
	" ".join(["RD%d" % i for i in range(num_bits)]),
	" ".join(["WA" for i in range(num_addr)]),
	" ".join(["WD" for i in range(num_bits)]),
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
scs.write("VCK0 (nCK1 0) vsource type=pulse val0=0 val1=%g delay=%g width=%g period=%g\n" % (VDD, (Tstart+2)*T, 1*T, 4*T))
scs.write("VCK1 (CK nCK1) vsource type=pulse val0=0 val1=%g delay=%g-0.5*tsc width=%g-0.5*tsc period=%g rise=tsc fall=10p\n" % (VDD, Tstart*T, 1*T, 4*T))

def scsStmt(scs, *args, **kwargs):
	scs.write(" ".join(list(args) + ["%s=%s" % (k,v) for k,v in kwargs.items()])+"\n")

# Generate the input signal for the RA, WA, and WD pins.
for p in [("RE", True), ("WE", True), ("RA", False), ("WA", False), ("WD", False)]:
	tps = (Tstart if p[1] else Tstart+4) # Start time of the pulse.
	tpw = (12 if p[1] else 4) # Pulse width.

	tsurise = setupTimes["Tsu_%s_rise" % p[0]]
	tsufall = setupTimes["Tsu_%s_fall" % p[0]]

	# Generate the rising edge with the appropriate rising setup time.
	scs.write("V%s0 (n%s1 0) vsource type=pulse val0=0 val1=%g delay=%g-0.5*tsd-(%g) width=%g-tsd+(%g) period=%g rise=tsd fall=tsd\n" % (
		p[0], p[0], VDD,
		tps*T,
		tsurise,
		tpw*T*0.5,
		tsurise,
		Tcycle*T
	))

	# Generate the falling edge with the appropriate falling setup time.
	scs.write("V%s1 (n%s2 n%s1) vsource type=pulse val0=0 val1=%g delay=%g-0.5*tsd width=%g-tsd-(%g) period=%g rise=tsd fall=tsd\n" % (
		p[0], p[0], p[0], VDD,
		tps*T+tpw*T*0.5,
		tpw*T*0.5,
		tsufall,
		Tcycle*T
	))

	# Generate the falling edge that shifts and triggers a hold violation after
	# the signal has risen.
	scsStmt(scs,
		"V%s2 (n%s3 n%s2) vsource type=pulse" % (p[0], p[0], p[0]),
		"rise=tsd fall=10p",
		"val0=0 val1=-(%g)" % VDD,
		"delay=%g+tinit-0.5*tsd" % (tps*T),
		"width=%g-tinit-0.5*tsd-5p" % T,
		"period=%g+tdr" % (Tcycle*T)
	)

	# Generate the rising edge that shifts and triggers a hold violation after
	# the signal has fallen.
	scsStmt(scs,
		"V%s3 (%s n%s3) vsource type=pulse" % (p[0], p[0], p[0]),
		"rise=tsd fall=10p",
		"val0=0 val1=%g" % VDD,
		"delay=%g+tinit-0.5*tsd" % ((tps+tpw)*T),
		"width=%g-tinit-0.5*tsd-5p" % T,
		"period=%g+tdr" % (Tcycle*T)
	)

# Specify the simulation to perform.
scs.write("tran tran stop=%g readns=\"%s.ns\"\n" % ((Tstart+Ncycles*Tcycle)*T, cname))

# The following are the probing points to determine the propagation delay for
# the various inputs.
prb_RE = "X.XRWCKG.X0.n1"
prb_RA = "X.nRA0"
prb_WE = "X.XRWCKG.X1.n1"
prb_WA = "X.XAD.XCKG0.n1"
prb_WD = "X.nWD0"

# Specify what to save.
scs.write("save CK RE WE WA RA WD\n")
scs.write("save %s %s %s %s %s\n" % (prb_RE, prb_RA, prb_WE, prb_WA, prb_WD))

# In the OCEAN script, calculate the rising and falling edges of the measured
# points such that the propagation delays can be calculated later.
for s in [("RE", prb_RE, True), ("WE", prb_WE, True), ("RA", prb_RA, False), ("WA", prb_WA, False), ("WD", prb_WD, False)]:
	ocn.write("X_%s_rise = cross(VT(\"%s\") %g 1 \"%s\" t \"time\") - %g\n" % (s[0], s[1], VDD/2, "falling" if s[2] else "rising", Tstart*T))
	ocn.write("X_%s_fall = cross(VT(\"%s\") %g 1 \"%s\" t \"time\") - %g\n" % (s[0], s[1], VDD/2, "rising" if s[2] else "falling", Tstart*T))

# For the edge triggered sequential elements.
for s in [
		("RA", 4*T, 8*T),
		("WD", 4*T, 8*T),
		("WA", 4*T - setupTimes["Tsu_WA_rise"],  8*T - setupTimes["Tsu_WA_fall"]),
		("RE", 0*T - setupTimes["Tsu_RE_rise"], 12*T - setupTimes["Tsu_RE_fall"]),
		("WE", 0*T - setupTimes["Tsu_WE_rise"], 12*T - setupTimes["Tsu_WE_fall"])
	]:
	ocn.write("Tpd_%s_rise = (X_%s_rise - int(X_%s_rise / %g) * %g - %g)\n" % (s[0], s[0], s[0], Tcycle*T, Tcycle*T, s[1]))
	ocn.write("Tpd_%s_fall = (X_%s_fall - int(X_%s_fall / %g) * %g - %g)\n" % (s[0], s[0], s[0], Tcycle*T, Tcycle*T, s[2]))

# Calculate the threshold values for the propagation delay which if crossed mark
# a setup violation.
for s in ["RE", "RA", "WE", "WA", "WD"]:
	for e in ["rise", "fall"]:
		ocn.write("Tpdth_%s_%s = value(Tpd_%s_%s %g) * %f\n" % (s, e, s, e, (Tstart+Tcycle)*T, 1.05))

# Calculate the number of cycles after which the propagation delays cross the
# corresponding threshold value.
for s in ["RE", "RA", "WE", "WA", "WD"]:
	for e in ["rise", "fall"]:
		ocn.write("Nc_%s_%s = int(cross(Tpd_%s_%s Tpdth_%s_%s 1 \"rising\") / %g)\n" % (s, e, s, e, s, e, Tcycle*T))
		ocn.write("fprintf(p, \"Tho_%s_%s,%%g\\n\", %g + Nc_%s_%s * (%g))\n" % (s, e, Tinit, s, e, Tdr))

ocn.write("close(p)\n")

scs.close()
ocn.close()
