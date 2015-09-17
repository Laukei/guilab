#!/usr/bin/env python
# -*- coding: utf-8 -*-

timeout = 500 #milliseconds
import random

class Attenuator:
	def __init__(self,address):
		'''
		supply address (Sim900('ASRL1')) to connect to
		'''
		print 'WARNING: YOU ARE USING THE FAKE ATTENUATOR'
		self.value = 20
		if address == 'ASRL1':
			self.device = True
		else:
			self.device = False

	def check(self):
		return self.device


	def write(self,command):
		print str(command)
		try:
			self.value = command[4:-2]
		except IndexError:
			self.value = 20

	def read(self):
		return 'What were you expecting?'

	def query(self,command):
		print str(command)
		return float(self.value)

	def clear(self):
		pass

	def close(self):
		pass