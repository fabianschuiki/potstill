# Copyright (c) 2016 Fabian Schuiki
#
# This file implements layout generation for memory macros. Given a macro
# specification it generates a structure representing individual cells that can
# be used by other parts of the generator to derive the placement of subcells
# or the location of obstructions and pins.

import sys, os, yaml
from bisect import bisect
from functools import reduce


class Vec():
	def __init__(self, x, y):
		self.x = x
		self.y = y


class Cell(object):
	def __init__(self, name, config, suffix=None):
		super(Cell, self).__init__()
		self.name = name + (suffix or "")
		self.config = config
		self.gds_struct = config["gds_struct"] + (suffix or "")


class InstPin(object):
	def __init__(self, name, config, inst, index=None, track=None, additional_rects=None):
		self.name = name
		self.name_gds = name
		if index is not None:
			self.name += "[%d]" % index
			self.name_gds += "%d" % index
		self.config = config
		self.inst = inst
		self.index = index
		self.track = track

		self.dir = "OUTPUT" if name == "RD" else "INPUT"
		self.use = "CLOCK" if name == "CK" else "SIGNAL"
		self.shape = None
		self.layer = config["layer"]
		self.layer_gds = config["layer_gds"]
		self.additional_rects = additional_rects
		self.anchor = Vec(
			config["anchor"][0] * self.inst.size.x,
			config["anchor"][1] * self.inst.size.y
		) if "anchor" in config else Vec(0,0)

		# Calculate where the pin label should be positioned.
		r = next(self.rects())
		self.label_pos = Vec((r[0].x+r[1].x)*0.5, (r[0].y+r[1].y)*0.5)

	def rects(self):
		if "geometry" in self.config:
			for a in self.config["geometry"]:
				yield (
					self.inst.to_world(Vec(a[0]*1e-6 + self.anchor.x, a[1]*1e-6 + self.anchor.y)),
					self.inst.to_world(Vec(a[2]*1e-6 + self.anchor.x, a[3]*1e-6 + self.anchor.y))
				)

		if self.additional_rects is not None:
			for r in self.additional_rects:
				yield (
					self.inst.to_world(self.rect[0]),
					self.inst.to_world(self.rect[1])
				)

		if self.track is not None:
			a = Vec((self.track + 0.25) * self.inst.layout.grid, 0.05e-6)
			b = Vec((self.track + 0.75) * self.inst.layout.grid, self.inst.size.y - 0.05e-6)
			yield (self.inst.to_world(a), self.inst.to_world(b))


class Inst(object):
	def __init__(self, layout, cell, name, pos, mx=False, my=False, index=None, size=None, stack=None, stack_step=None):
		super(Inst, self).__init__()
		self.layout = layout
		self.cell = cell
		self.name = name
		self.pos = pos
		self.mx = mx
		self.my = my
		self.index = index
		self.size = size
		self.stack = stack
		self.stack_step = stack_step

	def to_world(self, v):
		return Vec(
			self.pos.x + (-v.x if self.mx else v.x),
			self.pos.y + (-v.y if self.my else v.y)
		)

	def pins(self):
		if "pins" in self.cell.config:
			for (name, cfg) in self.cell.config["pins"].items():
				if "tracks" in cfg:
					for (idx, trk) in enumerate(cfg["tracks"][self.index]):
						yield InstPin(name, cfg, self, index=idx, track=trk)
				else:
					yield InstPin(name, cfg, self, index=self.index)


def layout_columns(columns):
	x = 0
	for col in columns:
		col.pos.x = (x + col.size.x if col.mx else x)
		x += col.size.x
	return x


