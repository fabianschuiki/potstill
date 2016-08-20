# Copyright (c) 2016 Fabian Schuiki
#
# This file implements layout generation for memory macros. Given a macro
# specification it generates a structure representing individual cells that can
# be used by other parts of the generator to derive the placement of subcells
# or the location of obstructions and pins.

import sys, os, yaml


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
	def __init__(self, layout, cell, name, pos, mx=False, my=False, index=None, size=None):
		super(Inst, self).__init__()
		self.layout = layout
		self.cell = cell
		self.name = name
		self.pos = pos
		self.mx = mx
		self.my = my
		self.index = index
		self.size = size

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

		# Calculate the supply pin tracks.
		self.supply_layer_gds = self.config["supply_layer_gds"]
		self.supply_tracks = [
			("VSS" if y%2 == 0 else "VDD", y*self.row_height)
			for y in range(self.num_words+3)
		]

		# Calculate the macro size.
		self.size = Vec(
			self.num_bits * bit_width + addrdec_width,
			(self.num_words+2) * self.row_height
		)

		# Lower Bits
		x_lower   = 0
		x_addrdec = x_lower + self.num_bits_left * bit_width
		x_upper   = x_addrdec + addrdec_width
		bitarray_size = Vec(bit_width, self.num_words * self.row_height)

		self.bitarrays = [
			Inst(
				self, self.bitarray_cell,
				"XBA%d" % i,
				Vec(x_lower + (i+1)*bit_width, 0),
				mx=True,
				index=i,
				size=bitarray_size
			)
			for i in range(self.num_bits_left)
		] + [
			Inst(
				self, self.bitarray_cell,
				"XBA%d" % (i + self.num_bits_left),
				Vec(x_upper + i*bit_width, 0),
				index=i + self.num_bits_left,
				size=bitarray_size
			)
			for i in range(self.num_bits_right)
		]

		# Address Decoder
		self.addrdec = Inst(self, self.addrdec_cell, "XAD", Vec(x_addrdec, 0), index=self.num_words, size=Vec(addrdec_width, (self.num_words+1)*self.row_height))

		# Global Clock Gate
		rwckg_x = x_upper - rwckg_width
		rwckg_y = self.num_words * self.row_height
		self.rwckg = Inst(self, self.rwckg_cell, "XRWCKG", Vec(rwckg_x, rwckg_y))

		# Read Address Registers
		x_ralower = x_addrdec - (self.num_addr_left) * rareg_width
		x_raupper = x_upper
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
			Vec(x_addrdec, y_raregwire)
		))
		self.wiring.append(Inst(
			self, self.rareg_rwire_cell,
			"XRAWR",
			Vec(x_raupper, y_raregwire),
			mx=True
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
