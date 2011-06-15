#!/usr/bin/env python
# -*- coding:utf-8 -*-

from sys import stdin
from optparse import OptionParser

from parse import CSSDoc,Format

op = OptionParser()
op.add_option('--minify', type="store_false", default=False, help='print the minimal possible equivalent representation')
op.add_option('--canonical', type="store_false", default=False, help='print a nicely formatted, indented representation')
op.add_option('--parse-tree', type="store_false", default=False, help='show the internal parse tree')
op.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True, help="STFU")
(Opts, Args) = op.parse_args()

if Args:
	filename = Args[0]
	# TODO: add support for URLs
	f = open(filename, 'r')
	contents = f.read()
	f.close()
else: # read from stdin
	filename = '-'
	contents = stdin.read()

doc = CSSDoc(contents)



"""
Checks:
	- dimensions without unit should be converted to 'px'
	- too many similar but different colors in the same range
	- validate against known web browser versions and CSS standards

Normalize:
	- find/merge redundant/conflicting
		- selectors
			h1 { font-family: sans-serif }
			h2 { font-family: sans-serif }
			h3 { font-family: sans-serif }
			h1, h2, h3 { font-family: sans-serif }
	- find/merge redundant/conflicting decls
	- merge together separate decls:
		from:
			border-top-width: 1px;
			border-right-width: 2px;
			border-bottom-width: 3px;
		to:
			border-width: 1px 2px 3px auto;

Output:
	- pretty-print
	- minify
		-eliminate unnecessary whitespace
		-remove unnecessary ';' in last decl
		-strip comments(?)
		-reduce color codes
			#cccccc -> #ccc
			#ff0000 -> red
		-merge identical/subset decls
			apply all merging aggressively
"""


