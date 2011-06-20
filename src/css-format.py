#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
"""
# TODO:
# 	* retain comment-using hacks as mentioned in http://developer.yahoo.com/yui/compressor/css.html#hacks


from test import CSSUnitTests

class FormatUnitTests(CSSUnitTests):
	def __init__(self):
		CSSUnitTests.__init__(self, 'minify')

if __name__ == '__main__':

	import sys
	from optparse import OptionParser

	import parse as cssparse

	op = OptionParser()
	op.add_option('--canonical',  dest='canonical',  action='store_true', help='print a nicely formatted, indented representation')
	op.add_option('--minify',     dest='minify',     action='store_true', help='print the minimal possible equivalent representation')
	op.add_option('--parse-tree', dest='parse_tree', action='store_true', help='show the internal parse tree')
	op.add_option('--test',       dest='test',       action='store_true', help='run unit test')
	Opts, Args = op.parse_args()

	if Opts.test:
		f = FormatUnitTests()
		f.test()
		exit(0)

	if Args:
		filename = Args[0]
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

