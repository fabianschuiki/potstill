# Copyright (c) 2016 Fabian Schuiki
#
# This file implements GDS output generation using the Phalanx tool.

import sys, numbers, itertools, subprocess


def argify(v):
	if isinstance(v, numbers.Integral):
		return "%d" % v
	elif isinstance(v, numbers.Real):
		return "%.8g" % v
	else:
		return str(v)


class PhalanxWriter(object):
	def __init__(self):
		super(PhalanxWriter, self).__init__()
		self.lines = list()
		self.level = 0
		self.prefix = ""

	def set_level(self, level):
		self.level = level
		self.prefix = "    "*level

	def comment(self, *lines):
		self.lines += [self.prefix + ("# "+(l or "")).strip() for l in lines]

	def skip(self, num=1):
		self.lines += itertools.repeat("", num)

	def cmd(self, *args, suffix=";"):
		self.lines.append(self.prefix + " ".join([argify(a) for a in args if a is not None]) + suffix)

	def pushgrp(self, *args):
		self.cmd(*args, suffix=" {")
		self.set_level(self.level+1)

	def popgrp(self):
		assert(self.level > 0)
		self.set_level(self.level-1)
		self.lines.append(self.prefix+"}")

	def inst(self, inst):
		self.pushgrp("inst", inst.cell.gds_struct, inst.name)
		self.cmd("set_position", inst.pos.x, inst.pos.y)
		if inst.mx or inst.my:
			self.cmd("set_orientation", "MX" if inst.mx else None, "MY" if inst.my else None)
		self.popgrp()

	def collect(self):
		return "\n".join(self.lines)+"\n"


# Generate the input script for Phalanx that assembles the given layout into the
# given GDS output file.
def make_phalanx_input(layout, outfile):
	wr = PhalanxWriter()
	wr.comment(
		None,
		"Standard Cell Based Memory",
		"%d words, %d bits" % (layout.macro.num_words, layout.macro.num_bits),
		None,
		"Phalanx GDS assembly script. Automatically generated by Potstill",
		None
	)
	wr.skip()

	# Import the required GDS file.
	if "import" in layout.config and "gds" in layout.config["import"]:
		imports = layout.config["import"]["gds"]
		if len(imports) > 0:
			wr.comment("Import building blocks")
			for imp in imports:
				wr.cmd("load_gds", '"'+layout.macro.techdir+"/"+imp+'"')
			wr.skip()

	# Open the root cell.
	wr.comment("Root Cell")
	wr.pushgrp("cell", layout.macro.name)
	wr.cmd("set_size", layout.size.x, layout.size.y)
	wr.skip()

	# Instantiate the bit columns.
	wr.comment("Bit Arrays")
	for ba in layout.bitarrays:
		wr.inst(ba)
	wr.skip()

	# Instantiate the address decoder.
	wr.comment("Address Decoder")
	wr.inst(layout.addrdec)
	wr.skip()

	# Instantiate the global clock gate.
	wr.comment("Global Clock Gate")
	wr.inst(layout.rwckg)
	wr.skip()

	# Instantiate the read address registers.
	wr.comment("Read Address Registers")
	for r in layout.raregs:
		wr.inst(r)
	wr.skip()

	# Add the pin labels. These are used to perform LVS checks.
	wr.comment("Pin Labels")
	for pin in layout.pins():
		wr.cmd("add_gds_text", pin.layer_gds, 0, pin.label_pos.x, pin.label_pos.y, '"'+pin.name+'"')

	# Close the root cell.
	wr.popgrp()
	wr.skip()


	# Store the cell GDS data.
	wr.comment("Generate GDS data")
	wr.pushgrp("gds", layout.macro.name)
	wr.cmd("make_gds_for_cell", layout.macro.name)
	wr.cmd("write_gds", '"'+outfile+'"')
	wr.popgrp()

	return wr.collect()


# Uses the phalanx tool to generate GDS output for the given layout.
def make_gds(layout, outfile):
	script = make_phalanx_input(layout, outfile)
	with subprocess.Popen(["phalanx"], stdin=subprocess.PIPE, stdout=sys.stderr, stderr=sys.stderr, universal_newlines=True) as phx:
		phx.stdin.write(script)
		phx.stdin.close()
		phx.wait()
		if phx.returncode != 0:
			sys.stderr.write("Phalanx failed to generate GDS data\n")
			sys.exit(1)
