# Copyright (c) 2016 Fabian Schuiki
#
# This file implements simulation model output generation.

import re, sys


def make(macro, template_path):
	# Read the template file.
	with open(template_path) as f:
		template = f.read()

	# Evaluate the placeholders.
	template = re.sub(
		'{(.*?)}',
		lambda match: str(eval(match.group(1), {}, {
			"NAME": macro.name,
			"NW": macro.num_words,
			"NA": macro.num_addr,
			"NB": macro.num_bits
		})),
		template
	)

	return template


def make_vhdl(macro):
	return make(macro, macro.techdir+"/model.vhd")
