#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
Base unit test object for css-tools
"""

import os

import parse as cssparse

class CSSUnitTests:
	PATH = '../test/'
	def __init__(self, testdir):
		self.tests = []
		self.skipped = []
		for root, dirs, files in os.walk(CSSUnitTests.PATH + testdir):
			for name in files:
				filename = os.path.join(root, name)
				if name.endswith('.css'):
					self.tests.append(CSSUnitTests.parse_test(filename))
				elif '.css.' in name:
					self.skipped.append(filename)

	def test(self):
		passed = 0
		cssparse.Format.minify()
		for filename, before, after in self.tests:
			print filename[len(CSSUnitTests.PATH):],
			doc = cssparse.CSSDoc.parse(before)
			result = doc.format()
			if result == after:
				print 'OK'
				passed += 1
			else:
				print '!! expected "%s", got "%s"' % (after, result)
		cssparse.Format.pop()
		print '%u/%u tests passed%s' % (passed, len(self.tests),
			', %u skipped' % len(self.skipped) if self.skipped else '')

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
	# run unit tests
	for root, dirs, files in os.walk(CSSUnitTests.PATH):
		for d in dirs:
			print '%s...' % (d,)
			t = CSSUnitTests(d)
			t.test()
