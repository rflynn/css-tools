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
from itertools import chain, combinations
from collections import defaultdict
from optparse import OptionParser

import parse as cssparse
from parse import Rule, Sels, Decls, Decl, Ident, Delim

def flatten(l): return list(chain.from_iterable(l))

# css string sort: # '@' < '*' < [a-zA-Z_] < '#' < '.' < '-'
# Unicode code points are within 'the range of integers from 0 to 0x10FFFF.'
# Ref: http://unicode.org/glossary/#code_point
FIRSTCHAR = {
	'.' : 0x110002,
	'#' : 0x110001,
	'-' : 0x110000,
	'*' : -1,
	'@' : -2,
}
def css_strcmp(x, y):
	if x and y:
		x0 = FIRSTCHAR.get(x[0], ord(x[0]))
		y0 = FIRSTCHAR.get(y[0], ord(y[0]))
		if x0 != y0:
			return x0 - y0
	return cmp(x, y)

class Inherit_(Ident):
	def __init__(self):
		super(self.__class__, self).__init__('inherit')

class Auto_(Ident):
	def __init__(self):
		super(self.__class__, self).__init__('auto')

class Normal_(Ident):
	def __init__(self):
		super(self.__class__, self).__init__('normal')

Inherit = Inherit_()
Auto = Auto_()
Normal = Normal_()

class Background:
	def __init__(self): pass
	def pre_process(self, prop): return prop
	def post_process(self, vals): return vals

class Border:
	def __init__(self): pass
	def pre_process(self, prop): return prop
	def post_process(self, vals): return vals

class Box:
	"""Box parent properties require exactly 4 child values"""
	def __init__(self, property_):
		self.property = property_
	def pre_process(self, prop): return prop
	def post_process(self, vals): return vals

class Font:
	def __init__(self): pass
	def pre_process(self, prop):
		# can't have line-height w/o font-size
		if 'line-height' in prop:
			if 'font-size' not in prop:
				prop['font-size'] = Decl('font-size', [Inherit])
		return prop
	def post_process(self, vals):
		try:
			fsi = [v.property for v in vals].index('font-size')
			if vals[fsi+1].property == 'line-height':
				vals.insert(fsi+1, Decl('line-height', [Delim('/')]))
		except (ValueError, IndexError):
			return vals
		return vals

class ListStyle:
	def __init__(self): pass
	def pre_process(self, prop): return prop
	def post_process(self, vals): return vals

PROPERTIES = {
	'background'		: (False, Background(),
		[
			'background-color',
			'background-image',
			'background-repeat',
			'background-attachment',
			'background-position',
		]),
	'background-color'	: (False, None, []),
	'background-image'	: (False, None, []),
	'background-repeat'	: (False, None, []),
	'background-attachment'	: (False, None, []),

	'border'		: (False, Box('border'),
		[
			'border-top',
			'border-right',
			'border-bottom',
			'border-left',
		]),
	'border-top'		: (False, None, []),
	'border-right'		: (False, None, []),
	'border-bottom'		: (False, None, []),
	'border-left'		: (False, None, []),

	'font'			: (True, Font(),
		[
			'font-style',
			'font-variant',
			'font-weight',
			'font-size',
			'line-height',
			'font-family',
		]),
	'font-style'		: (True, Normal,  []),
	'font-variant'		: (True, Normal,  []),
	'font-weight'		: (True, Normal,  []),
	'font-size'		: (True, Inherit, []),
	'line-height'		: (True, Inherit, []),
	'font-family'		: (True, Inherit, []),

	'margin'		: (False, Box('margin'),
		[
			'margin-top',
			'margin-right',
			'margin-bottom',
			'margin-left',
		]),
	'margin-top'		: (False, Auto, []),
	'margin-right'		: (False, Auto, []),
	'margin-bottom'		: (False, Auto, []),
	'margin-left'		: (False, Auto, []),

	'padding'		: (False, Box('padding'),
		[
			'padding-top',
			'padding-right',
			'padding-bottom',
			'padding-left',
		]),
	'padding-top'		: (False, Auto, []),
	'padding-right'		: (False, Auto, []),
	'padding-bottom'	: (False, Auto, []),
	'padding-left'		: (False, Auto, []),

	'list-style'		: (True, ListStyle(),
		[
			'list-style-type',
			'list-style-position',
			'list-style-image',
		]),
	'list-style-type'	: (True, Inherit, []),
	'list-style-position'	: (True, Inherit, []),
	'list-style-image'	: (True, Inherit, []),

}

# reverse lookup
PARENT = dict(flatten([[(child, prop) for child in children] for
		prop,(inherited,default,children) in PROPERTIES.items()]))

