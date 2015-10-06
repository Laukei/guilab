#!user/bin/env python
# -*- coding: utf-8 -*-


import time
import random
import visa

timeout = 5000

def findClass(key=None):
	index = {
			'fakecounter':FakeCounter,
			'fakereflec':FakeLockIn,
			'universalcounter':UniversalCounter,
			'lockin':LockIn,
			 }
	if key == None:
		return index
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
	
class UniversalCounter(Measurer):
	devicetype = 'c'
	tests = {'c':  [[['tp','tm'],[0,2],'Time(s) out of bounds']]}
	def __init__(self,address='GPIB0::3'):
		try:
			self.rm = visa.ResourceManager()
			self.device = self.rm.open_resource(address)
			self.device.timeout = timeout
			self.device.write(':INP1:COUP AC;IMP 50 OHM')
		except visa.VisaIOError as e:
			self.device = str(e)
		except OSError as e:
			self.device = str(e)

	def setDefaults(self,meastime,pausetime):
		self.meastime = float(meastime)
		self.pausetime = float(pausetime)
		self.device.write('SENS:TOT:ARM:STOP:TIM '+str(self.meastime))

	def getMeasurement(self):
		time.sleep(self.pausetime)
		return (float(self.device.query('READ?'))/float(self.meastime))

	def close(self):
		self.device.close()

class LockIn(Measurer):
	devicetype = 'r'
	tests = {'r':  [[['tp','tm'],[0,2],'Time(s) out of bounds']]}
	def __init__(self,address='GPIB0::16'):
		try:
			self.rm = visa.ResourceManager()
			self.device = self.rm.open_resource(address,read_termination = '\r\n')
			self.device.timeout = timeout
		except visa.VisaIOError as e:
			self.device = str(e)
		except OSError as e:
			self.device = str(e)

	def setDefaults(self,meastime,pausetime):
		self.pausetime = float(pausetime)

	def getMeasurement(self):
		time.sleep(self.pausetime)
		return float(self.device.query('ADC. 1'))

	def close(self):
		self.device.close()

class FakeLockIn(Measurer):
	tests = {'r':  [[['tp','tm'],[0,2],'Time(s) out of bounds']]}
	devicetype = 'r'
	def setDefaults(self,meastime,pausetime):
		self.meastime = meastime
		self.pausetime = pausetime

	def getMeasurement(self):
		time.sleep(self.pausetime)
		time.sleep(self.meastime)
		return random.gauss(-0.8,0.1)


class FakeCounter(Measurer):
	devicetype = 'c'
	tests = {'c':  [[['tp','tm'],[0,2],'Time(s) out of bounds']]}
	def setDefaults(self,meastime,pausetime):
		self.meastime = meastime
		self.pausetime = pausetime

	def getMeasurement(self):
		time.sleep(self.pausetime)
		time.sleep(self.meastime)
		return random.gauss(3000,250)