class Layout(object):
	def __init__(self, macro):
		super(Layout, self).__init__()
		self.macro = macro
		self.cells = list()
		self.num_addr = macro.num_addr
		self.num_bits = macro.num_bits
		self.num_words = 2**self.num_addr
		self.name = "PS%dX%d" % (self.num_words, self.num_bits)
		self.wiring = list()
		with open(macro.techdir+"/config.yml") as f:
			self.config = yaml.load(f)

		# Calculate the number of bits and address bits that go to the left and
		# right of the central spine.
		self.num_bits_left  = int(self.num_bits/2)
		self.num_bits_right = self.num_bits - self.num_bits_left
		self.num_addr_left  = int(self.num_addr/2)
		self.num_addr_right = self.num_addr - self.num_addr_left

		# Load the cell descriptions.
		cells = self.config["cells"]
		self.rwckg_cell = Cell("rwckg", cells["rwckg"])
		self.addrdec_cell = Cell("addrdec", cells["addrdec"], suffix=str(self.num_words))
		self.bitarray_cell = Cell("bitarray", cells["bitarray"], suffix=str(self.num_words))
		self.rareg_cell = Cell("rareg", cells["rareg"])
		self.rareg_lwire_cell = Cell("raregwire", cells["raregwire"], suffix=str(self.num_addr_left))
		self.rareg_rwire_cell = Cell("raregwire", cells["raregwire"], suffix=str(self.num_addr_right))
		self.welltap_cell = Cell("welltap", cells["welltap"])
		self.welltap_awire_cell = Cell("welltap_wa", self.welltap_cell.config["wiring_a"])
		self.welltap_bwire_cell = Cell("welltap_wb", self.welltap_cell.config["wiring_b"])

		# Read and prepare some basic dimensions required for partitioning.
		G = self.config["track"]
		self.grid = G
		self.row_height_trk = self.config["row-height"]
		self.row_height = self.row_height_trk*G

		self.regwd_y_trk = self.num_words * self.row_height_trk
		self.column_width_trk = self.config["widths"]["bitarray"]
		self.addrdec_width_trk = self.config["widths"]["addrdec"][self.num_words]
		self.column_right_trk = self.num_bits_left * self.column_width_trk + self.addrdec_width_trk
		bit_width = self.column_width_trk*G
		rwckg_width = self.config["widths"]["rwckg"]*G
		addrdec_width = self.addrdec_width_trk*G
		rareg_width = self.config["widths"]["rareg"]*G
		bitarray_size = Vec(bit_width, self.num_words * self.row_height)
		column_height = (self.num_words+1)*self.row_height
		welltap_width = float(self.welltap_cell.config["width"])
		welltap_cadence = float(self.welltap_cell.config["cadence"])

		# Calculate the supply pin tracks.
		self.supply_layer_gds = self.config["supply_layer_gds"]
		self.supply_tracks = [
			("VSS" if y%2 == 0 else "VDD", y*self.row_height)
			for y in range(self.num_words+3)
		]

		# Assemble the columns of the memory, which consist of bit arrays,
		# welltaps, and the address decoder.

		# Lower and upper bits.
		lower_bits = [
			Inst(
				self, self.bitarray_cell,
				"XBA%d" % i,
				Vec(0, 0),
				mx=True,
				index=i,
				size=bitarray_size
			)
			for i in range(self.num_bits_left)
		]
		upper_bits = [
			Inst(
				self, self.bitarray_cell,
				"XBA%d" % (i + self.num_bits_left),
				Vec(0, 0),
				index=i + self.num_bits_left,
				size=bitarray_size
			)
			for i in range(self.num_bits_right)
		]
		self.bitarrays = lower_bits + upper_bits

		# Address Decoder
		self.addrdec = Inst(
			self, self.addrdec_cell, "XAD",
			# Vec(x_addrdec, 0),
			Vec(0, 0),
			index=self.num_words,
			size=Vec(addrdec_width, column_height)
		)

		columns = lower_bits + [self.addrdec] + upper_bits


		# Determine a reasonable distribution for the welltaps.
		width = layout_columns(columns)
		num_welltaps = int(width/(welltap_cadence - welltap_width)) + 2
		max_spacing = None
		welltap_placement = None

		while welltap_placement is None or max_spacing > welltap_cadence:

			# Calculate the approximate position for each welltap.
			approx_welltap_positions = [
				width * i / (num_welltaps-1) for i in range(num_welltaps)
			]

			# Calculate the index of the column before which each welltap should
			# be inserted. This positions each welltap to the left of each
			# approximate positions.
			colpos = [col.pos.x for col in columns]
			welltap_indices = [
				max(0, min(len(columns), bisect(colpos, x)))
				for x in approx_welltap_positions
			]

			# Extract the position the welltaps would have if placed at the
			# indices found above.
			welltap_placement = [
				(i, columns[i].pos.x if i < len(columns) else width)
				for i in welltap_indices
			]

			# Calculate the maximum spacing between two neighbouring welltaps.
			max_spacing = reduce(max, [
				b - a + welltap_width
				for ((_,a),(_,b)) in zip(welltap_placement[:-1], welltap_placement[1:])
			])

			# Increase the number of welltaps. If the max_spacing calculated
			# above is greater than the required welltap cadence, the loop body
			# is re-executed with one more welltap.
			num_welltaps += 1


		# Insert the welltaps and the required wiring on top of them.
		self.welltaps = list()
		for (i, (offset, _)) in enumerate(reversed(welltap_placement)):
			wt = Inst(self, self.welltap_cell, "WT%d" % i, Vec(0,0),
				size=Vec(welltap_width, column_height),
				stack=self.num_words+1,
				stack_step=self.row_height
			)
			self.welltaps.append(wt)
			columns.insert(offset, wt)


		# Rearrange the columns a final time and calculate the size of the
		# macro.
		self.size = Vec(
			layout_columns(columns),
			(self.num_words+2) * self.row_height
		)


		# Add the wiring to the welltaps.
		for wt in self.welltaps[1:-1]:
			flip = wt.pos.x < self.addrdec.pos.x + 0.5*addrdec_width
			self.wiring.append(Inst(
				self, self.welltap_awire_cell, wt.name+"WA",
				Vec(wt.pos.x + welltap_width if flip else wt.pos.x, wt.pos.y),
				stack=self.num_words,
				stack_step=self.row_height,
				mx=flip
			))
			self.wiring.append(Inst(
				self, self.welltap_bwire_cell, wt.name+"WB",
				Vec(
					wt.pos.x + welltap_width if flip else wt.pos.x,
					wt.pos.y + self.num_words * self.row_height
				),
				mx=flip
			))


		# Place the global clock gate and address registers which are attached
		# to the address decoder layout-wise.
		x_spine_l = self.addrdec.pos.x
		x_spine_r = x_spine_l + self.addrdec.size.x

		# Global Clock Gate
		rwckg_x = x_spine_r - rwckg_width
		rwckg_y = self.num_words * self.row_height
		self.rwckg = Inst(self, self.rwckg_cell, "XRWCKG", Vec(rwckg_x, rwckg_y))

		# Read Address Registers
		x_ralower = x_spine_l - (self.num_addr_left) * rareg_width
		x_raupper = x_spine_r
		y_rareg = (self.num_words+2) * self.row_height

		self.raregs = [
			Inst(
				self, self.rareg_cell,
				"XRA%d" % i,
				Vec(x_ralower + (i+1)*rareg_width, y_rareg),
				index=i,
				mx=True,
				my=True
			)
			for i in range(self.num_addr_left)
		] + [
			Inst(
				self, self.rareg_cell,
				"XRA%d" % (i+self.num_addr_left),
				Vec(x_raupper + i*rareg_width, y_rareg),
				index=(i + self.num_addr_left),
				my=True
			)
			for i in range(self.num_addr_right)
		]

		y_raregwire = (self.num_words+1) * self.row_height
		self.wiring.append(Inst(
			self, self.rareg_lwire_cell,
			"XRAWL",
			Vec(x_spine_l, y_raregwire)
		))
		self.wiring.append(Inst(
			self, self.rareg_rwire_cell,
			"XRAWR",
			Vec(x_spine_r, y_raregwire),
			mx=True
		))

		# Add the welltaps flanking the read address registers.
		for (p, x) in [
			("L", self.raregs[0].pos.x - rareg_width - welltap_width),
			("R", self.raregs[-1].pos.x + rareg_width)
		]:
			self.welltaps.append(Inst(
				self, self.welltap_cell, "WTRA%s" % p, Vec(x, y_rareg),
				size=Vec(welltap_width, self.row_height),
				my=True
			))


	def pins(self):
		for p in self.rwckg.pins():
			yield p
		for p in self.addrdec.pins():
			yield p
		for reg in self.raregs:
			for p in reg.pins():
				yield p
		for b in self.bitarrays:
			for p in b.pins():
				yield p
