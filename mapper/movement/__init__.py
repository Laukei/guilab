#!user/bin/env python
# -*- coding: utf-8 -*-

try:
	from anc350.PyANC350 import Positioner
except WindowsError:
	print 'PyANC350 failed to load'

try:
	from anc300.attolib import Stages, Readout, LockIn, SmartStage
except:
	print 'attolib failed to load'

import time

def findClass(key):
	index = {
			'fakescanner':FakeScanner,
			'fakemotor':FakeMotor,
			 }
	return index[key]

class Mover:
	#superclass; features are vital for any controller implemented
	#be it ANC300, ANC350, motor, or scanner
	def __init__(self):
		pass

	def setDefaults(self):
		print 'Not implemented: setDefaults'

	def getPos(self,axis=None):
		print 'Not implemented: getPos'
	
	def moveTo(self,axis,position):
		print 'Not implemented: moveTo'

	def close(self):
		print 'Not implemented: close'

class FakeMotor(Mover):
	def __init__(self):
		self.pos = {'x':2.5, 'y':2.5, 'z':2.5}

	def setDefaults(self,voltage,frequency,clicks,readvoltage):
		self.voltage = voltage
		self.frequency = frequency
		self.clicks = clicks
		self.readvoltage = readvoltage

	def getPos(self,axis=None):
		if axis != None:
			return self.pos[axis]
		else:
			return self.pos

	def moveUp(self,axis):
		self.pos[axis] += self.clicks * 0.001
		time.sleep(0.1)
		return True

	def moveDown(self,axis):
		self.pos[axis] -= self.clicks * 0.001
		time.sleep(0.1)
		return True

	def moveTo(self,axis,position):
		self.pos[axis] = position
		time.sleep(0.5)
		return True

class FakeScanner(Mover):
	def __init__(self):
		self.pos = {'x':0,'y':0}

	def setDefaults(self,stepx,stepy):
		self.stepdict = {'x':stepx,'y':stepy}
		
	def getPos(self,axis=None):
		if axis != None:
			return self.pos[axis]
		else:
			return self.pos

	def moveUp(self,axis):
		self.pos[axis] += self.stepdict[axis]
		return True

	def moveDown(self,axis):
		self.pos[axis] -= self.stepdict[axis]
		return True

	def moveTo(self,axis,position):
		self.pos[axis] = position
		time.sleep(0.1)
		return True
