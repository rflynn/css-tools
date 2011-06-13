#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
find a python parsing tool that doesn't suck
"""

from simpleparse.common import numbers, strings, comments

declaration = r'''# note use of raw string when embedding in python code...
file           :=  [ \t\n]*, section+
section        :=  '[',identifier!,']'!, ts,'\n', body
body           :=  statement*
statement      :=  (ts,semicolon_comment)/equality/nullline
nullline       :=  ts,'\n'
equality       :=  ts, identifier,ts,'=',ts,identified,ts,'\n'
identifier     :=  [a-zA-Z], [a-zA-Z0-9_]*
identified     :=  string/number/identifier
ts             :=  [ \t]*
'''

from simpleparse.parser import Parser
parser = Parser( declaration)

testEquality = [
	"s=3\n",
	"s = 3\n",
	#'''"three\\nthree"\n''',
	'''  s=three\n''',
]

production = "equality"

for testData in testEquality:
	success, children, nextcharacter = parser.parse( testData, production=production)
	assert success and nextcharacter==len(testData), """Wasn't able to parse %s as a %s (%s chars parsed of %s), returned value was %s"""%( repr(testData), production, nextcharacter, len(testData), (success, children, nextcharacter))


