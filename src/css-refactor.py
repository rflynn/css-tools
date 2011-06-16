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

