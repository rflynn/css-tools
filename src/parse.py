#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
CSS parser
"""

from simpleparse.common import numbers, strings, comments
from simpleparse.parser import Parser
from sys import stdin
import fcntl, os, sys

class AstNode:
	def __init__(self, s, tag, start, end, child):
		self.tag = tag
		self.start = start
		self.end = end
		self.str = s[start:end]
		self.child = child
	def __str__(self):
		if self.child:
			return '%s(%s)' % (self.tag, str(self.child))
		else:
			return self.str
	def __repr__(self): return str(self)
	def dump(self, indent=0):
		ins = ' ' * indent
		if self.child:
			return ins + '%s:\n' % (self.tag,) + \
				''.join([c.dump(indent+1) for c in self.child])
		else:
			return ins + self.str + '\n'
	@staticmethod
	def make(matches, s):
		nodes = []
		for tag, start, end, child in matches:
			n = AstNode(s, tag, start, end,
				AstNode.make(child, s) if child else [])
			nodes.append(n)
		return nodes 
	@staticmethod
	def Empty():
		return AstNode('','',0,0,[])

CSS_EBNF = r'''
css      := toplevel*
toplevel := rule/s
rule     := sels?,block
sels     := sel,(s?,',',s?,sel)*,s?
sel      := sel_tagop, (s?, sel_tagop)*
sel_tagop:= (sel_tag, sel_op?) / (sel_tag?, sel_op)
sel_tag  := ident/sel_univ
sel_univ := '*'
sel_op   := sel_class/sel_id/sel_psuedo/sel_child/sel_adj/sel_attr
sel_class:= '.',sel_tag
sel_id   := '#',sel_tag
sel_psuedo:=':',sel_tag
sel_child:= '>',sel_tag
sel_adj  := '+',sel_tag
sel_attr := '[',sel_tag,']'
block    := '{',s?,decls,s?,'}'
decls    := decl?,(s?,';',s?,decl)*,s?,';'?
decl     := property,s?,':',s?,values
property := name
values   := value,(s?,value)*,s?
value    := any/block
any      := percent/dim/hash/expr/uri/string/filter/ident/num/inc/bareq/delim
percent  := num,'%'
dim      := (num,ident),('/',num,ident)*
hash     := '#',hex+
uri      := url
url      := ('url(',urlchars,')')
urlchars := urlchar*
urlchar  := [a-zA-Z0-9~`!@#$%^&*_+{}[|:,./?-]
# FIXME: can't get character class hex escape ranges to work...
#urlchar  := [\x09\x21\x23-\x26\x27-\x7E] / nonascii / escape
filter   := filtername, space?, '(', space?, filterkvs?, space?, ')'
filtername:= name, (':', name)*, ('.', name)*
filterkvs:= filterkvs2
filterkvs2:= filterkv, (space?, ',', space?, filterkv)*
filterkv := name, '=', sqstring
sqstring := "'", sqchars, "'"
sqchars  := -"'"*
string   := '"',chars,'"'
chars    := -'"'*
inc      := '=~'
bareq    := '|='
ident    := ident2
ident2   := [-]?,name
nonascii := [\x80-\xD7FF\xE000-\xFFFD\x10000-\x10FFFF]
escape   := unicode / ('\\', [\x20-\x7E\x80-\xD7FF\xE000-\xFFFD\x10000-\x10FFFF])
unicode  := '\\', hex, hex?, hex?, hex?, hex?, hex?, wc?
wc       := [\x9\xA\xC\xD\x20]
num      := number
number   := [-]?,[0-9]+,('.',[0-9]+)?
delim    := delimiter
delimiter:= '!'/','
expr     := 'expression(', space?, exprexpr?, space?, ')'
exprexpr := exprterm, (space?, exprop)*
exprop   := exprbinop, space?, exprexpr
exprterm := num / exprstr / ('(', space?, exprexpr?, space?, ')') / exprcall / exprident
exprcall := exprident, '(', space?, exprexpr?, space?, ')'
exprident:= name, ('.', name)*
exprstr  := "'", -"'"*, "'"
exprbinop:= '+' / '-' / '*' / '/' / '||' / '&&'
exprsinop:= '+' / '-'
exprparen:= '(', space?, exprexpr, space?, ')'
name     := [a-zA-Z_-],[a-zA-Z0-9_-]*
hex      := [0-9a-fA-F]
s        := space/comment
space    := [ \t\r\n\v\f]+
comment  := '/*', commtext, '*/'
commtext := -"*/"*
'''

class Format:
	"""Options for CSS formatting"""
	IndentChar = '\t'
	IndentSize = 1
	Indent = IndentChar * IndentSize
	class Spec:
		OpSpace = True
	class Block:
		Indent = True
	class Decl:
		class Property:
			LeadingSpace = True
		class Value:
			LeadingSpace = False
		LastSemi = False

class TopLevel:
	def __init__(self, ast):
		self.ast = ast
		self.contents = TopLevel.make(ast)
	def __repr__(self):
		return str(self.contents)
	@staticmethod
	def make(ast):
		if ast.tag == 'rule':
			return Rule(ast)
		elif ast.tag == 's':
			if ast.child[0].child:
				return Comment(ast)
			else:
				return Whitespace(ast)
	def format(self):
		return self.contents.format()

class Rule:
	def __init__(self, ast):
		print 'Rule ast=', ast
		print 'Rule tag=', ast.child[0].tag
		if ast.child[0].tag == 'sels':
			self.sels = Sels(ast.child.pop(0))
		else:
			self.sels = Sels.Empty()
		self.decls = Decls(ast.child[0])
	def __repr__(self):
		return 'Rule(%s,%s)' % (self.sels, self.decls)
	def format(self):
		selstr = self.sels.format()
		if selstr:
			selstr += ' '
		return selstr + self.decls.format(1)

class Comment:
	def __init__(self, ast):
		self.ast = ast
		c = ast.child[0]
		self.text = c.child[0].str if c.child else ''
	def __repr__(self):
		return 'Comment(%s)' % (self.text,)
	def format(self):
		return '/*%s*/' % (self.text,)

class Whitespace:
	def __init__(self, ast):
		self.ast = ast
	def __repr__(self):
		return self.ast.child[0].str
	def format(self):
		return str(self)

class Sels:
	def __init__(self, ast):
		print 'Sels ast=', ast
		self.sel = map(Sel, ast.child)
	def __repr__(self):
		return 'Sels(' + ','.join(map(str,self.sel)) + ')'
	def format(self):
		return ', '.join(s.format() for s in self.sel)
	@staticmethod
	def Empty():
		# fudge an empty Sels
		return Sels(AstNode.Empty())

class Sel:
	def __init__(self, ast):
		print 'Sel ast=', ast
		self.sel = map(Sel.make, filter_space(ast.child))
	def __repr__(self):
		return 'Sel(' + ','.join(map(str,self.sel)) + ')'
	@staticmethod
	def make(ast):
		print 'Sel.make ast=', ast
		skip_tagop = ast.child[0]
		if skip_tagop.tag == 'sel_tag':
			return Sel_Tags(skip_tagop)
		return Sel_Ops(ast)
	def format(self):
		return ' '.join(s.format() for s in self.sel)

# strip whitespace and comments
def filter_space(l): return filter(lambda c: c.tag not in ('s','comment'), l)

class Sel_Tags:
	def __init__(self, ast):
		# save tag idents, strip spaces/comments
		print 'Sel_Tags=', filter_space(ast.child)
		self.tags = map(Sel_Tags.make, (c for c in filter_space(ast.child)))
	def __repr__(self):
		return 'Sel_Tags(' + str(self.tags) + ')'
	def format(self):
		return ''.join(t.format() for t in self.tags)
	@staticmethod
	def make(ast):
		print 'Sel_Tags.make ast=', ast
		if ast.str == '*':
			return '*'
		return Ident(ast)

class Sel_Ops:
	def __init__(self, ast):
		print 'Sel_Ops ast=', ast
		self.ast = ast
		self.op = map(Sel_Op, ast.child)
	def __repr__(self):
		return 'Sel_Ops(' + str(self.op) + ')'
	def format(self):
		return ''.join(o.format() for o in self.op)

class Sel_Op:
	CLASS  = 1
	ID     = 2
	PSUEDO = 3
	CHILD  = 4
	ADJ    = 5
	ATTR   = 6
	def __init__(self, ast):
		print 'Sel_Op ast=', ast
		self.ast = ast
		c = ast.child[0]
		self.tag = c.tag
		print 'Sel_Op tag=', self.tag
		if c.tag == 'sel_class':	self.op = Sel_Op.CLASS
		elif c.tag == 'sel_id':		self.op = Sel_Op.ID
		elif c.tag == 'sel_psuedo':	self.op = Sel_Op.PSUEDO
		elif c.tag == 'sel_child':	self.op = Sel_Op.CHILD
		elif c.tag == 'sel_adj':	self.op = Sel_Op.ADJ
		elif c.tag == 'sel_attr':	self.op = Sel_Op.ATTR
		self.s = c.child[0].child[0].child[0].str
	def __repr__(self):
		return 'Sel_Op(%s)' % (self.format(),)
	def format(self):
		s = ''
		if self.op == Sel_Op.CLASS:	s = '.'  + self.s
		elif self.op == Sel_Op.ID:	s = '#'  + self.s
		elif self.op == Sel_Op.PSUEDO:	s = ':'  + self.s
		elif self.op == Sel_Op.CHILD:	s = '> ' + self.s
		elif self.op == Sel_Op.ADJ:	s = '+ ' + self.s
		elif self.op == Sel_Op.ATTR:	s = '['  + self.s + ']'
		return s

class Decls:
	def __init__(self, ast):
		print 'Decls ast=', ast
		self.decl = map(Decl, ast.child[0].child)
	def __repr__(self):
		return 'Decls(' + ','.join(map(str,self.decl)) + ')'
	def format(self, indent_level=0):
		return '{' + \
			'; '.join(d.format(indent_level) for d in self.decl) + \
			(';' if Format.Decl.LastSemi else '') + \
			'}'

class Decl:
	def __init__(self, ast):
		print 'Decl ast=', ast
		prop,vals = ast.child
		self.property = prop.str
		self.values = map(Value, filter_space(vals.child))
	def __repr__(self):
		return 'Decl(%s:%s)' % (self.property, self.values)
	def format(self, indent_level):
		return self.property + ':' + \
			(' ' if Format.Decl.Value.LeadingSpace else '') + \
			' '.join(v.format() for v in self.values)

class Value:
	def __init__(self, ast):
		self.v = Value.make(ast)
	def __repr__(self):
		return 'Value(%s)' % (self.v,)
	def format(self):
		return self.v.format()
	@staticmethod
	def make(ast):
		v = ast.child[0]
		if v.tag != 'any':
			print 'ast=', ast
			raise Exception('unsupported')
		x = v.child[0]
		if x.tag == 'ident':	return Ident(x)
		elif x.tag == 'num':	return Number(x)
		elif x.tag == 'percent':return Percent(x)
		elif x.tag == 'string':	return String(x)
		elif x.tag == 'hash':	return Hash(x)
		elif x.tag == 'dim':	return Dimension(x)
		elif x.tag == 'delim':	return Delim(x)
		elif x.tag == 'expr':	return Expression(x)
		elif x.tag == 'uri':	return Uri(x)
		elif x.tag == 'filter':	return Filter(x)
		print 'Value.make.x=', x
		assert False
		return ast

class Ident:
	def __init__(self, ast):
		self.s = ast.child[0].str
	def __repr__(self):
		return 'Ident(%s)' % (self.s,)
	def format(self):
		return self.s

class Number:
	def __init__(self, ast):
		self.s = ast.child[0].str
		self.f = float(self.s)
	def __repr__(self):
		return 'Num(%s)' % (self.s,)
	def format(self):
		return self.s

class Percent:
	def __init__(self, ast):
		self.s = ast.child[0].str
		self.f = float(self.s)
	def __repr__(self):
		return 'Percent(%s%%)' % (self.s,)
	def format(self):
		return self.s + '%'

class Dimension:
	def __init__(self, ast):
		self.ast = ast
	def __repr__(self):
		return 'Dimension(%s)' % (self.ast,)
	def format(self):
		return str(self.ast)

class String:
	def __init__(self, ast):
		self.s = ast.child[0].str
	def __repr__(self):
		return self.s
	def format(self):
		return self.s

class Delim:
	def __init__(self, ast):
		self.s = ast.str
	def __repr__(self):
		return 'Delim(%s)' % (self.s,)
	def format(self):
		return self.s

class Hash:
	def __init__(self, ast):
		self.s = ast.str
	def __repr__(self):
		return 'Hash(%s)' % (self.s,)
	def format(self):
		return self.s

class Expression:
	def __init__(self, ast):
		self.s = ast.str
	def __repr__(self):
		return 'Expression(%s)' % (self.s,)
	def format(self):
		return self.s

class Uri:
	def __init__(self, ast):
		self.s = ast.str
	def __repr__(self):
		return 'Uri(%s)' % (self.s,)
	def format(self):
		return self.s

class Filter:
	def __init__(self, ast):
		self.s = ast.str
	def __repr__(self):
		return 'Filter(%s)' % (self.s,)
	def format(self):
		return self.s

parser = Parser(CSS_EBNF)

CSS_TESTS = [
	'/**/',
	'/***/',
	'/****/',
	'/*/*/',
	"{}",
	"{;}",
	'* html{}',
	'html .jqmWindow{}',
	"""#under_scores a{color:#000;}""",
	#'a,b{c:d;e:f}',
	'a b.c{d:e}',
	#'*.b.c.d{c:d}',
	#'a{b:c}d{e:f}',
	'a{b:c}\r\nd{e:f}',
	"{hash:#333}",
	"""{string:""}""",
	"""{empty-url:url()}""",
	"""{a-url:url(a)}""",
	"""{foo-url:url(http://foo)}""",
	#'h1,h2{font-family:Arial,Heletica,sans-serif}',
	'body{background-position:center 118px !important;font:normal 13px/1.2em Arial, Helvetica, sans-serif;margin:0;padding:0;}',
	'a:hover{text-decoration:underline;}', # psuedo class
	'span.ns{text-indent:-9000px;a:b}', # negative numbers
	"""span.ns{display:block;text-indent:-9000px;width:1px;}
	.lc{text-transform:none;}""",
	""".jqmWindow{top:30%;left:50%;background-color:#fff}""",
	"""expr-empty{foo:expression();}""",
	"""{foo:expression(a);}""",
	"""{foo:expression(a+b);}""",
	"""{foo:expression(a+'s');}""",
	"""{foo:expression(a.b+'s');}""",
	"""{foo:expression((a+b));}""",
	"""{foo:expression(a||b);}""",
	"""{foo:expression(a+b+c);}""",
	"""{foo:expression(a+(b+c));}""",
	"""{foo:expression((a+b)+c);}""",
	"""{foo:expression( ( a + b ) + c );}""",
	"""{foo:expression(funcall());}""",
	"""{foo:expression(funcall(2+2)+'');}""",
	"""{foo:expression((a||b)+Math.round(1*(c||d)/1)+'e');}""",
	"""#foo .bar a,#baz .closeb a{background-color:inherit;color:#fff;}""",
	"""-sh-linkedin .-sh-but a{}""",
	""".-sh-iwiw .-sh-but a{background-position:-112px -48px;}""",
	"""#selector_attributes .title[class] h3,#foo #Bar #baz .title[class] h3{background:url(http://image.png) no-repeat;}""",
	"""{filter:progid()}""",
	"""filter-yay{filter:progid:DXImageTransform.Microsoft.AlphaImageLoader()}""",
	"""filter-yay{filter:progid:DXImageTransform.Microsoft.AlphaImageLoader(enabled='true')}""",
	"""filter-yay{filter:progid:DXImageTransform.Microsoft.AlphaImageLoader(enabled='true', sizingMethod='img',src='http://image.jpg')}""",
]

