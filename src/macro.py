# Copyright (c) 2016 Fabian Schuiki

class Macro(object):
	def __init__(self, num_addr, num_bits, name=None):
		super(Macro, self).__init__()
		self.num_addr = num_addr
		self.num_bits = num_bits
		self.num_words = 2**num_addr
		self.name = (name if name is not None else "PS%dX%d" % (2**num_addr, num_bits))

class MacroConditions(Macro):
	def __init__(self, *args, vdd=1.2, temp=25, **kwargs):
		super(MacroConditions, self).__init__(*args, **kwargs)
		self.vdd = vdd
		self.temp = temp
