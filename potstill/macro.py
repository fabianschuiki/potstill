# Copyright (c) 2016 Fabian Schuiki

import os

class Macro(object):
	def __init__(self, num_addr, num_bits, vdd=1.2, temp=25, name=None):
		super(Macro, self).__init__()
		self.num_addr = num_addr
		self.num_bits = num_bits
		self.vdd = vdd
		self.temp = temp
		self.num_words = 2**num_addr
		self.name = name or ("PS%dX%d" % (2**num_addr, num_bits))
		self.techdir = os.path.dirname(__file__)+"/../umc65"

class MacroConditions(Macro):
	def __init__(self, *args, **kwargs):
		super(MacroConditions, self).__init__(*args, **kwargs)
