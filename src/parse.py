#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
CSS parser

Copyright 2011 Ryan Flynn <parseerror@gmail.com>
MIT licensed: http://www.opensource.org/licenses/mit-license.php
"""

from simpleparse.parser import Parser
from itertools import chain
from sys import stdin
import fcntl, os, sys

from ast import AstNode

# TODO: rgb(r,g,b[,a])
# TODO: hsl(%,%,%)
# TODO: hsla(%,%,%,0.0)
# TODO: support crazy CSS3 selectors http://www.w3.org/TR/css3-selectors/
CSS_EBNF = r'''
css      := toplevel*
toplevel := at_rule/rule/s
rule     := sels?,block
sels     := sel,(s?,',',s?,sel)*,s?
sel      := sel_ops,(s,sel_ops)*
sel_ops  := sel_op+
sel_op   := sel_tag/sel_class/sel_id/sel_psuedo/sel_child/sel_adj/sel_attr
sel_tag  := tag
sel_class:= '.',tag
sel_id   := '#',tag
sel_psuedo:=':',tag
sel_attr := '[',sel_attr_sel,']'
sel_attr_sel := tag,(sel_attr_op,sel_attr_val)?
sel_attr_val := any
sel_attr_op := '='
sel_child:= '>',s?,tag
sel_adj  := '+',s?,tag
tag      := ident/sel_univ
sel_univ := sel_univ2
sel_univ2:= '*'
at_rule  := at_kword,s,values?,';'?
at_kword := '@',ident
block    := '{',s?,decls,s?,'}'
decls    := decl?,(s?,';',s?,decl?)*,s?,';'?
decl     := property,s?,colon,s?,values
colon    := ':'
property := name
values   := value,(s?,value)*,s?
value    := any/block
any      := percent/dim/hash/expr/uri/string/sqstring/filter/propfunc/ident/num/inc/bareq/delim
percent  := num,'%'
dim      := num,ident
hash     := '#',hex+
uri      := url
url      := 'url(',urlstring?,')'
urlstring:= string/sqstring/urlchars
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
chars    := (('\\',[\000-\377])/-'"')*
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
delimiter:= '!'/','/'/'
propfunc := exprcall
expr     := 'expression(', space?, exprexpr?, space?, ')'
exprexpr := exprterm, (space?, exprop)*
exprop   := exprbinop, space?, exprexpr
exprterm := num / exprstr / ('(', space?, exprexpr?, space?, ')') / exprcall / exprident
exprcall := exprident, '(', space?, exprexpr?, (space?, ',', exprexpr)*, space?, ')'
exprident:= name, ('.', name)*
exprstr  := "'", -"'"*, "'"
exprbinop:= '+' / '-' / '*' / '/' / '||' / '&&'
exprsinop:= '+' / '-'
exprparen:= '(', space?, exprexpr, space?, ')'
# NOTE: IE prefix hack
name     := [*a-zA-Z_-],[\\a-zA-Z0-9_-]*
hex      := [0-9a-fA-F]
s        := (space/comment)+
space    := [ \t\r\n\v\f]+
comment  := '/*', commtext, '*/'
commtext := -"*/"*
'''

# TODO: disparate values like Percent and Dimension should __cmp__ equal
# if they're both '0'

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
		NewLine = '\n' # TODO: detect Windows/UNIX line endings
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
		Format.Stack.pop()
		if not Format.Stack:
			return None
		else:
			last = Format.Stack[-1]
			if last == 'canonical':
				Format.canonical()
			elif last == 'minify':
				Format.minify()
			return last

# strip whitespace and comments
def filter_space(l): return filter(lambda c: c.tag not in ('s','comment'), l)

def first_index(lst, pred):
    for i,v in enumerate(lst):
        if pred(v):
            return i
    return None

class CSSDoc:
	Parser = Parser(CSS_EBNF)
	def __init__(self, ast):
		self.ast = ast
		#print 'CSSDoc ast:', ast
		self.top = []
		for a in ast:
			#print 'a.child:', a.child
			if a.child[0].tag == 'rule':
				t = TopLevel(a.child[0])
				self.top.append(t)
			elif a.child[0].tag == 's':
				for s in a.child[0].child:
					t = TopLevel(s)
					self.top.append(t)
		#print 'CSSDoc top:', self.top
		self.atrules = []
		self.rules = []
		for t in self.top:
			if isinstance(t.contents, Rule):
				self.rules.append(t.contents)
			elif isinstance(t.contents, AtRule):
				self.atrules.append(t.contents)
	def __repr__(self): return ','.join(map(str, self.top))
	def format(self):
		nl = '' if Format.Minify else '\n'
		s = ''
		for t in self.top:
			if isinstance(t.contents, Comment) and Format.Minify and \
				(t.contents.text == '' or '\\' in t.contents.text):
				# assume browser-specific hack, preserve
				# see: test/minify/hack-ie5-mac-backslash.css
				txt = t.contents.text
				s += '/*' + txt[max(0, txt.find('\\')):] + '*/'
			else:
				s += t.format() + nl
		return s.strip()
	@staticmethod
	def parse(text):
		prod = 'css'
		ok, child, nextchar = CSSDoc.Parser.parse(text, production=prod)
		if not ok or nextchar != len(text):
			lineno = text[:nextchar].count('\n')
			line = text[:nextchar+256].split('\n')[lineno]
			raise Exception("""Line %u: %s\n\tparse error: "%s..." """ % (
				lineno, line, repr(text[nextchar:nextchar+256])))
		ast = AstNode.make(child, text)
		doc = CSSDoc(ast)
		return doc

class TopLevel:
	def __init__(self, ast):
		self.ast = ast
		self.contents = TopLevel.from_ast(ast)
	def __repr__(self):
		return str(self.contents)
	@staticmethod
	def from_ast(ast):
		#print 'TopLevel.from_ast ast:', ast
		if ast.tag == 'rule':
			return Rule.from_ast(ast)
		elif ast.tag == 'comment':
			return Comment.from_ast(ast)
		elif ast.tag.startswith('@'):
			return AtRule.from_ast(ast)
		else:
			return Whitespace.from_ast(ast)
	def format(self):
		return self.contents.format()

class AtRule:
	def __init__(self, ast, keyword, vals):
		self.ast = ast
		self.keyword = keyword
		self.vals = vals
	def __repr__(self): return 'AtRule(%s)' % str(self.ast)
	def format(self):
		return self.keyword.format() + ' ' + \
			' '.join([v.format() for v in self.vals]) + \
			(';' if not isinstance(self.vals[-1], Decls) else '')
	@staticmethod
	def from_ast(ast):
		c = filter_space(ast.child)[0]
		keyword = Ident.from_ast(c)
		#print 'AtRule.from_ast ast.child:', ast.child
		vals = map(Value.from_ast,
			filter_space(ast.child[2].child))
		return AtRule(ast, keyword, vals)

class Rule:
	def __init__(self, sels, decls):
		#print 'Rule ast:', ast
		#print 'Rule tag:', ast.child[0].tag
		self.sels = sels
		self.decls = decls
	def __repr__(self):
		return 'Rule(%s,%s)' % (self.sels, self.decls)
	def format(self):
		selstr = self.sels.format()
		if selstr and not Format.Minify:
			selstr += ' '
		return selstr + self.decls.format()
	@staticmethod
	def from_ast(ast):
		if ast.child[0].tag == 'sels':
			sels = Sels.from_ast(ast.child.pop(0))
		else:
			sels = Sels.Empty()
		decls = Decls.from_ast(ast.child[0])
		return Rule(sels, decls)

class Comment:
	def __init__(self, text):
		self.text = text
	def __repr__(self):
		return 'Comment(%s)' % self.text
	def format(self, preserve=False):
		return '/*' + self.text + '*/' if preserve or not Format.Minify or self.text.endswith('/*') else ''
	@staticmethod
	def from_ast(ast):
		return Comment(ast.child[0].str)

class Whitespace:
	def __init__(self, s):
		self.s = s
	def __repr__(self):
		return 'Whitespace(%s)' % repr(self.s)
	def format(self, forceshow=False):
		if forceshow:
			return self.s
		if Format.Minify:
			return ''
		if not Format.Unmodified and self.s.count('\n') > 1:
			return '\n'
		return self.s
	@staticmethod
	def from_ast(ast):
		return Whitespace(ast.str)

class Sels:
	def __init__(self, sel):
		#print 'Sels ast:', ast
		self.sel = sel
	def __repr__(self):
		return 'Sels(' + ','.join(map(str,self.sel)) + ')'
	def __len__(self):
		return sum(map(len, self.sel))
	def format(self):
		j = ',' + (' ' if not Format.Minify else '')
		return j.join(s.format() for s in self.sel)
	@staticmethod
	def from_ast(ast):
		sel = map(Sel.from_ast, filter_space(ast.child))
		return Sels(sel)
	@staticmethod
	def Empty():
		# fudge an empty Sels
		return Sels.from_ast(AstNode.Empty())

class Sel:
	def __init__(self, sel):
		#print 'Sel ast:', ast
		self.sel = sorted(sel)
		#print 'Sel.sel:', self.sel
		# FIXME: this is hideous
		Format.minify()
		f = self.format()
		Format.pop()
		self._len = len(f)
	def __repr__(self):
		return 'Sel(' + ','.join(map(str,self.sel)) + ')'
	def format(self):
		s = ''.join(s.format() for s in self.sel[0])
		for sel in self.sel[1:]:
			s2 = ''.join(s.format() for s in sel)
			if sel[0].op in (Sel_Op.TAG, Sel_Op.CLASS, Sel_Op.ID):
				# spaces only matter for these operators; the
				# rest can be omitted with no difference
				s += ' '
			s += s2
		return s
	def __len__(self):
		return self._len
	def is_simple(self):
		"""is this selector free of complex operators?"""
		return False
	@staticmethod
	def from_ast(ast):
		sel = map(Sel.from_ast_tagop, filter_space(ast.child))
		return Sel(sel)
	@staticmethod
	def from_ast_tagop(ast):
		#print 'Sel.from_ast ast:', ast
		skip_tagop = ast.child[0]
		#print 'Sel.from_ast skip_tagop:', skip_tagop
		return map(Sel_Op, ast.child)
	def __hash__(self):
		return hash(str(self))
	def __cmp__(self, other):
		return cmp(str(self), str(other))

class Sel_Op:
	TAG    = 1
	CLASS  = 2
	ID     = 3
	PSUEDO = 4
	CHILD  = 5
	ADJ    = 6
	ATTR   = 7
	def __init__(self, ast):
		self.ast = ast
		c = ast.child[0]
		self.tag = c.tag
		if c.tag == 'sel_tag':		self.op = Sel_Op.TAG
		elif c.tag == 'sel_class':	self.op = Sel_Op.CLASS
		elif c.tag == 'sel_id':		self.op = Sel_Op.ID
		elif c.tag == 'sel_psuedo':	self.op = Sel_Op.PSUEDO
		elif c.tag == 'sel_child':	self.op = Sel_Op.CHILD
		elif c.tag == 'sel_adj':	self.op = Sel_Op.ADJ
		elif c.tag == 'sel_attr':	self.op = Sel_Op.ATTR
		#print 'Sel_Op c.tag:', c.tag, 'c.child:', c.child
		args = list(filter_space(c.child))[0].child
		self.s = args[0].child[0].str
		self.sel_op = None
		self.operand = None
		if len(args) > 1:
			self.sel_op = args[1].str
			self.operand = Value.from_ast(args[2])
		#print 'Sel_Op self.s:', self.s
	def __repr__(self):
		return 'Sel_Op(%s)' % self.format()
	def format(self):
		s = self.s
		sp = '' if Format.Minify else ' '
		if self.op == Sel_Op.TAG:	s =        s
		elif self.op == Sel_Op.CLASS:	s = '.'  + s
		elif self.op == Sel_Op.ID:	s = '#'  + s
		elif self.op == Sel_Op.PSUEDO:	s = ':'  + s
		elif self.op == Sel_Op.CHILD:
			s = '>'
			try:
				c = self.ast.child[0].child[0].child[0]
				if c.tag == 'comment' and c.str == '/**/':
					# child selector hack, preserve comment
					# see test/minify/hack-ie-child-selector.css
					s += '/**/'
			except:
				pass
			s += sp + self.s
		elif self.op == Sel_Op.ADJ:	s = '+' + sp + s
		elif self.op == Sel_Op.ATTR:
			if self.sel_op:
				s += str(self.sel_op) + str(self.operand)
			s = '[' + s + ']'
		return s

class Decls:
	def __init__(self, decl):
		self.decl = list(decl)
	def __repr__(self):
		return 'Decls(' + ','.join(map(str,self.decl)) + ')'
	def format(self):
		nd = Format.Indent.Char if Format.Block.Indent else ''
		nl = '\n' if Format.Block.Indent else ''
		le = ';' + nl
		return '{' + nl + \
			((le.join(nd + d.format() for d in self.decl) +
			 (';' if (not isinstance(self.decl[-1].values[0], Decls)) and Format.Decl.LastSemi and not Format.Minify else '') + nl) \
				if self.decl else '') + '}'
	def __hash__(self):
		return hash(str(sorted(self.decl)))
	def __cmp__(self, other):
		return cmp(str(sorted(self.decl)), str(sorted(other.decl)))
	@staticmethod
	def from_ast(ast):
		"""build Decls() from an AstNode"""
		#print 'Decls ast:', ast
		decls = list(filter_space(ast.child))[0].child
		#print 'Decls decls:', decls
		nospace = filter_space(decls)
		#print 'Decls nospace:', nospace
		decl = map(Decl.from_ast, nospace)
		return Decls(decl)
	def __add__(self, other):
		return Decls(self.decl + other.decl)

class Decl:
	def __init__(self, property_, values, ast=None, post_prop_s='', pre_vals_s=''):
		self.ast = ast
		#print 'Decl ast:', ast
		self.property = property_
		self.propertylow = self.property.lower()
		self.post_prop_s = post_prop_s if post_prop_s else Whitespace('')
		self.pre_vals_s = pre_vals_s if pre_vals_s else Whitespace('')
		self.values = values
		self._str = None
	def __repr__(self):
		if not self._str:
			self._str = 'Decl(%s:%s)' % (self.property, self.values)
		return self._str
	def __len__(self):
		return len(self.property.format()) + \
			sum(len(v.format())+2 for v in self.values) - 1
	def format(self):
		# decl values need spaces between them even in Minify, with a few exceptions
		valstr = self.values[0].format()
		prevNoSpace = False # set by values to tell next one it doesn't need a space
		prev = None
		for v in self.values[1:]:
			# the rules for required inter-value spaces are a little tricky
			currNoSpace = isinstance(v, Delim) and (Format.Minify or not v.leading_space())
			prevNoSpace = prev and \
				((Format.Minify and \
					(isinstance(prev, Uri) or isinstance(prev, Delim)))
				 or (isinstance(prev, Delim) and not prev.trailing_space()))
			sp = '' if currNoSpace or prevNoSpace else ' '
			valstr += sp + v.format()
			prev = v
		return self.property + self.post_prop_s.format(True) + ':' + \
			self.pre_vals_s.format(True) + \
			(' ' if Format.Decl.Value.LeadingSpace else '') + valstr
	def __eq__(self, other):
		return self.propertylow == other.property and self.values == other.values
	def __hash__(self): return hash(str(self.propertylow))
	def __cmp__(self, other): return cmp(str(self), str(other))
	@staticmethod
	def from_ast(ast):
		"""generate a Decl from an AstNode"""
		#print 'Decl ast:', ast
		c = ast.child
		#print 'Decl c[1].child:', c[1].child
		prop_idx = first_index(c, lambda t: t.tag == 'property')
		col_idx = first_index(c, lambda t: t.str == ':')
		vals_idx = first_index(c, lambda t: t.tag == 'values')
		post_prop_s = None
		pre_vals_s = None
		#print 'prop_idx=%u col_idx=%u vals_idx=%u' % (prop_idx, col_idx, vals_idx)
		if col_idx == prop_idx+2 and c[col_idx-1].child:
			#print 'c[col_idx-1].str(%s)' % c[col_idx-1].str
			post_prop_s = Whitespace(c[col_idx-1].str)
		if vals_idx == col_idx+2 and c[col_idx+1].child:
			pre_vals_s = Whitespace(c[col_idx+1].str.strip())
		prop = ast.child[0]
		d = Decl(prop.str, [], ast, post_prop_s, pre_vals_s)
		d.values = map(Value.from_ast, filter_space(c[vals_idx].child))
		return d

class Value:
	@staticmethod
	def from_ast(ast):
		#print 'Value ast:', ast
		v = ast.child[0]
		if v.tag not in ('any', 'at_kword', 'block'):
			print 'ast:', ast
			raise Exception('unsupported: ' + str(v.tag))
		x = v.child[0]
		if x.tag == 'ident':
			c = x.child[0]
			if c.str.lower() in Color.KEYWORDS:
				return Color(c.str)
			return Ident.from_ast(c)
		elif x.tag == 'num':	return Number(x)
		elif x.tag == 'percent':return Percent(x)
		elif x.tag == 'string':	return String(x, '"')
		elif x.tag == 'sqstring':return String(x, "'")
		elif x.tag == 'hash':	return Hash(x)
		elif x.tag == 'dim':	return Dimension(x)
		elif x.tag == 'delim':	return Delim.from_ast(x)
		elif x.tag == 'expr':	return Expression(x)
		elif x.tag == 'propfunc':return Expression(x)
		elif x.tag == 'uri':	return Uri(x)
		elif x.tag == 'filter':	return Filter(x)
		elif x.tag == 'decls':	return Decls.from_ast(v)
		raise Exception('unexpected: Value.from_ast() x.tag: ' + x.tag)
		return ast

class Ident(object):
	def __init__(self, s): self.s = s
	def __repr__(self): return 'Ident(%s)' % self.s
	def format(self): return self.s
	def __cmp__(self, other): return cmp(str(self), str(other))
	@staticmethod
	def from_ast(ast): return Ident(ast.str)

class Number:
	def __init__(self, ast):
		self.s = ast.child[0].str
		self.f = float(self.s)
	def __repr__(self): return 'Number(%s)' % self.s
	def format(self): return self.s
	def __cmp__(self, other): return cmp(str(self), str(other))

class Percent:
	def __init__(self, ast):
		self.s = ast.child[0].str
		self.f = float(self.s)
	def __repr__(self): return 'Percent(%s%%)' % self.s
	def format(self):
		unit = '%'
		if Format.Minify and self.s == '0':
			unit = ''
		return self.s + unit
	def __cmp__(self, other): return cmp(str(self), str(other))

class Dimension:
	def __init__(self, ast):
		self.ast = ast
		n = ast.child[0]
		self.num = Number(n)
		u = ast.child[1] if len(ast.child) > 1 else ''
		self.unit = Ident.from_ast(u.child[0])
	def __repr__(self): return 'Dimension(%s,%s)' % (self.num, self.unit)
	def format(self):
		nf = self.num.format()
		uf = self.unit.format()
		# "After the '0' length, the unit identifier is optional."
		# Ref: http://www.w3.org/TR/css3-values/#lengths
		if Format.Minify and nf == '0':
			uf = ''
		return nf + uf
	def __cmp__(self, other): return cmp(str(self), str(other))

class String:
	def __init__(self, ast, q):
		self.q = q
		self.s = ast.child[0].str
	def __repr__(self): return self.q + self.s + self.q
	def format(self): return self.q + self.s + self.q
	def __cmp__(self, other): return cmp(str(self), str(other))

class Delim:
	def __init__(self, s): self.s = s
	def __repr__(self): return 'Delim(%s)' % self.s
	def format(self): return self.s
	def leading_space(self):
		return self.s in ('!',)
	def trailing_space(self):
		return self.s in (',',)
	def __cmp__(self, other): return cmp(str(self), str(other))
	@staticmethod
	def from_ast(ast):
		return Delim(ast.str)

class Hash:
	def __init__(self, ast):
		self.color = Color(ast.str)
	def __repr__(self): return 'Hash(%s)' % self.color
	def format(self): return self.color.format()
	def __cmp__(self, other): return cmp(str(self), str(other))

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
			name = sl
			rgb6 = Color.KEYWORDS[name]
			sl = rgb6
		if sl[:1] == "#":
			if len(sl) == 7 and sl[1] == sl[2] and sl[3] == sl[4] and sl[5] == sl[6]:
				rgb6 = sl
				rgb3 = '#' + sl[1] + sl[3] + sl[5]
			elif len(sl) == 4:
				rgb3 = sl
				rgb6 = '#' + (sl[1] * 2) + (sl[2] * 2) + (sl[3] * 2)
			if not name:
				if rgb6 and rgb6 in Color.KEYWORDS_REV:
					name = Color.KEYWORDS_REV[rgb6]
				else:
					name = s
		self.canonical = name if name else rgb6 if rgb6 else s
		self.shortest = name if name and len(name) < 4 else rgb3 if rgb3 else name
	def __repr__(self):
		return 'Color(%s)' % self.canonical
	def format(self):
		return self.shortest if Format.Minify else self.canonical
	def __cmp__(self, other): return cmp(str(self), str(other))

class Expression:
	def __init__(self, ast): self.s = ast.str
	def __repr__(self): return 'Expression(%s)' % self.s
	def format(self): return self.s
	def __cmp__(self, other): return cmp(str(self), str(other))

class Uri:
	def __init__(self, ast):
		self.ast = ast
		self.s = ast.child[0].child[0].child[0]
	def __repr__(self): return 'Uri(%s)' % self.s
	def format(self):
		url = self.s.str
		if Format.Minify \
			and self.s.tag in ('string','sqstring') \
			and url.find(')') == -1:
			url = url[1:-1]
		return 'url(%s)'  % url
	def __cmp__(self, other): return cmp(str(self), str(other))

class Filter:
	def __init__(self, ast): self.s = ast.str
	def __repr__(self): return 'Filter(%s)' % self.s
	def format(self): return self.s
	def __cmp__(self, other): return cmp(str(self), str(other))

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
	'a,b{c:d;e:f}',
	'a b.c{d:e}',
	'*.b.c.d{c:d}',
	'a{b:c}d{e:f}',
	'a{b:c}\r\nd{e:f}',
	"{hash:#333}",
	"""{string:""}""",
	"""{empty-url:url()}""",
	"""{a-url:url(a)}""",
	"""{foo-url:url(http://foo)}""",
	'h1,h2{font-family:Arial,Heletica,sans-serif}',
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
	"""filter-yay{filter:progid:DXImageTransform.Microsoft.AlphaImageLoader(enabled='true', sizingMethod='img',src='http://image.jpg')}""",
	'''@import "foo";''',
	'@import url();',
	'@import url("foo") bar, baz;',
	'@page foo;',
	"""input[type="radio"] { vertical-align: text-bottom; }""", # https://github.com/rflynn/css-tools/issues/1
    '.x { -webkit-transform:translate3d(0,0,0); }', # https://github.com/rflynn/css-tools/issues/5
	# TODO: support these constructs
	'''a[title="a not s\\
o very long title"] {/*...*/}''',
	'@media all and (min-width: 0px) { html:first-child selector { property: value; } }',
	'@-moz-document url-prefix() { selector { property: value; } }',
	'selector:not(:root:root) { property: value; }',
	]

	# read from stdin if it's available
	try:
		fcntl.fcntl(0, fcntl.F_SETFL, os.O_NONBLOCK) # stdin non-blocking
		foo = stdin.read()
		doc = CSSDoc.parse(foo)
		print 'ast:', doc.ast
		print 'parse tree:', doc
		print 'formatted:', doc.format()
		exit(0)
	except IOError:
		# nothing to read
		pass

	print 'Testing parser...'

	passed = 0
	for t in CSS_TESTS:
		try:
			doc = CSSDoc.parse(t)
			passed += 1
		except:
			print t
			print sys.exc_info()

	print 'Tests passed (%u/%u)' % (passed, len(CSS_TESTS))

