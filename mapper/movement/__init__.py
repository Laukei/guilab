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

class Mover:
	#superclass; features are vital for any controller implemented
	#be it ANC300, ANC350, motor, or scanner
	def __init__(self):
		pass

	def getPos(self,axis=None):
		print 'Not implemented: getPos'
	
	def moveTo(self,axis,position):
		print 'Not implemented: moveTo'

	def run(self,measurement,argv):
		return measurement(*argv)

class FakeMotor(Mover):
	def __init__(self):
		self.pos = {'x':2.5, 'y':2.5, 'z':2.5}

	def getPos(self,axis=None):
		if axis != None:
			return self.pos[axis]
		else:
			return self.pos

	def moveTo(self,axis,position):
		self.pos[axis] = position
		time.sleep(0.2)
		return True

class FakeScanner(Mover):
	def __init__(self):
		self.pos = {'x':0,'y':0}

	def getPos(self,axis=None):
		if axis != None:
			return self.pos[axis]
		else:
			return self.pos

	def moveTo(self,axis,position):
		self.pos[axis] = position
		return True
