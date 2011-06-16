#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
CSS parser
"""

from simpleparse.parser import Parser
from itertools import chain
from sys import stdin
import fcntl, os, sys

from ast import AstNode

# TODO: rgb(r,g,b[,a])
# TODO: hsl(%,%,%)
# TODO: hsla(%,%,%,0.0)
CSS_EBNF = r'''
css      := toplevel*
toplevel := rule/s
rule     := sels?,block
sels     := sel,(s?,',',s?,sel)*,s?
sel      := sel_tagop,(s?,sel_tagop)*
sel_tagop:= (sel_tag,sel_op?)/(sel_tag?,sel_op)
sel_tag  := ident/sel_univ
sel_univ := '*'
sel_op   := sel_class/sel_id/sel_psuedo/sel_child/sel_adj/sel_attr
sel_class:= '.',sel_tag
sel_id   := '#',sel_tag
sel_psuedo:=':',sel_tag
sel_attr := '[',sel_tag,']'
sel_child:= '>',s?,sel_tag
sel_adj  := '+',s?,sel_tag
block    := '{',s?,decls,s?,'}'
decls    := decl?,(s?,';',s?,decl?)*,s?,';'?
decl     := property,s?,':',s?,values
property := name
values   := value,(s?,value)*,s?
value    := any/block
any      := percent/dim/hash/expr/uri/string/filter/ident/num/inc/bareq/delim
percent  := num,'%'
# FIXME: wrong, dimensons are scalar; you were looking at font-size/line-height; '/' is a delimiter
dim      := (num,ident),('/',num,ident)*
hash     := '#',hex+
uri      := url
url      := ('url(',urlchars,')')
urlchars := [a-zA-Z0-9~`!@#$%^&*_+{}[|:,./?-]*
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
# NOTE: simpleparse only gives you the identity of the token if you abstract one layer, wtf
ident2   := [-]?,[a-zA-Z_-],[a-zA-Z0-9_-]*
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
	Minify = False
	Unmodified = False
	Stack = []
	class Indent:
		Char = '\t'
	class Spec:
		OpSpace = True
	class Block:
		Indent = True
	class Decl:
		class Property:
			LeadingSpace = True
		class Value:
			LeadingSpace = False
		LastSemi = True
		OnePerLine = True
		NewLine = '\r\n' # TODO: detect Windows/UNIX line endings
	@staticmethod
	def canonical():
		Format.Stack.append('canonical')
		Format.Minify = False
		Format.Spec.OpSpace = True
		Format.Block.Indent = True
		Format.Decl.Property.LeadingSpace = True
		Format.Decl.Value.LeadingSpace = True
		Format.Decl.LastSemi = True
		Format.Decl.OnePerLine = True
	@staticmethod
	def minify():
		Format.Stack.append('minify')
		Format.Minify = True
		Format.Spec.OpSpace = False
		Format.Block.Indent = False
		Format.Decl.Property.LeadingSpace = False
		Format.Decl.Value.LeadingSpace = False
		Format.Decl.LastSemi = False
		Format.Decl.OnePerLine = False
	@staticmethod
	def pop():
		# NOTE: intentionally raise exception if none were pushed
		last = Format.Stack.pop(0)
		if last == 'canonical':
			Format.canonical()
		elif last == 'minify':
			Format.minify()
		return last

# strip whitespace and comments
def filter_space(l): return filter(lambda c: c.tag not in ('s','comment'), l)

class CSSDoc:
	Parser = Parser(CSS_EBNF)
	def __init__(self, ast):
		self.ast = ast
		self.top = [TopLevel(a.child[0]) for a in ast]
		self.rules = [t.contents for t in self.top if isinstance(t.contents, Rule)]
	def __repr__(self): return ','.join(map(str, self.top))
	def format(self):
		return ''.join(t.format() for t in self.top).rstrip()
	@staticmethod
	def parse(text):
		prod = 'css'
		ok, child, nextchar = CSSDoc.Parser.parse(text, production=prod)
		if not ok or nextchar != len(text):
			raise Exception("""Wasn't able to parse "%s..." as a %s (%s chars parsed of %s), returned value was %s""" % (
				repr(text)[max(0,nextchar-1):nextchar+100], prod, nextchar, len(text), (ok, child[-1] if child else child, nextchar)))
		ast = AstNode.make(child, text)
		doc = CSSDoc(ast)
		return doc

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
		#print 'Rule ast:', ast
		#print 'Rule tag:', ast.child[0].tag
		if ast.child[0].tag == 'sels':
			self.sels = Sels(ast.child.pop(0))
		else:
			self.sels = Sels.Empty()
		self.decls = Decls.build(ast.child[0])
	def __repr__(self):
		return 'Rule(%s,%s)' % (self.sels, self.decls)
	def format(self):
		selstr = self.sels.format()
		if selstr and not Format.Minify:
			selstr += ' '
		nl = '\n' if not Format.Minify else ''
		return selstr + self.decls.format() + nl

class Comment:
	def __init__(self, ast):
		self.ast = ast
		c = ast.child[0]
		self.text = c.child[0].str if c.child else ''
	def __repr__(self):
		return 'Comment(%s)' % (self.text,)
	def format(self):
		return '/*' + self.text + '*/' if not Format.Minify else ''

