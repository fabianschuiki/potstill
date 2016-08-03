#!/usr/bin/env python3
# Copyright (c) 2016 Fabian Schuiki

import sys, os
BASE = sys.path[0]+"/.."

if len(sys.argv) != 2:
	sys.stderr.write("usage: %s NADDR\n" % sys.argv[0])
	sys.exit(1)

num_addr = int(sys.argv[1])
VDD = 1.2

print("openResults(\"./trdwr.psf\")")
print("selectResult('tran)")

print("p = outfile(\"trdwr.csv\", \"w\")")
print("fprintf(p, \"t_wr,%%g\\n\", cross(VT(\"X.XBA0.X%d.nZ\") %g 1) - cross(VT(\"CK\") %g 1))" % (2**num_addr-1, VDD/2, VDD/2))
print("fprintf(p, \"t_rd,%%g\\n\", cross(VT(\"RD0\") %g 1) - cross(VT(\"CK\") %g 3))" % (VDD/2, VDD/2))
print("close(p)")
