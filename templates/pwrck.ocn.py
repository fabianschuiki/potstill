#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki

import sys, os
BASE = sys.path[0]+"/.."

if len(sys.argv) != 2:
	sys.stderr.write("usage: %s NADDR\n" % sys.argv[0])
	sys.exit(1)

num_addr = int(sys.argv[1])
VDD = 1.2
T = 5

print("openResults(\"./pwrck.psf\")")
print("selectResult('tran)")

print("p = outfile(\"pwrck.csv\", \"w\")")
print("fprintf(p, \"P_leak,%%g\\n\", integ(-IT(\"VDD:p\") 0n %gn) / %gn * 1.2)" % (1*T, 1*T))
print("fprintf(p, \"E_idle_rise,%%g\\n\", integ(-IT(\"VDD:p\") %gn %gn) * 1.2)" % (1*T, 2*T))
print("fprintf(p, \"E_idle_fall,%%g\\n\", integ(-IT(\"VDD:p\") %gn %gn) * 1.2)" % (2*T, 3*T))

Tswp = (2**num_addr) * 3

for p in [
		("read_rise",  0, 1), ("read_fall",  0, 2),
		("write_rise", 1, 1), ("write_fall", 1, 2),
		("rw_rise",    2, 1), ("rw_fall",    2, 2),
	]:
	print("fprintf(p, \"E_%s,%%g\\n\", (%s) / %d * 1.2)" % (
		p[0],
		" + ".join(["integ(-IT(\"VDD:p\") %gn %gn)" % (
			((i+1)*3 + p[1]*Tswp + p[2]+0)*T,
			((i+1)*3 + p[1]*Tswp + p[2]+1)*T
		) for i in range(2**num_addr)]),
		2**num_addr
	))

print("close(p)")
