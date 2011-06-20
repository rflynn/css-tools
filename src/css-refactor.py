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
from collections import defaultdict
from optparse import OptionParser

import parse as cssparse
import refactor as cssrefactor

from parse import Rule, Sels, Decls, Decl, Ident, Delim

op = OptionParser()
op.add_option('--aggressive', dest='aggressive', action='store_true', help='perform expensive space-saving optimizations')
op.add_option('-v', '--verbose', dest='verbose', action='store_true', help='display progress')
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
if Opts.aggressive:
	print >> sys.stderr, 'aggressively optimizing...',
	for _ in ref.aggressive(yield_step=True, step_max=100):
		sys.stderr.write('.')
	sys.stderr.write('\n')

print ref.format()

