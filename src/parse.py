#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
CSS parser
"""

from simpleparse.common import numbers, strings, comments
from simpleparse.parser import Parser

class AstNode:
	def __init__(self, s, tag, start, end, children):
		self.tag = tag
		self.start = start
		self.end = end
		self.str = s[start:end]
		self.children = children
	def __str__(self):
		if self.children:
			return '%s(%s)' % (self.tag, str(self.children))
		else:
			return self.str
	def __repr__(self): return str(self)
	def dump(self, indent=0):
		ins = ' ' * indent
		if self.children:
			return ins + '%s:\n' % (self.tag,) + \
				''.join([c.dump(indent+1) for c in self.children])
		else:
			return ins + self.str + '\n'
	@staticmethod
	def make(matches, s):
		nodes = []
		for tag, start, end, children in matches:
			if tag not in ('s',):
				n = AstNode(s, tag, start, end,
					AstNode.make(children, s) if children else [])
				nodes.append(n)
		return nodes 

CSS_EBNF = r'''
css      := toplevel*
toplevel := rule/s
rule     := sels?,block
block    := '{',s?,decls,s?,'}'
sels     := sel,(s?,',',s?,sel)*,s?
decls    := decl?,(s?,';',s?,decl)*,s?,';'?
decl     := property,s?,':',s?,values
property := name
values   := value,(s?,value)*,s?
value    := any/block
any      := string/percent/dim/uri/hash/inc/bareq/ident/num/delim
string   := '"',[^"]*,'"'
percent  := num,'%'
dim      := (num,ident),('/',num,ident)*
uri      := 'url(',[^)]*,')'
hash     := '#',name
inc      := '=~'
bareq    := '|='
ident    := [-]?,name
num      := [0-9]+,([.],[0-9]+)?
delim    := '!'/','
name     := [a-zA-Z-],[a-zA-Z0-9-]*
sel      := sel_tags,sel_ops?
sel_tags := sel_tag,(s,sel_tag)*
sel_tag  := '*'/ident
sel_ops  := sel_child/sel_adj
sel_child:= '>',sel_tags
sel_adj  := '+',sel_tags
s        := whitespace/comment
space    := [ \t\r\n\v\f]+
comment  := '/*','*/'
'''

class Rule(AstNode):
	def __init__(self, ast):
		self.ast = ast
	def __repr__(self):
		return 'Rules:' + ''.join(map(str,self.ast.children))

parser = Parser(CSS_EBNF)

CSS_TESTS = [
	#'/**/',
	#'/***/',
	#'/* */',
	'a,b{c:d;e:f}',
	#'h1,h2{font-family:Arial,Heletica,sans-serif}',
	#'body{background-position:center 118px !important;font:normal 13px/1.2em Arial, Helvetica, sans-serif;margin:0;padding:0;}',
]

prod = 'css'
for t in CSS_TESTS:
	ok, children, nextchar = parser.parse(t, production=prod)
	assert ok and nextchar == len(t), "Wasn't able to parse %s as a %s (%s chars parsed of %s), returned value was %s" % (
			 repr(t), prod, nextchar, len(t), (ok, children, nextchar))
	#print children
	toplevel = AstNode.make(children, t)[0]
	rules = []
	#print ast
	print toplevel.children
	for c in toplevel.children:
		print c.tag
		if c.tag == 'rule':
			rules.append(Rule(c))
		#print a.dump()
	print rules

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


