#!user/bin/env python
# -*- coding: utf-8 -*-

try:
	from anc350.PyANC350 import Positioner
except WindowsError:
	print 'PyANC350 failed to load'

try:
	from anc300.attolib import LockIn, SmartStage
except:
	print 'attolib failed to load'

import time
import random

def findClass(key=None):
	index = {
			'fakescanner':FakeScanner,
			'fakemotor':FakeMotor,
			'lockinscanner':LNAScanner,
			'anc300arc200motor':ANC300ARC200Motor,
			 }
	if key == None:
		return index
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
	devicetype = 'Mm'
	tests = {'m':	[[['xt','xf','yf','yt'],[0,5],'X/Y range(s) out of bounds'],
							[['v'],[0.01,70],'Voltage out of bounds'],
							[['f'],[1,1000],'Frequency out of bounds'],
							[['vr'],[0,2],'Readout voltage out of bounds'],
							[['c'],[1,1000],'Clicks out of bounds']],
			  'M':	[[['xt','xf','yf','yt'],[0,5],'X/Y range(s) out of bounds'],
							[['vr'],[0,2],'Readout voltage out of bounds'],
							[['n'],[2,1000],'Number of points out of bounds']]
				}

	def setDefaults(self,voltage,frequency,clicks,readvoltage):
		self.voltage = voltage
		self.frequency = frequency
		self.clicks = clicks
		self.readvoltage = readvoltage
		self.open_movement = True

	def setClosedCircuitDefaults(self,frequency,readvoltage):
		self.readvoltage = readvoltage
		self.frequency = frequency

	def getPos(self,axis=None):
		if axis != None:
			return self.pos[axis]
		else:
			return self.pos

	def moveUp(self,axis):
		self.pos[axis] += self.clicks * 0.001 + random.gauss(0,0.001)
		time.sleep(0.1)
		return True

	def moveDown(self,axis):
		self.pos[axis] -= self.clicks * 0.001 + random.gauss(0,0.001)
		time.sleep(0.1)
		return True

	def moveTo(self,axis,position):
		self.pos[axis] = position+random.gauss(0,0.001)
		time.sleep(0.5)
		return True

class ANC300ARC200Motor(Mover):
	def __init__(self,addresses = ('ASRL6','ASRL5')):
		self.addresses = addresses
		self.device = SmartStage(*addresses)
		self.pos = self.device.ARC200.position
	devicetype = 'Mm'
	tests = {'m':	[[['xt','xf','yf','yt'],[0,5],'X/Y range(s) out of bounds'],
							[['v'],[0.01,70],'Voltage out of bounds'],
							[['f'],[1,1000],'Frequency out of bounds'],
							[['vr'],[0,2],'Readout voltage out of bounds'],
							[['c'],[1,1000],'Clicks out of bounds']],
			  'M':	[[['xt','xf','yf','yt'],[0,5],'X/Y range(s) out of bounds'],
							[['vr'],[0,2],'Readout voltage out of bounds'],
							[['n'],[2,1000],'Number of points out of bounds']]
				}

	def setDefaults(self,voltage,frequency,clicks,readvoltage):
		self.voltage = voltage
		self.frequency = frequency
		for key in ['x','y']:
			self.device.ANC300.set_voltage(key,voltage)
			self.device.ANC300.set_frequency(key,frequency)
		self.clicks = int(clicks)
		self.readvoltage = readvoltage #ARC200
		print 'readvoltage not used'

	def setClosedCircuitDefaults(self,frequency,readvoltage):
		self.readvoltage = readvoltage
		print 'readvoltage not used'
		self.frequency = frequency
		self.voltage = 60
		for key in ['x','y']:
			self.device.ANC300.set_voltage(key,60)
			self.device.ANC300.set_frequency(key,200)


	def getPos(self,axis=None):
		if axis != None:
			return self.pos()[axis]
		else:
			return self.pos()

	def moveUp(self,axis):
		self.device.ANC300.stepu(axis,self.clicks)
		return True

	def moveDown(self,axis):
		self.device.ANC300.stepd(axis,self.clicks)
		return True

	def moveTo(self,axis,position):
		self.device.ANC300.set_voltage(axis,60)
		self.device.ANC300.set_frequency(axis,200)
		self.device.move_to(axis,position,100)
		self.device.ANC300.set_voltage(axis,self.voltage)
		self.device.ANC300.set_frequency(axis,self.frequency)
		return True

	def close(self):
		self.device.ANC300.ground()
		self.device.close()

class LNAScanner(Mover):
	def __init__(self,address='GPIB0::16'):
		self.device = LockIn(address)
		self.pos = {'x':self.device.query('DAC. '+str(self.device.aidmap['x'])),
					'y':self.device.query('DAC. '+str(self.device.aidmap['y']))}

	devicetype = 's'
	tests = {'s':	[[['xt','xf','yf','yt'],[0,10],'X/Y range(s) out of bounds'],
					  		[['xv','yv'],[0,1],'X/Y step size out of bounds']]}
					  		
	def setDefaults(self,stepx,stepy):
		self.stepdict = {'x':stepx,'y':stepy}

	def getPos(self,axis=None):
		if axis != None:
			return self.pos[axis]
		else:
			return self.pos

	def moveUp(self,axis):
		self.pos[axis] += self.stepdict[axis]
		self.device.rawmove('DAC. '+str(self.device.aidmap[axis])+" %.3f" % (self.pos[axis]))
		return True

	def moveDown(self,axis):
		self.pos[axis] -= self.stepdict[axis]
		self.device.rawmove('DAC. '+str(self.device.aidmap[axis])+" %.3f" % (self.pos[axis]))
		return True

	def moveTo(self,axis,position):
		self.device.move(axis,position)
		self.pos[axis] = position
		return True

	def close(self):
		self.device.close()

class FakeScanner(Mover):
	def __init__(self):
		self.pos = {'x':0,'y':0}
	devicetype = 's'
	tests = {'s':	[[['xt','xf','yf','yt'],[0,10],'X/Y range(s) out of bounds'],
					  		[['xv','yv'],[0,1],'X/Y step size out of bounds']]}

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