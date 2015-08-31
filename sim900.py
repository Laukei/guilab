#!/usr/bin/env python
# -*- coding: utf-8 -*-

import visa

timeout = 500 #milliseconds

class Sim900:
	def __init__(self,address):
		'''
		supply address (Sim900('ASRL1')) to connect to
		'''
		self.rm = visa.ResourceManager()
		try:
			self.device = self.rm.open_resource(address)
			self.device.timeout = timeout
		except visa.VisaIOError:
			self.device = False

	def check(self):
		return self.device

	def write(self,module,command):
		try:
			self.device.write('CONN '+str(module)+', "xyxxz"')
			self.device.write(command)
		except visa.VisaIOError as e:
			raise e
		finally:
			self.device.write('xyxxz')

	def read(self,module):
		try:
			self.device.write('CONN '+str(module)+', "xyxxz"')
			self.retstr = self.device.read().strip('\r\n')
		except visa.VisaIOError as e:
			raise e
		finally:
			self.device.write('xyxxz')
		return self.retstr

	def query(self,module,command):
		try:
			self.device.write('CONN '+str(module)+', "xyxxz"')
			self.device.write(command)
			self.retstr = self.device.read().strip('\r\n')
		except visa.VisaIOError as e:
			raise e
		finally:
			self.device.write('xyxxz')
		return self.retstr

	def clear(self):
		self.device.clear()

	def close(self):
		self.device.close()