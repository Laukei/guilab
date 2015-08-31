#!/usr/bin/env python
# -*- coding: utf-8 -*-

timeout = 500 #milliseconds
print 'WARNING: YOU ARE USING THE FAKE SIM900'
import random

class Sim900:
	def __init__(self,address):
		'''
		supply address (Sim900('ASRL1')) to connect to
		'''
		self.value = 5
		if address == 'ASRL1':
			self.device = True
		else:
			self.device = False

	def check(self):
		return self.device


	def write(self,module,command):
		print 'CONN '+str(module)+', "xyxxz" ; '+str(command)+' ; xyxxz'
		try:
			self.value = command[4:-2]
		except IndexError:
			self.value = 5

	def read(self,module):
		print 'CONN '+str(module)+', "xyxxz" ; READ_SOMETHING? ; xyxxz'
		return 'What were you expecting?'

	def query(self,module,command):
		print 'CONN '+str(module)+', "xyxxz" ; '+str(command)+' ; '+str(self.value)+' ; xyxxz'
		return float(self.value) + random.gauss(0,0.4)

	def clear(self):
		pass

	def close(self):
		pass