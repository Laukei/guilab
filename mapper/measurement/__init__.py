#!user/bin/env python
# -*- coding: utf-8 -*-


import time
import random

def findClass(key):
	index = {
			'fakecounter':FakeCounter,
			'fakereflec':FakeLockIn,
			 }
	return index[key]

class Measurer:
	#superclass; features are vital for any controller implemented
	#be it counter or power meter or otherwise
	def __init__(self):
		pass

	def setDefaults(self):
		print 'Not implemented: initialise'

	def getMeasurement(self):
		print 'Not implemented: getMeasurement'

	def close(self):
		print 'Not implemented: close'
	
class FakeLockIn(Measurer):
	def setDefaults(self,meastime,pausetime):
		self.meastime = meastime
		self.pausetime = pausetime

	def getMeasurement(self):
		time.sleep(self.pausetime)
		time.sleep(self.meastime)
		return random.gauss(-0.8,0.1)

class FakeCounter(Measurer):
	def setDefaults(self,meastime,pausetime):
		self.meastime = meastime
		self.pausetime = pausetime

	def getMeasurement(self):
		time.sleep(self.pausetime)
		time.sleep(self.meastime)
		return random.gauss(3000,250)