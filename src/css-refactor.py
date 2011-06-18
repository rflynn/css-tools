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
from itertools import chain
from collections import defaultdict
from optparse import OptionParser

import parse as cssparse
import refactor as cssrefactor

from parse import Rule, Sels, Decls, Decl, Ident, Delim

op = OptionParser()
#op.add_option('--parse-tree', dest='parse_tree', action='store_true', help='show the internal parse tree')
(Opts, Args) = op.parse_args()

if Args:
	filename = Args[0]
	f = open(filename, 'r')
	contents = f.read()
	f.close()
else:
	filename = '-'
	contents = sys.stdin.read()

cssparse.Format.canonical()

doc = cssparse.CSSDoc.parse(contents)
ref = cssrefactor.CSSRefactor(doc)

import itertools

# list of all overlapping decls subsets
overlap = (set(x.decls.decl) & set(y.decls.decl)
		for x,y in itertools.combinations(ref.rules, 2))
overlap2 = filter(None, overlap)
print overlap2
od = dict.fromkeys(map(tuple, overlap2), {})

# for each unique overlapping subset, build a set of all
# decls that share it
for r in ref.rules:
	rs = set(r.decls.decl)
	for k, v in od.items():
		ks = set(k)
		if len(ks & rs) == len(ks):
			v[r] = 1
print od

# calculate the sum total length of the selectors of the overlapping decls

# sort the overlapping subsets by total size, i.e.
# figure out which ones will save the most space if condensed

# if we have 1 or more overlapping subsets, and the best one will save us
# space, use it. pull the subsets out of each decl and build a new rule from
# their selectors. save this for later.

# the removal of these subsets of 2+ selectors could potentially effect
# every other overlapping subset, so do everything over again until we run out
# of subset operations that save space.

# now merge the remaining doc rules with the factored-out ones into a coherent document

#print ref.format()

