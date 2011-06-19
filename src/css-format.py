#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
from optparse import OptionParser

import parse as cssparse

op = OptionParser()
op.add_option('--canonical', action='store_true', help='print a nicely formatted, indented representation')
op.add_option('--minify', action='store_true', help='print the minimal possible equivalent representation')
op.add_option('--parse-tree', dest='parse_tree', action='store_true', help='show the internal parse tree')
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

if Opts.parse_tree:
	print doc
else:
	if Opts.minify:
		cssparse.Format.minify()
	else:
		cssparse.Format.canonical()
	print doc.format()