class CSSRefactor:
	def __init__(self, doc):
		self.doc = doc
		# merge all properies associated with each selector
		sels_merged = CSSRefactor.selectors_merge(doc)
		# merge child properties into parents
		foo = []
		for sel, decls in sels_merged.items():
			dcomb = CSSRefactor.decls_property_combine(decls)
			foo.append((sel, dcomb))

		# merge selectors having identical decls
		# TODO: would be better if we identified subsets of decls that were longer than their selector name,
		# then merged those, breaking decls up
		identical_decls = defaultdict(list)
		for s, d in foo:
			identical_decls[d].append(s)
		identical_decls = dict((d, sorted(s))
			for d, s in identical_decls.items())

		self.rules = []
		for d, s in sorted(identical_decls.items(), \
				key=lambda x:x[1], \
				cmp=lambda x,y: css_strcmp(x[0].format(), y[0].format())):
			# eliminate identical decls and sort
			d.decl = sorted(list(set(d.decl)), \
				cmp=lambda x,y: css_strcmp(x.property, y.property))
			#print s, d
			r = Rule(Sels(s), d)
			self.rules.append(r)

	def format(self):
		s = ''
		for at in self.doc.atrules:
			s += at.format()
		for r in self.rules:
			if r.decls.decl:
				s += r.format()
		return s.rstrip()

	def aggressive(self, yield_step=False, step_max=100):
		step = 1
		while step <= step_max and self.extract_overlapping_decl_subsets():
			if yield_step:
				yield step
			step += 1

	def extract_overlapping_decl_subsets(self):
		"""
		aggressive optimization (expensive, i.e. slow)
		for all declaration subsets shared by two or more selectors:
			break them out into a separate rule if it will save space when minimized
		"""

		rules = [(set(r.decls.decl), r) for r in self.rules]
		overlap = set([tuple(o) for o in
				(xs & ys for (xs,_),(ys,_) in combinations(rules, 2)) if o])
		if not overlap:
			return None

		"""
		# try to reduce number of least effective overlaps considered in each round
		# this hueristic reduces effectiveness ~10% but halves execution time
		maxoverlap = len(max(overlap, key=len))
		print >> sys.stderr, 'maxoverlap:', maxoverlap
		if maxoverlap > 2:
			overlap = [o for o in overlap if len(o) >= 2]
		print >> sys.stderr, 'rules(%u) * overlap(%u): %u' % (
			len(rules), len(overlap),
			len(rules) * len(overlap))
		"""

		# for each overlapping subset, set of all decls that contain it
		# O(n^2)... slow!
		overlap_decls_sets = [(set(o), o) for o in overlap]
		tmp = {}
		for rs, r in rules:
			for ks, k in overlap_decls_sets:
				if ((ks & rs) == ks):
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
		affected = set()
		for bestdecls, (bestscore, bestrules) in best:

			# if we hit an entry that refers to a selector that
			# appeared in a previous entry we need to stop, because
			# it affects the results
			for r in bestrules:
				for sel in r.sels.sel:
					if sel in affected:
						return True
					affected.add(sel)

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
	
			self.rules.insert(0, extracted)

		return True


	@staticmethod
	def selectors_merge(doc):
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
		return sel_decls

	@staticmethod
	def decls_property_combine(block):
		# merge decl based on property parents
		prop = defaultdict(list)
		parents = defaultdict(list)
		for decl in block.decl:
			prop[decl.property].append(decl)
			if decl.property in PARENT:
				parent = PARENT[decl.property]
				if parent:
					parents[parent].append(decl)
		if len(prop) != len(block.decl):
			# 1+ duplicate properties, go no further
			return block
		# now go by parents...
		for parent, decls in parents.iteritems():
			if parent in prop:
				# parent exists in the decl also; skip it for now
				continue
			merged = CSSRefactor.properties_merge(parent, decls)
			if merged:
				# remove merged children from prop
				for d in decls:
					del prop[d.property]
				# add new parent
				prop[merged.property].append(merged)
				#print 'decls_property_combine merged:', merged.format(), merged
		block.decl = [v[0] for v in prop.values()]
		#print 'decls_property_combine block:', block
		return block 

	@staticmethod
	def properties_merge(parent, decl):
		"""given a parent property string and a list of child decls,
		generate the equivalent combined Decl for the parent"""
		if len(decl) < 2:
			return None # don't bother merging < 2 children
		inherited, merger, children = PROPERTIES[parent]
		prop = dict((d.propertylow, d) for d in decl)
		vals = []
		prop2 = merger.pre_process(prop)
		# insert Decl in order defined by parent
		for c in children:
			if c in prop2:
				vals.append(prop2[c])
			else:
				inherit, default, _ = PROPERTIES[c]
				if inherit:
					pass # value can be omitted
				elif default:
					vals.append(Decl(c, [default]))
				else:
					# no value, no inheritance, no default. bail.
					return None
		if not vals:
			return None # couldn't merge
		vals = merger.post_process(vals)
		# we no longer need the Decl properties; strip Decl into values
		vals = flatten([d.values for d in vals])
		if len(vals) == 4 and isinstance(merger, Box):
			if vals[0] == vals[2]:
				if vals[1] == vals[3]:
					if vals[0] == vals[1]:
						# [top, right, bottom, left] -> [top/right/bottom/left]
						vals = vals[:1]
					else:
						# [top, right, bottom, left] -> [top/bottom, left/right]
						vals = vals[:2]
				else:
					# [top, right, bottom, left] -> [top, left/right, bottom]
					vals = vals[:3]
		return Decl(parent, vals)

	@staticmethod
	def decls_find_duplicate_properties(doc):
		"""
		not so easy; there are browser hacks out there that require this. be smarter.
		"""
		for r in doc.rules:
			decls = r.decls.decl
			d = dict([(x.property, x.values) for x in decls])
			if len(d) != len(decls):
				yield (r, len(decls) - len(d))

