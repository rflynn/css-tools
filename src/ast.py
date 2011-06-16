#!/usr/bin/env python
# -*- coding:utf-8 -*-

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
			return repr(self.str)
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
	@staticmethod
	def Custom(s):
		return AstNode(s,s,0,max(0, len(s)-1),[])

