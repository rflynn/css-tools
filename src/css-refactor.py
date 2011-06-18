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
from collections import defaultdict

Extracted_Overlapping_Rules = []

def extract_overlapping_decl_subsets(ref):

	# list of all overlapping decls subsets
	overlap = (set(x.decls.decl) & set(y.decls.decl)
			for x,y in itertools.combinations(ref.rules, 2))
	overlap2 = filter(None, overlap)

	overlap_decls = dict.fromkeys(map(tuple, overlap2), {})

	# for each unique overlapping subset, build a set of all
	# decls that share it
	tmp = defaultdict(dict)
	for r in ref.rules:
		rs = set(r.decls.decl)
		for k, v in overlap_decls.items():
			ks = set(k)
			if (ks & rs) == ks:
				tmp[k][r] = 1
	overlap_decls = dict(tmp)
	if not overlap_decls:
		return None

	# calculate difference between sum total lengths of decls - selectors
	for shared, rules in overlap_decls.items():
		sharedlen = sum(map(len, shared)) * len(rules)
		sellen = sum([len(r.sels) for r in rules.keys()])
		overlap_decls[shared] = (sharedlen - sellen, rules)

	# sort the overlapping subsets by the difference between the length of the decls
	# and the selectors; this is the space that we can save by applying it
	best = max(overlap_decls.items(), key=lambda x:x[1][0])
	bestdecls, (bestscore, bestrules) = best
	if bestscore < 1 or not bestrules:
		# no more space-saving overlaps
		return None

	# build a new rule for bestrules/bestdecls
	extracted = Rule(Sels([r.sels for r in bestrules]),
			Decls(bestdecls))

	# remove shared subsets from the originals
	for r in bestrules:
		for d in bestdecls:
			r.decls.decl.remove(d)

	ref.rules.insert(0, extracted)

	return extracted

while extract_overlapping_decl_subsets(ref):
	pass

print ref.format()