class Whitespace:
	def __init__(self, ast):
		self.ast = ast
	def __repr__(self):
		s = self.ast.child[0].str
		return 'Whitespace(%s)' % (repr(s),)
	def format(self):
		if Format.Minify:
			return ''
		s = self.ast.child[0].str
		if not Format.Unmodified and s.count('\n') > 1:
			return '\n'
		return s

class Sels:
	def __init__(self, ast):
		#print 'Sels ast:', ast
		self.sel = map(Sel, filter_space(ast.child))
	def __repr__(self):
		return 'Sels(' + ','.join(map(str,self.sel)) + ')'
	def format(self):
		j = ',' + (' ' if not Format.Minify else '')
		return j.join(s.format() for s in self.sel)
	@staticmethod
	def Empty():
		# fudge an empty Sels
		return Sels(AstNode.Empty())

class Sel:
	def __init__(self, ast):
		#print 'Sel ast:', ast
		self.sel = map(Sel.build, filter_space(ast.child))
		#print 'Sel.sel:', self.sel
	def __repr__(self):
		return 'Sel(' + ','.join(map(str,self.sel)) + ')'
	def format(self):
		return ' '.join([''.join([s.format() for s in sel]) for sel in self.sel])
	def is_simple(self):
		"""is this selector free of complex operators?"""
		return False
	@staticmethod
	def build(ast):
		#print 'Sel.make ast:', ast
		skip_tagop = ast.child[0]
		#print 'Sel.make skip_tagop:', skip_tagop
		return [Sel_Tag(c) if c.tag == 'sel_tag' else Sel_Op(c)
			for c in ast.child]
	def __hash__(self):
		"""we want equality by value, not object, for dictionaries"""
		return hash(str(self))
	def __cmp__(self, other):
		return cmp(str(self), str(other))

class Sel_Tag:
	def __init__(self, ast):
		# save tag idents, strip spaces/comments
		#print 'Sel_Tag:', filter_space(ast.child)
		tag = filter_space(ast.child)[0]
		self.tag = tag.str
	def __repr__(self): return 'Sel_Tag(%s)' % (self.tag,)
	def format(self): return self.tag

class Sel_Op:
	CLASS  = 1
	ID     = 2
	PSUEDO = 3
	CHILD  = 4
	ADJ    = 5
	ATTR   = 6
	def __init__(self, ast):
		self.ast = ast
		c = ast.child[0]
		self.tag = c.tag
		if c.tag == 'sel_class':	self.op = Sel_Op.CLASS
		elif c.tag == 'sel_id':		self.op = Sel_Op.ID
		elif c.tag == 'sel_psuedo':	self.op = Sel_Op.PSUEDO
		elif c.tag == 'sel_child':	self.op = Sel_Op.CHILD
		elif c.tag == 'sel_adj':	self.op = Sel_Op.ADJ
		elif c.tag == 'sel_attr':	self.op = Sel_Op.ATTR
		self.s = list(filter_space(c.child))[0].child[0].child[0].str
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
	def __init__(self, decl):
		self.decl = decl
	def __repr__(self):
		return 'Decls(' + ','.join(map(str,self.decl)) + ')'
	def format(self):
		nd = Format.Indent.Char if Format.Block.Indent else ''
		nl = '\n' if Format.Block.Indent else ''
		le = ';' + nl
		return '{' + nl + \
			le.join(nd + d.format() for d in self.decl) + \
			(';' if Format.Decl.LastSemi and not Format.Minify else '') + nl + \
			'}'
	@staticmethod
	def build(ast):
		"""build Decls() from an AstNode"""
		#print 'Decls ast:', ast
		decls = list(filter_space(ast.child))[0].child
		#print 'Decls decls:', decls
		nospace = filter_space(decls)
		#print 'Decls nospace:', nospace
		decl = map(Decl, nospace)
		return Decls(decl)
	def __add__(self, other):
		return Decls(self.decl + other.decl)

class Decl:
	def __init__(self, ast):
		#print 'Decl ast:', ast
		nospace = list(filter_space(ast.child))
		prop,vals = nospace
		self.property = prop.str
		self.values = map(Value.make, filter_space(vals.child))
	def __repr__(self):
		return 'Decl(%s:%s)' % (self.property, self.values)
	def format(self):
		# decl values need spaces between them even in Minify, with a few exceptions
		valstr = self.values[0].format()
		prevNoSpace = False # set by values to tell next one it doesn't need a space
		for v in self.values[1:]:
			sp = ' '
			isDelim = Format.Minify and isinstance(v, Delim)
			if prevNoSpace or isDelim:
				sp = ''
			prevNoSpace = isDelim or isinstance(v, Uri)
			valstr += sp + v.format()
		return	self.property + ':' + \
			(' ' if Format.Decl.Value.LeadingSpace else '') + valstr
	def __eq__(self, other): return self.values == other.values

class Value:
	@staticmethod
	def make(ast):
		v = ast.child[0]
		if v.tag != 'any':
			print 'ast:', ast
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
		print 'Value.make.x:', x
		assert False
		return ast

