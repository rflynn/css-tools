#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
pretty-print
	sort alphabetically

minify
	skip comments
	skip whitespace where possible
	skip semi-colons where possible
	aggressively merge
	when done, merge all empty decl blocks into one
"""

# Ref: http://www.w3.org/TR/CSS2/syndata.html#color-units
COLORS = {
	'maroon'  : '800000',
	'red'     : 'ff0000',
	'orange'  : 'ffA500',
	'yellow'  : 'ffff00',
	'olive'   : '808000',
	'purple'  : '800080',
	'fuchsia' : 'ff00ff',
	'white'   : 'ffffff',
	'lime'    : '00ff00',
	'green'   : '008000',
	'navy'    : '000080',
	'blue'    : '0000ff',
	'aqua'    : '00ffff',
	'teal'    : '008080',
	'black'   : '000000',
	'silver'  : 'c0c0c0',
	'gray'    : '808080',
}
COLORS_REV = dict((v,k) for k,v in COLORS.items())

import sys

def color_shortest(color):
	"""
	given a color in the form #abc, #abcdef or by name,
	determine the shortest expression of this exact color
	"""
	if not color: return color
	rgb = color
	if rgb[0] == '#':
		rgb = rgb[1:]
	elif color in COLORS:
		rgb = COLORS[color]
		if len(color) <= 4:
			return color
	else:
		return color
	print 'rgb=',rgb
	if len(rgb) == 3:
		if rgb == 'f00': return 'red'
		return '#' + rgb 
	elif len(rgb) != 6:
		return color
	if rgb == rgb[0]*2 + rgb[2]*2 + rgb[5]*2:
		rgb = rgb[0] + rgb[2] + rgb[5]	
		if rgb == 'f00': return 'red'
		return '#' + rgb
	elif rgb in COLORS_REV:
		if len(COLORS_REV[rgb]) <= 4:
			return COLORS_REV[rgb]
	return color

if __name__ == '__main__':

	assert color_shortest('') == ''
	assert color_shortest('#abcdef') == '#abcdef'
	assert color_shortest('wtf') == 'wtf'
	assert color_shortest('#f00') == 'red'
	assert color_shortest('#ff0000') == 'red'
	assert color_shortest('red') == 'red'
	assert color_shortest('white') == '#fff'
	assert color_shortest('#aabbcc') == '#abc'
	assert color_shortest('#000080') == 'navy'
	assert color_shortest('navy') == 'navy'

