#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
first, merge the contents of identical selectors
then, merge any 2+ sub-properties into their common parent
--oocss
	# Ref: https://github.com/stubbornella/oocss/wiki
	identify declarations that would benefit from object-oriented css:
		1. Separate structure from skin
		2. Separate container and content
"""

import sys
from optparse import OptionParser

import parse as cssparse
from parse import Color, Uri, Percent, Number

class Inherit:
	def __init__(self): pass

class Auto:
	def __init__(self): pass

class Normal:
	def __init__(self): pass

class Background:
	def __init__(self): pass

class Border:
	def __init__(self): pass

class BorderWidth:
	def __init__(self): pass

class BorderStyle:
	def __init__(self): pass

class BorderColor:
	def __init__(self): pass

class Font:
	def __init__(self): pass

class Margin:
	def __init__(self): pass

class Padding:
	def __init__(self): pass

class ListStyle:
	def __init__(self): pass

class Property:
	def __init__(self, name, inherited, values, children):
		pass

PROPERTIES = [
	"""
	NOTE: default values, anywhere, may be omitted if they are the default
	"""

	('background', 		False,	Background,
		[
			'background-color',
			'background-image',
			'background-repeat',
			'background-attachment',
			'background-position',
		]),
	('background-color',	False,	None, []),
	('background-image',	False,	None, []),
	('background-repeat',	False,	None, []),
	('background-attachment',False,	None, []),

	('border',		False,	Border,
		[
			'border-width',
			'border-style',
			'border-color',
		]),
	('border-width',	False,	BorderWidth,
		[
			'border-top-width',
			'border-right-width',
			'border-bottom-width',
			'border-left-width',
		]),
	('border-top-width',	False,	None, []),
	('border-right-width',	False,	None, []),
	('border-bottom-width',	False,	None, []),
	('border-left-width',	False,	None, []),
	('border-style',	False,	BorderStyle,
		[
			'border-top-style',
			'border-right-style',
			'border-bottom-style',
			'border-left-style',
		]),
	('border-top-style',	False,	None, []),
	('border-right-style',	False,	None, []),
	('border-bottom-style',	False,	None, []),
	('border-left-style',	False,	None, []),
	('border-color',	False,	BorderColor,
		[
			'border-top-color',
			'border-right-color',
			'border-bottom-color',
			'border-left-color',
		]),
	('border-top-color',	False,	None, []),
	('border-right-color',	False,	None, []),
	('border-bottom-color',	False,	None, []),
	('border-left-color',	False,	None, []),

	('font', 		True,	Font,
		[
			'font-style',
			'font-variant',
			'font-weight',
			'font-size',
			'line-height',
			'font-family',
		]),
	('font-style',		True,	Normal, []),
	('font-variant',	True,	Normal, []),
	('font-weight',		True,	Normal, []),
	('font-size',		True,	Inherit, []),
	('line-height',		True,	Inherit, []),
	('font-family',		True,	Inherit, []),

	('margin', 		False,	Margin,
		[
			'margin-top',
			'margin-right',
			'margin-bottom',
			'margin-left',
		]),
	('margin-top',		False,	Auto, []),
	('margin-right',	False,	Auto, []),
	('margin-bottom',	False,	Auto, []),
	('margin-left',		False,	Auto, []),

	('padding', 		False,	Padding,
		[
			'padding-top',
			'padding-right',
			'padding-bottom',
			'padding-left',
		]),
	('padding-top',		False,	Auto, []),
	('padding-right',	False,	Auto, []),
	('padding-bottom',	False,	Auto, []),
	('padding-left',	False,	Auto, []),

	('list-style', 		True,	ListStyle,
		[
			'list-style-type',
			'list-style-position',
			'list-style-image',
		]),
	('list-style-type',	True,	Inherit, []),
	('list-style-position',	True,	Inherit, []),
	('list-style-image',	True,	Inherit, []),

]

def decl_find_duplicate_properties(doc):
	"""
	not so easy; there are browser hacks out there that require this. be smarter.
	"""
	for r in doc.rules:
		decls = r.decls.decl
		d = dict([(x.property, x.values) for x in decls])
		if len(d) != len(decls):
			yield (r, len(decls) - len(d))

def selectors_merge_identical(doc):
	"""
	for each unique selector:
		merge all specified decls
	this allows us to perform intra-decl operations
	"""
	sel_decls = {}
	for r in doc.rules:
		for sel in r.sels.sel:
			try:
				sel_decls[sel] += r.decls
			except KeyError:
				sel_decls[sel] = r.decls
	print sel_decls
	for k,v in sel_decls.items():
		print k.format(), v.format()

"""
algorithm given PROPERTIES[property] = {name, inherited, default, children}
the goal of which is to combine properties into parent properties in order
which often (but not always) produce shorter equivalent code
"""
from collections import defaultdict
def property_combine(decls):
	# merge decl based on property parents
	parents = defaultdict(list)
	for decl in decls.decls:
		parent = PROPERTIES[decl.property].parent
		if parent:
			parents[parent].append(decl)
	# now go by parents...
	# FIXME hmmm... there are 3 layers of tags, 2 possible levels
	# of parents; do I bring everything to the top-most layer,
	# or go iteratively or what?...
	for parent,decls in parents.itervalues():
		pass

op = OptionParser()
(Opts, Args) = op.parse_args()

if Args:
	filename = Args[0]
	# TODO: add support for URLs
	f = open(filename, 'r')
	contents = f.read()
	f.close()
else:
	filename = '-'
	contents = sys.stdin.read()

doc = cssparse.CSSDoc.parse(contents)
print doc.rules

cssparse.Format.canonical()

selectors_merge_identical(doc)

"""
rules_with_dupes = list(decl_find_duplicate_properties(doc))
if rules_with_dupes:
	print '/* !!! Duplicate decl properties !!! */'
	for r, dupecnt in rules_with_dupes:
		print r.format()
"""

