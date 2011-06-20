#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
"""
# TODO:
# 	* retain comment-using hacks as mentioned in http://developer.yahoo.com/yui/compressor/css.html#hacks

import os

class FormatTest:
	def __init__(self):
		self.tests = []
		for root, dirs, files in os.walk('../test/minify'):
			for name in files:
				if name.endswith('.css'):
					filename = os.path.join(root, name)
					self.tests.append(FormatTest.parse_test(filename))

	def test(self):
		passed = 0
		cssparse.Format.minify()
		for filename, before, after in self.tests:
			print filename,
			doc = cssparse.CSSDoc.parse(before)
			result = doc.format()
			if result == after:
				print 'OK'
			else:
				print '!! expected "%s", got "%s"' % (after, result)
		cssparse.Format.pop()
		assert passed == len(self.tests)

	@staticmethod
	def parse_test(filename):
		try:
			fd = open(filename, 'r')
			t = fd.read()
			fd.close()
			bb = t.find('/* before ')
			be = t.find('*/', bb) + 2
			ab = t.find('/* after ', be)
			ae = t.find('*/', ab) + 2
			before = t[be:ab].strip()
			after = t[ae:].strip()
			return (filename, before, after)
		except Exception as e:
			print e
			print 'test "%s" is fucked up. fix it!' % (filename,)
			exit(1)

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
		f = FormatTest()
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