# read from stdin if it's available
try:
	fcntl.fcntl(0, fcntl.F_SETFL, os.O_NONBLOCK) # stdin non-blocking
	foo = stdin.read()
	CSS_TESTS = [foo]
except:
	pass

# looks like simpleparse module is breaking occasionally, try to catch it...
# Ref: http://code.activestate.com/recipes/65287-automatically-start-the-debugger-on-an-exception/
def info(type, value, tb):
   if hasattr(sys, 'ps1') or not sys.stderr.isatty():
      # we are in interactive mode or we don't have a tty-like
      # device, so we call the default hook
      sys.__excepthook__(type, value, tb)
   else:
      import traceback, pdb
      # we are NOT in interactive mode, print the exception...
      traceback.print_exception(type, value, tb)
      print
      # ...then start the debugger in post-mortem mode.
      pdb.pm()

sys.excepthook = info

prod = 'css'
for t in CSS_TESTS:
	print 'input=', t[:200], '...' if len(t) >= 200 else ''
	ok, child, nextchar = parser.parse(t, production=prod)
	assert ok and nextchar == len(t), \
			"""Wasn't able to parse "%s..." as a %s (%s chars parsed of %s), returned value was %s""" % (
			repr(t)[max(0,nextchar-1):nextchar+100], prod, nextchar, len(t), (ok, child[-1] if child else child, nextchar))
	ast = AstNode.make(child, t)
	print 'ast=', ast
	top = [TopLevel(a.child[0]) for a in ast]
	print 'parse tree=', top
	print 'format=', [t.format() for t in top]
	print '**************************'

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

