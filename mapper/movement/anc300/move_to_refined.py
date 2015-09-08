#
# A little program to simulate refined movement
#         by Rob Heath
#
import math
import time
import random
import numpy as np

current_x_position = 4.4152
target_x_position = 3.3
tolerance = 0.001 #to within nearest micron

frequency = 100
voltage = 40
start_steps = 40 # number of steps per movement

#print 'code does not check for \'hump\', watch for this and abort as necessary'

def distance_moved(voltage,frequency,steps,direction,pure=False):
	raw_value = direction*(((steps/float(frequency))*voltage)/500.0)
	if pure==False:
		raw_value += random.normalvariate(0,0.002) #represents the uncertainty in the resistive readout
	return raw_value

def move_to(target_x_position,voltage,frequency,steps):
	global current_x_position
	direction = math.copysign(1,target_x_position-current_x_position)
	while True:
		current_x_position += distance_moved(voltage,frequency,steps,direction)
		#time.sleep(0.1)
		#print 'x:',current_x_position
		if abs(current_x_position-target_x_position) <= tolerance:
			print 'STOP! Arrived!'
			return True
		elif (direction == -1 and current_x_position < target_x_position) or (
			  direction == 1 and current_x_position > target_x_position):
			print 'on this pass, we overshot'
			return False

def home_in_on(target_x_position,voltage,frequency,start_steps):
	step_size = [float(start_steps)]+list(np.logspace(math.floor(math.log10(start_steps)),0,math.floor(math.log10(start_steps))+1))
	print 'changing STEP SIZE'
	for steps in step_size:
		print '\tsteps:',int(steps),'\n\tfrequency:',frequency,'Hz\n\tvoltage:',voltage,'V'
		print('this internally simulated as a movement of roughly %.3f mm' % (distance_moved(voltage,frequency,steps,1,True)))
		if move_to(target_x_position,voltage,frequency,steps) == True:
			break

#home_in_on(target_x_position,voltage,frequency,start_steps)

tests = 10000
data = []
import copy
import csv
for i in range(tests):
	current_x_position = 4.4152
	naive_movement = move_to(target_x_position,voltage,frequency,start_steps)
	dataline = [i,copy.copy(current_x_position)]
	current_x_position = 4.4152
	homed_movement = home_in_on(target_x_position,voltage,frequency,start_steps)
	dataline.append(copy.copy(current_x_position))
	data.append(dataline)

filename = 'data.txt'
filehandle = open(filename,'a')
csvhandle = csv.writer(filehandle,delimiter=',')
for row in data:
	csvhandle.writerow(row)
filehandle.close()