class Ident:
	def __init__(self, ast): self.s = ast.child[0].str
	def __repr__(self): return 'Ident(%s)' % (self.s,)
	def format(self): return self.s
	def __eq__(self, other): return type(other) == Ident and self.s == other.s

class Number:
	def __init__(self, ast):
		self.s = ast.child[0].str
		self.f = float(self.s)
	def __repr__(self): return 'Num(%s)' % (self.s,)
	def format(self): return self.s
	def __eq__(self, other): return type(other) == Number and self.s == other.s

class Percent:
	def __init__(self, ast):
		self.s = ast.child[0].str
		self.f = float(self.s)
	def __repr__(self): return 'Percent(%s%%)' % (self.s,)
	def format(self): return self.s + '%'
	def __eq__(self, other): return type(other) == Percent and self.s == other.s

class Dimension:
	def __init__(self, ast):
		self.ast = ast
		# NOTE: dimension can contain multiple values for different units
		self.vals = []
		for i in range(0, len(ast.child), 2):
			n, u = ast.child[i:i+2]
			dim = (Number(n), Ident(u))
			self.vals.append(dim)
	def __repr__(self): return 'Dimension(%s)' % (self.vals,)
	def format(self): return '/'.join(n.format() + u.format() for n,u in self.vals)
	def __eq__(self, other): return type(other) == Dimension and self.vals == other.vals

class String:
	def __init__(self, ast): self.s = ast.child[0].str
	def __repr__(self): return self.s
	def format(self): return self.s
	def __eq__(self, other): return type(other) == String and self.s == other.s

class Delim:
	def __init__(self, ast): self.s = ast.str
	def __repr__(self): return 'Delim(%s)' % (self.s,)
	def format(self): return self.s
	def __eq__(self, other): return type(other) == Delim and self.s == other.s

class Hash:
	def __init__(self, ast):
		self.color = Color(ast.str)
	def __repr__(self): return 'Hash(%s)' % (self.color,)
	def format(self): return self.color.format()
	def __eq__(self, other): return type(other) == Hash and self.color == other.color

class Color:
	# Ref: http://www.w3.org/TR/CSS2/syndata.html#color-units
	KEYWORDS = {
		'maroon'  : '#800000',
		'red'     : '#ff0000',
		'orange'  : '#ffa500',
		'yellow'  : '#ffff00',
		'olive'   : '#808000',
		'purple'  : '#800080',
		'fuchsia' : '#ff00ff',
		'white'   : '#ffffff',
		'lime'    : '#00ff00',
		'green'   : '#008000',
		'navy'    : '#000080',
		'blue'    : '#0000ff',
		'aqua'    : '#00ffff',
		'teal'    : '#008080',
		'black'   : '#000000',
		'silver'  : '#c0c0c0',
		'gray'    : '#808080',
	}
	KEYWORDS_REV = dict((v,k) for k,v in KEYWORDS.items())
	def __init__(self, s):
		name, rgb3, rgb6 = None, None, None
		sl = s.lower()
		if sl in Color.KEYWORDS:
			name = s.lower()
			rgb6 = Color.KEYWORDS[name]
			s = rgb6
		if s[:1] == '#':
			if len(sl) == 7 and sl[1] == sl[2] and sl[3] == sl[4] and sl[5] == sl[6]:
				print '7'
				rgb6 = sl
				rgb3 = '#' + sl[1] + sl[3] + sl[5]
			elif len(s) == 4:
				rgb3 = sl
				rgb6 = '#' + (sl[1] * 2) + (sl[2] * 2) + (sl[3] * 2)
			if not name and rgb6 and rgb6 in Color.KEYWORDS_REV:
				name = Color.KEYWORDS_REV[rgb6]
		self.canonical = name if name else rgb6 if rgb6 else s
		self.shortest = name if (name and len(name) < 4) else rgb3 if rgb3 else name if name else s
	def __repr__(self):
		return 'Color(%s)' % (self.canonical,)
	def format(self):
		return self.shortest if Format.Minify else self.canonical
	def __eq__(self, other):
		return type(other) == Color and self.canonical == other.canonical

class Expression:
	def __init__(self, ast): self.s = ast.str
	def __repr__(self): return 'Expression(%s)' % (self.s,)
	def format(self): return self.s
	def __eq__(self, other): return type(other) == Expression and self.s == other.s

class Uri:
	def __init__(self, ast): self.s = ast.str
	def __repr__(self): return 'Uri(%s)' % (self.s,)
	def format(self): return self.s
	def __eq__(self, other): return type(other) == Uri and self.s == other.s

class Filter:
	def __init__(self, ast): self.s = ast.str
	def __repr__(self): return 'Filter(%s)' % (self.s,)
	def format(self): return self.s
	def __eq__(self, other): return type(other) == Filter and self.s == other.s

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

if __name__ == '__main__':

	sys.excepthook = info

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

	for t in CSS_TESTS:
		doc = CSSDoc.parse(t)
		print 'parse tree:', doc
		print doc.format()
		#print 'doc.rules:', doc.rules
