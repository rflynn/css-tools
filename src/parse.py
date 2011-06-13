#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
CSS Parser and evaluator
"""
import re
import lepl
from lepl import *

ParseMe = """
/* COMMENTS CANNOT BE NESTED */

"""
"""
.empty-class { }
#bg-id { background-color:#ccc }
a:link, a:visited { color:Purple }
A:active  { color: blue; font-size: 125% }
BODY { background: url(bar.gif) white;
       background-repeat: repeat-x ! important }
code.html { color: #191970 }
P EM { background: yellow }
H1, H2, H3, H4, H5, H6 {
  color: red;
  font-family: sans-serif }
* {color: #bb0; } /* universal selector */
p > * > em {font-size: larger; } /* child combinator */
@import "style.css";
/* CSS2 attribute selectors */
/* Ref: http://www.yourhtmlsource.com/stylesheets/advancedselectors.html */
a[href="http://www.yourhtmlsource.com/"] {font-weight: bold; }
a[title~="Mail"] {text-decoration: none; }
p[align="right"][class="intro"] {line-height: 1.8em; }
input:focus:hover {background: gold; }
div#intro p:first-child {font-size: 110%; }
blockquote p:nth-child(5) {color: gold; }
table tr:nth-child(2n+1) td {background: silver; }
div#content p:first-child::first-line {text-transform: uppercase; }
"""

class Comment(List): pass
class AtKeyword(List): pass
class AtRule(List): pass
class Any(List): pass
class Number(List): pass
class Percentage(List): pass
class Dimension(List): pass
class String_(List): pass
class Uri(List): pass
class Hash(List): pass
class Includes(List): pass
class DashMatch(List): pass
class UnicodeRange(List): pass
class Property(List): pass
class Values(List): pass
class Decl(List): pass
class Decls(List): pass
class SelTag(List): pass
class SelClass(List): pass
class SelId(List): pass
class SelUniv(List): pass
class SelAttr(List): pass
class SelAttrEq(List): pass
class SelAttrInc(List): pass
class SelAttrDash(List): pass
class SelPsuedoClass(List): pass
class SelChild(List): pass
class SelAdjSibling(List): pass
class Selector(List): pass
class Selectors(List): pass
class Ruleset(List): pass

# Ref: http://www.w3.org/TR/CSS2/syndata.html#syntax

commentbody = Token('[^\*]+') | Token('[\*]')
# 'b' so matching '*' in */ will backtrack
comment = ~Token('/\*') & commentbody[::,...] & ~Token('\*/') > Comment

CDO = Token('<!--')
CDC = Token('-->')

IDENT_ = Token('\-?[a-zA-Z_][a-zA-Z0-9_\-]*')
NAME = Token('[a-zA-Z_][a-zA-Z0-9_\-]*')
SYMBOL = Token('[^0-9a-zA-Z \t\r\n]')

NUMBER = Token(Integer()) & Optional(Token('\.') & Token(Integer())) > Number
PERCENTAGE = And(NUMBER, Token('%')) > Percentage
DIMENSION = (NUMBER & IDENT_)[1:,~SYMBOL('/')] > Dimension
stringbody = Token(r'[^"]*')
STRING_ = SYMBOL('"') & Optional(stringbody) & SYMBOL('"') > String_
url = Token('http://')#'(?:[a-z]+:)?/[^\)]*')
URI = ~Token('url\(') & Optional(url) & ~SYMBOL(')') > Uri
HASH = ~SYMBOL('#') & NAME > Hash
ATKEYWORD = SYMBOL('@') & IDENT_ > AtKeyword
INCLUDES = SYMBOL('=~') > Includes
DASHMATCH = SYMBOL('|=') > DashMatch
UNICODE = Token('[0-9a-f][0-9a-f]?[0-9a-f]?[0-9a-f]?[0-9a-f]?[0-9a-f]?')
UNICODE_RANGE = (~Token('u\+') & UNICODE & Optional(SYMBOL('-') & UNICODE)) > UnicodeRange
DELIM = (SYMBOL('!') | SYMBOL(','))

def sane_error(s, e):
	lineno, offset = map(int, re.search('line (\d+), character (\d+)', str(e)).groups(0))
	lines = re.split('\r?\n', s)
	line = lines[lineno-1]
	linenostr = 'line %u: ' % (lineno,)
	print '%s%s' % (linenostr, line.rstrip())
	print '%s^-- %s' % (' ' * (len(linenostr) + offset - 1), e)

"""
from logging import basicConfig, DEBUG
basicConfig(level=DEBUG)
"""

import sys

S = Token('[ \r\n\t\v\f]')
with DroppedSpace(S[:]):
	any = PERCENTAGE | DIMENSION | URI | HASH | INCLUDES | DASHMATCH | IDENT_ | NUMBER | DELIM | SYMBOL(':') > Any #STRING_ #| FUNCTION S* [any|unused]* ')' > Any
	# FIXME: UNICODE_RANGE breaks shit, why?!
	# Ref: http://www.w3.org/TR/CSS2/selector.html#pattern-matching
	sel_univ = ~SYMBOL('*') > SelUniv
	sel_attrval = IDENT_# | STRING_
	sel_attr_eq = ~SYMBOL('=') & sel_attrval > SelAttrEq
	sel_attr_inc = ~INCLUDES & sel_attrval > SelAttrInc
	sel_attr_dash = ~DASHMATCH & sel_attrval > SelAttrDash
	sel_attrbody = IDENT_ & Optional(sel_attr_eq | sel_attr_inc | sel_attr_dash)
	sel_attr = ~SYMBOL('[') & sel_attrbody & ~SYMBOL(']') > SelAttr
	sel_psuedoclass = ~SYMBOL(':') & IDENT_ > SelPsuedoClass
	sel_class = ~SYMBOL('.') & IDENT_ > SelClass
	sel_id = ~SYMBOL('#') & IDENT_ > SelId
	sel_tag = Optional(sel_univ) & (((Optional(IDENT_) & (sel_class | sel_id)) | IDENT_) & Optional(sel_psuedoclass) & Optional(sel_attr) > SelTag)
	sel_tags = sel_tag[1:]
	sel_child = ~SYMBOL('>') & sel_tags > SelChild
	sel_adjsibling = SYMBOL('+') & sel_tags > SelAdjSibling
	sel_ops = sel_child | sel_adjsibling
	selector = sel_tags & Optional(sel_ops) > Selector
	selectors = selector[1:,SYMBOL(',')]

	property = IDENT_
	block = Delayed()
	value = (any | block)
	values = value[1:] > Values
	declaration = (property & ~Optional(S) & ~SYMBOL(':') & ~Optional(S) & values) > Decl
	declarations = declaration[:,~SYMBOL(';')] + Optional(~SYMBOL(';')) > Decls
	block += ~SYMBOL('{') & declarations & ~SYMBOL('}')
	ruleset = (Optional(selectors) & block & ~Optional(S)) > Ruleset
	at_rule = (ATKEYWORD & ~Optional(S) & Optional(any) & (block | Token(';') & ~Optional(S))) > AtRule
toplevel = ruleset # comment and ruleset both work great, except together. why?!
stylesheet = toplevel[:]

for s in [
		#'h1.big-text{a:b; c:1; d:100%; e:5px; f:string_doesnt_work; g:url(); h:#hash; border-width: -1px 2px 3px 4px;u:u+0;u2:u+012345-67890a;}',
		#'/**/',
		#'/* */',
		#'/***/',
		#'/****/',
		'h1,h2{x:y}',
		'*.foo{x:y}',
		'a:link{a:b}',
		'* a:link{a:b}',
		'P#id > a:link{a:b}',
		'a * b{a:b}',
		'a[b]{a:b}',
		'a[b=c]{a:b}',
		'#a #b a{}',
		'a{font-family:Arial, Helvetica, sans-serif;}',
		'a{font:normal 1px/2.0px Arial;}',
		'a{font:normal 1px/2em Arial;}',
		'a{font:normal 1px/2.0em Arial;}',
		#'@import;',
		#sys.stdin.read()
		]:
	try:
		ast = stylesheet.parse(s)
		for a in ast:
			print a
	except lepl.stream.maxdepth.FullFirstMatchException, e:
		sane_error(s, e)
		exit(1)

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

