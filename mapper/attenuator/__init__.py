#!/usr/bin/env python
# -*- coding: utf-8 -*-

import visa

timeout = 500 #milliseconds

class Attenuator:
	def __init__(self,address):
		'''
		supply address to connect to
		'''
		try:
			self.rm = visa.ResourceManager()
			self.device = self.rm.open_resource(address)
			self.device.timeout = timeout
		except visa.VisaIOError as e:
			self.device = str(e)
		except OSError as e:
			self.device = str(e)

	def check(self):
		return self.device

	def write(self,command):
		try:
			self.device.write(command)
		except visa.VisaIOError as e:
			raise e

	def read(self):
		try:
			self.retstr = self.device.read()
		except visa.VisaIOError as e:
			raise e
		return self.retstr

	def query(self,command):
		try:
			self.retstr = self.device.query(command)
		except visa.VisaIOError as e:
			raise e
		return self.retstr

	def clear(self):
		self.device.clear()

	def close(self):
		self.device.close()