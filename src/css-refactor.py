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
from itertools import combinations
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

Extracted_Overlapping_Rules = []

def extract_overlapping_decl_subsets(ref):

	# list of all overlapping decls subsets
	# NOTE: expensive
	overlap = filter(None,
			(set(x.decls.decl) & set(y.decls.decl)
				for x,y in combinations(ref.rules, 2)))
	if not overlap:
		return None

	overlap_decls_sets = [(tuple(o), set(o)) for o in overlap]

	# for each unique overlapping subset, build a set of all
	# decls that share it
	tmp = {}
	for r in ref.rules:
		rs = set(r.decls.decl)
		for k, ks in overlap_decls_sets:
			if (ks & rs) == ks:
				try:
					tmp[k][r] = 1
				except KeyError:
					tmp[k] = {r:1}
	overlap_decls_total = tmp

	# calculate difference between sum total lengths of decls - selectors
	for shared, rules in overlap_decls_total.items():
		sharedlen = sum(map(len, shared)) * len(rules)
		sellen = sum([len(r.sels) for r in rules.keys()])
		overlap_decls_total[shared] = (sharedlen - sellen, rules)

	# sort the overlapping subsets by the difference between the length of the decls
	# and the selectors; this is the space that we can save by applying it
	worth_it = list(filter(lambda x:x[1][0] > 0,
				overlap_decls_total.items()))
	if not worth_it:
		return None

	best = sorted(worth_it, key=lambda x:x[1][0], reverse=True)

	bestdecls, (bestscore, bestrules) = best[0]
	if bestscore < 1 or not bestrules:
		# no more space-saving overlaps
		return None

	# apply as many space-saving overlap extractions as possible
	affected = {}
	for bestdecls, (bestscore, bestrules) in best:

		# if we hit an entry that refers to a selector that
		# appeared in a previous entry we need to stop, because
		# it affects the results
		for r in bestrules:
			for sel in r.sels.sel:
				if sel in affected:
					return True
				affected[sel] = 1

		# build a new rule for bestrules/bestdecls
		extracted = Rule(Sels([r.sels for r in bestrules]),
				Decls(bestdecls))

		# remove shared subsets from the originals
		for r in bestrules:
			for d in bestdecls:
				try:
					r.decls.decl.remove(d)
				except ValueError:
					pass
	
		ref.rules.insert(0, extracted)

	return True

cnt = 0
while extract_overlapping_decl_subsets(ref):
	cnt += 1

print >> sys.stderr, 'cnt:', cnt

print ref.format()

