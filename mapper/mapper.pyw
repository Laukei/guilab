#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import matplotlib
matplotlib.use('Qt4Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as tri
import numpy as np
#import math
from PySide import QtGui, QtCore, QtWebKit

import json
#import time
#import csv
#import os

import colormaps
import movement
import measurement

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

settings_file = 'settings.json'

def getSettings():
	try:
		with open(settings_file,'r') as f:
			settings = json.loads(f.read())
	except IOError:
		settings = defaultSettings()
	return settings

def defaultSettings():
	return {'CORE':{
				'scannertype':'fakescanner',
				'motortype':'fakemotor',
				'countertype':'fakecounter',
				'reflectype':'fakereflec'
				},
			'SIM':{
				'sim900addr':'ASRL1',
				'vsourcemod':2,
				'tsourcemod':1,
				'vmeasmod':7,
				'vsourceinput':1,
				'vmeasinput':2,
				'tinput':3},
			'EXPORT':{
					'title':True,
					'verbose':False,
					'manual_axes':False,
					'xmax':None,
					'xmin':None,
					'ymax':None,
					'ymin':None,
					'width':8,
					'height':6,
					'unit':'in',
					'dpi':150},
			'targetfolder':''
			}

def setSettings(settings):
	try:
		with open(settings_file,'w') as f:
			f.write(json.dumps(settings))
			return True
	except IOError:
		return False

class MapperProg(QtGui.QMainWindow):
	def __init__(self):
		super(MapperProg,self).__init__()
		self.initUI()


	def initUI(self):
		#create UI; maybe use lists? dicts? something more elegant!
		self.createMenuAndToolbar()
		self.createLayoutsAndWidgets()
		self.populateLayouts()

		#finalize things

		self.setDefaults()
		self.settings = getSettings()
		self.name_of_application = 'Mapper'
		#self.resize(800,500)
		self.setWindowTitle(self.name_of_application + '[*]')
		self.setWindowIcon(QtGui.QIcon(r'icons\mapper.png'))
		self.statusBar().showMessage('Ready...')
		self.show()

	def createMenuAndToolbar(self):
		exitAction = QtGui.QAction(QtGui.QIcon(r'icons\exit.png'),'&Exit',self)
		exitAction.setShortcut('Ctrl+Q')
		exitAction.setStatusTip('Exit application')
		exitAction.triggered.connect(self.close)

		newAction = QtGui.QAction(QtGui.QIcon(r'icons\new.png'),'&New...',self)
		newAction.setShortcut('Ctrl+N')
		newAction.setStatusTip('Blank dataset')
		newAction.triggered.connect(self.new)

		newSequentialAction = QtGui.QAction(QtGui.QIcon(r'icons\newsequential.png'),'&New (sequential)...',self)
		newSequentialAction.setShortcut('Ctrl+Shift+N')
		newSequentialAction.setStatusTip('Blank sequential dataset')
		newSequentialAction.triggered.connect(self.newSequential)

		openAction = QtGui.QAction(QtGui.QIcon(r'icons\open.png'),'&Open...',self)
		openAction.setShortcut('Ctrl+O')
		openAction.setStatusTip('Open data for viewing')
		openAction.triggered.connect(self.open)

		saveAction = QtGui.QAction(QtGui.QIcon(r'icons\save.png'),'&Save',self)
		saveAction.setShortcut('Ctrl+S')
		saveAction.setStatusTip('Save current data')
		saveAction.triggered.connect(self.save)

		saveAsAction = QtGui.QAction(QtGui.QIcon(r'icons\saveas.png'),'&Save As...',self)
		saveAsAction.setShortcut('Ctrl+Shift+S')
		saveAsAction.setStatusTip('Save as')
		saveAsAction.triggered.connect(self.saveAs)

		acquireAction = QtGui.QAction(QtGui.QIcon(r'icons\acquire.png'),'&Run',self)
		acquireAction.setShortcut('Ctrl+R')
		acquireAction.setStatusTip('Run scan (Ctrl+R)')
		acquireAction.triggered.connect(self.acquire)

		haltAction = QtGui.QAction(QtGui.QIcon(r'icons\abort.png'),'&Halt acquisition',self)
		haltAction.setShortcut('Ctrl+H')
		haltAction.setStatusTip('Halt acquisition (Ctrl+H)')
		haltAction.triggered.connect(self.halt)
		haltAction.setEnabled(False)

		plotAction = QtGui.QAction(QtGui.QIcon(r'icons\plot.png'),'&Plot',self)
		plotAction.setShortcut('Ctrl+P')
		plotAction.setStatusTip('Plot data graphically (Ctrl+P)')
		plotAction.triggered.connect(self.plotExternal)

		exportAction = QtGui.QAction(QtGui.QIcon(r'icons\export.png'),'&Export',self)
		exportAction.setShortcut('Ctrl+C')
		exportAction.setStatusTip('Export data to CSV (Ctrl+C)')
		exportAction.triggered.connect(self.export)

		settingsAction = QtGui.QAction(QtGui.QIcon(r'icons\settings.png'),'&Device settings',self)
		settingsAction.setStatusTip('Edit device settings')
		settingsAction.triggered.connect(self.openSettings)

		helpAction = QtGui.QAction(QtGui.QIcon(r'icons\help.png'),'&View help',self)
		helpAction.setStatusTip('View help file')
		helpAction.triggered.connect(self.helpFile)

		aboutAction = QtGui.QAction(QtGui.QIcon(r'icons\about.png'),'&About program',self)
		aboutAction.setStatusTip('About program')
		aboutAction.triggered.connect(self.aboutProgram)

		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(newAction)
		fileMenu.addAction(newSequentialAction)
		fileMenu.addSeparator()
		fileMenu.addAction(openAction)
		fileMenu.addSeparator()
		fileMenu.addAction(saveAction)
		fileMenu.addAction(saveAsAction)
		fileMenu.addSeparator()
		fileMenu.addAction(exitAction)
		settingsMenu = menubar.addMenu('&Settings')
		settingsMenu.addAction(settingsAction)
		helpMenu = menubar.addMenu('&Help')
		helpMenu.addAction(helpAction)
		helpMenu.addSeparator()
		helpMenu.addAction(aboutAction)
		
		self.toolbar = self.addToolBar('Operations')
		self.toolbar.setMovable(False)
		self.toolbar.addAction(acquireAction)
		self.toolbar.addAction(haltAction)
		self.toolbar.addSeparator()
		self.toolbar.addAction(plotAction)
		self.toolbar.addAction(exportAction)

	def createLayoutsAndWidgets(self):
		self.metadata_grid = QtGui.QGridLayout()
		self.motor_grid = QtGui.QGridLayout()
		self.scanner_grid = QtGui.QGridLayout()
		self.count_grid = QtGui.QGridLayout()
		self.reflec_grid = QtGui.QGridLayout()

		self.metadata_widget = QtGui.QGroupBox('Metadata')
		self.motor_widget = QtGui.QWidget()
		self.scanner_widget = QtGui.QWidget()
		self.count_widget = QtGui.QWidget()
		self.reflec_widget = QtGui.QWidget()

		#self.metadata_widget.setLayout(self.metadata_grid)
		#self.motor_widget.setLayout(self.motor_grid)
		#self.scanner_widget.setLayout(self.scanner_grid)
		#self.count_widget.setLayout(self.count_grid)
		#self.reflec_widget.setLayout(self.reflec_grid)

		for grid, widget in [[self.metadata_grid, self.metadata_widget],
							 [self.motor_grid, self.motor_widget],
							 [self.scanner_grid, self.scanner_widget],
							 [self.count_grid, self.count_widget],
							 [self.reflec_grid, self.reflec_widget]]:
			layout = QtGui.QVBoxLayout()
			layout.addLayout(grid)
			layout.addStretch(1)
			widget.setLayout(layout)
	
		self.movement_tab = QtGui.QTabWidget()
		self.measurement_tab = QtGui.QTabWidget()

		self.movement_tab.setFixedWidth(250)
		self.measurement_tab.setFixedWidth(250)
		self.metadata_widget.setFixedWidth(500)

		self.movement_tab.addTab(self.motor_widget,'Motor')
		self.movement_tab.addTab(self.scanner_widget,'Scanner')

		self.measurement_tab.addTab(self.reflec_widget,'Reflection')
		self.measurement_tab.addTab(self.count_widget,'Counts')

		self.checkForGraph() #does the graph

		self.hbox = QtGui.QHBoxLayout()
		self.tabhbox = QtGui.QHBoxLayout()
		self.vbox = QtGui.QVBoxLayout()
		self.vbox.addWidget(self.metadata_widget)
		self.vbox.addLayout(self.tabhbox)
		self.hbox.addLayout(self.vbox)
		self.hbox.addWidget(self.canvas)
		self.tabhbox.addWidget(self.movement_tab)
		self.tabhbox.addWidget(self.measurement_tab)

		self.main_widget = QtGui.QWidget()
		self.main_widget.setLayout(self.hbox)
		self.setCentralWidget(self.main_widget)

	def populateLayouts(self):
		#populate metadata_grid
		self.username = QtGui.QLineEdit('')
		self.dateandtime = QtGui.QLineEdit('')
		self.batchName = QtGui.QLineEdit('')
		self.deviceId = QtGui.QLineEdit('')
		self.sma = QtGui.QLineEdit('')
		self.manualtemp = QtGui.QCheckBox('Manual?')
		self.temp = QtGui.QLineEdit('')
		self.comment = QtGui.QLineEdit('')
		self.manualbias = QtGui.QCheckBox('Manual?')
		self.bias = QtGui.QLineEdit('')

		self.dateandtime.setEnabled(False)
		self.manualtemp.stateChanged.connect(self.temp.setEnabled)
		self.manualbias.stateChanged.connect(self.bias.setEnabled)
		self.temp.setEnabled(False)
		self.bias.setEnabled(False)

		self.metadata_grid.setSpacing(10)
		self.subgrid1 = QtGui.QGridLayout()

		self.metadata_grid.addWidget(QtGui.QLabel('User:'),0,0)
		self.metadata_grid.addWidget(self.username,0,1)
		self.metadata_grid.addWidget(QtGui.QLabel('At:'),0,2)
		self.metadata_grid.addWidget(self.dateandtime,0,3)

		self.metadata_grid.addWidget(QtGui.QLabel('Batch:'),1,0)
		self.metadata_grid.addWidget(self.batchName,1,1)
		self.metadata_grid.addWidget(QtGui.QLabel('Device:'),1,2)
		self.metadata_grid.addWidget(self.deviceId,1,3)

		self.metadata_grid.addWidget(QtGui.QLabel('SMA:'),2,0)
		self.metadata_grid.addWidget(self.sma,2,1)
		self.subgrid1.addWidget(self.manualtemp,0,0)
		self.subgrid1.addWidget(QtGui.QLabel('Temp:'),0,1)
		self.subgrid1.addWidget(self.temp,0,2)
		self.subgrid1.addWidget(self.manualbias,1,0)
		self.subgrid1.addWidget(QtGui.QLabel('Bias:'),1,1)
		self.subgrid1.addWidget(self.bias,1,2)
		self.metadata_grid.addLayout(self.subgrid1,2,2,2,2)

		self.metadata_grid.addWidget(QtGui.QLabel('Comments:'),3,0)
		self.metadata_grid.addWidget(self.comment,3,1)

		#populate motor_grid
		self.xfrom_m = QtGui.QLineEdit('')
		self.xto_m = QtGui.QLineEdit('')
		self.yfrom_m = QtGui.QLineEdit('')
		self.yto_m = QtGui.QLineEdit('')
		self.volt_m = QtGui.QLineEdit('')
		self.freq_m = QtGui.QLineEdit('')
		self.readv_m = QtGui.QLineEdit('')
		self.clicks_m = QtGui.QLineEdit('')
		self.numpoints_m = QtGui.QLineEdit('')
		self.closedloop_m = QtGui.QCheckBox('Closed-loop')
		self.numpoints_m.setEnabled(False)

		self.motor_grid.addWidget(QtGui.QLabel('X range:'),0,0)
		self.motor_grid.addWidget(self.xfrom_m,0,1)
		self.motor_grid.addWidget(QtGui.QLabel('->'),0,2)
		self.motor_grid.addWidget(self.xto_m,0,3)
		self.motor_grid.addWidget(QtGui.QLabel('Y range:'),1,0)
		self.motor_grid.addWidget(self.yfrom_m,1,1)
		self.motor_grid.addWidget(QtGui.QLabel('->'),1,2)
		self.motor_grid.addWidget(self.yto_m,1,3)

		self.motor_grid.addWidget(QtGui.QLabel('Volt:'),2,0)
		self.motor_grid.addWidget(self.volt_m,2,1)
		self.motor_grid.addWidget(QtGui.QLabel('Freq:'),2,2)
		self.motor_grid.addWidget(self.freq_m,2,3)
		self.motor_grid.addWidget(QtGui.QLabel('V<sub>read</sub>:'),3,2)
		self.motor_grid.addWidget(self.readv_m,3,3)
		self.motor_grid.addWidget(QtGui.QLabel('Clicks:'),3,0)
		self.motor_grid.addWidget(self.clicks_m,3,1)
		#self.motor_grid.addWidget(QtGui.QLabel('->'),1,2)
		self.motor_grid.addWidget(self.closedloop_m,4,0,1,2)
		self.motor_grid.addWidget(QtGui.QLabel('Points:'),4,2)
		self.motor_grid.addWidget(self.numpoints_m,4,3)

		self.closedloop_m.stateChanged.connect(self.numpoints_m.setEnabled)
		self.closedloop_m.stateChanged.connect(self.clicks_m.setDisabled)
		self.closedloop_m.stateChanged.connect(self.volt_m.setDisabled)
		self.closedloop_m.stateChanged.connect(self.freq_m.setDisabled)

		#populate scanner grid
		self.xfrom_s = QtGui.QLineEdit('')
		self.xto_s = QtGui.QLineEdit('')
		self.yfrom_s = QtGui.QLineEdit('')
		self.yto_s = QtGui.QLineEdit('')
		self.xvoltstep_s = QtGui.QLineEdit('')
		self.yvoltstep_s = QtGui.QLineEdit('')

		self.scanner_grid.addWidget(QtGui.QLabel('X range:'),0,0)
		self.scanner_grid.addWidget(self.xfrom_s,0,1)
		self.scanner_grid.addWidget(QtGui.QLabel('->'),0,2)
		self.scanner_grid.addWidget(self.xto_s,0,3)
		self.scanner_grid.addWidget(QtGui.QLabel('Y range:'),1,0)
		self.scanner_grid.addWidget(self.yfrom_s,1,1)
		self.scanner_grid.addWidget(QtGui.QLabel('->'),1,2)
		self.scanner_grid.addWidget(self.yto_s,1,3)

		self.scanner_grid.addWidget(QtGui.QLabel('X step:'),2,0)
		self.scanner_grid.addWidget(self.xvoltstep_s,2,1)
		self.scanner_grid.addWidget(QtGui.QLabel('Y step:'),2,2)
		self.scanner_grid.addWidget(self.yvoltstep_s,2,3)


		#populate counts grid
		self.meastime_c = QtGui.QLineEdit('')
		self.pausetime_c = QtGui.QLineEdit('')

		self.count_grid.addWidget(QtGui.QLabel('T<sub>meas</sub>:'),0,0)
		self.count_grid.addWidget(self.meastime_c,0,1)
		self.count_grid.addWidget(QtGui.QLabel('T<sub>pause</sub>:'),1,0)
		self.count_grid.addWidget(self.pausetime_c,1,1)

		#populate reflectance grid
		self.meastime_r = QtGui.QLineEdit('')
		self.pausetime_r = QtGui.QLineEdit('')

		self.reflec_grid.addWidget(QtGui.QLabel('T<sub>meas</sub>:'),0,0)
		self.reflec_grid.addWidget(self.meastime_r,0,1)
		self.reflec_grid.addWidget(QtGui.QLabel('T<sub>pause</sub>:'),1,0)
		self.reflec_grid.addWidget(self.pausetime_r,1,1)

		self.key_object_map = {'xfrom_m':self.xfrom_m,
								'xto_m':self.xto_m,
								'yfrom_m':self.yfrom_m,
								'yto_m':self.yto_m,
								'volt_m':self.volt_m,
								'freq_m':self.freq_m,
								'clicks_m':self.clicks_m,
								'readv_m':self.readv_m,
								'closedloop_m':self.closedloop_m,
								'numpoints_m':self.numpoints_m,
								'xfrom_s':self.xfrom_s,
								'xto_s':self.xto_s,
								'yfrom_s':self.yfrom_s,
								'yto_s':self.yto_s,
								'xvoltstep_s':self.xvoltstep_s,
								'yvoltstep_s':self.yvoltstep_s,
								'meastime_c':self.meastime_c,
								'pausetime_c':self.pausetime_c,
								'meastime_r':self.meastime_r,
								'pausetime_r':self.pausetime_r}

	def setDefaults(self):
		'''
		FOR REFERENCE:
		xfrom_m
		xto_m
		yfrom_m
		yto_m
		volt_m
		freq_m
		clicks_m
		readv_m
		closedloop_m
		numpoints_m
		xfrom_s
		xto_s
		yfrom_s
		yto_s
		xvoltstep_s
		yvoltstep_s
		meastime_c
		pausetime_c
		meastime_r
		pausetime_r
		'''
		self.key_object_map['xfrom_m'].setText('')
		self.key_object_map['xto_m'].setText('')
		self.key_object_map['yfrom_m'].setText('')
		self.key_object_map['yto_m'].setText('')
		self.key_object_map['volt_m'].setText('40')
		self.key_object_map['freq_m'].setText('100')
		self.key_object_map['readv_m'].setText('1')
		self.key_object_map['clicks_m'].setText('10')
		self.key_object_map['closedloop_m'].setChecked(False)
		self.key_object_map['numpoints_m'].setText('20')
		self.key_object_map['xfrom_s'].setText('0')
		self.key_object_map['xto_s'].setText('10')
		self.key_object_map['yfrom_s'].setText('0')
		self.key_object_map['yto_s'].setText('10')
		self.key_object_map['xvoltstep_s'].setText('1')
		self.key_object_map['yvoltstep_s'].setText('1')
		self.key_object_map['meastime_c'].setText('0.7')
		self.key_object_map['pausetime_c'].setText('0.2')
		self.key_object_map['meastime_r'].setText('0.05')
		self.key_object_map['pausetime_r'].setText('0.05')

	def acquire(self):
		#first: work out what measurement we're trying to run
		#by finding which tabs are selected
		self.meas_par = {}
		self.data = []
		self.colorbar_max = -float('inf')
		try:
			if self.movement_tab.currentWidget() == self.motor_widget:
				self.meas_par['xf'] = float(self.xfrom_m.text())
				self.meas_par['xt'] = float(self.xto_m.text())
				self.meas_par['yf'] = float(self.yfrom_m.text())
				self.meas_par['yt'] = float(self.yto_m.text())
				self.meas_par['vr'] = float(self.readv_m.text())
				if self.closedloop_m.isChecked() == False:
					self.meas_par['mtype'] = 'm'
					self.meas_par['v'] = float(self.volt_m.text())
					self.meas_par['f'] = float(self.freq_m.text())
					self.meas_par['c'] = float(self.clicks_m.text())
				elif self.closedloop_m.isChecked() == True:
					self.meas_par['mtype'] = 'M'
					self.meas_par['n'] = float(self.numpoints_m.text())
			elif self.movement_tab.currentWidget() == self.scanner_widget:
				self.meas_par['mtype'] = 's'
				self.meas_par['xf'] = float(self.xfrom_s.text())
				self.meas_par['xt'] = float(self.xto_s.text())
				self.meas_par['yf'] = float(self.yfrom_s.text())
				self.meas_par['yt'] = float(self.yto_s.text())
				self.meas_par['xv'] = float(self.xvoltstep_s.text())
				self.meas_par['yv'] = float(self.yvoltstep_s.text())
			else:
				self.statusBar().showMessage('Unable to identify movement type...')
				return

			if self.measurement_tab.currentWidget() == self.reflec_widget:
				self.meas_par['mtype'] += 'r'
				self.meas_par['tm'] = float(self.meastime_r.text())
				self.meas_par['tp'] = float(self.pausetime_r.text())
			elif self.measurement_tab.currentWidget() == self.count_widget:
				self.meas_par['mtype'] += 'c'
				self.meas_par['tm'] = float(self.meastime_c.text())
				self.meas_par['tp'] = float(self.pausetime_c.text())
			else:
				self.statusBar().showMessage('Unable to identify measurement type...')
				return
		except ValueError as e:
			self.statusBar().showMessage('ERROR: '+str(e))
			return
		#then check input values (ranges, etc)
		#tests is a series of tests to be checked against

		self.tests = {'m':	[[['xt','xf','yf','yt'],[0,5],'X/Y range(s) out of bounds'],
							[['v'],[0.01,70],'Voltage out of bounds'],
							[['f'],[1,1000],'Frequency out of bounds'],
							[['vr'],[0,2],'Readout voltage out of bounds'],
							[['c'],[1,1000],'Clicks out of bounds']],
					  'M':	[[['xt','xf','yf','yt'],[0,5],'X/Y range(s) out of bounds'],
							[['vr'],[0,2],'Readout voltage out of bounds'],
							[['n'],[2,1000],'Number of points out of bounds']],
					  's':	[[['xt','xf','yf','yt'],[0,10],'X/Y range(s) out of bounds'],
					  		[['xv','yv'],[0,1],'X/Y step size out of bounds']],
					  'r':  [[['tp','tm'],[0,2],'Time(s) out of bounds']],
					  'c':  [[['tp','tm'],[0,2],'Time(s) out of bounds']]}
		for test_set in self.tests.keys():
			if test_set in self.meas_par['mtype']:
				for test in self.tests[test_set]:
					for key in test[0]:
						if not (test[1][0] <= self.meas_par[key] <= test[1][1]):
							self.statusBar().showMessage(test[2]+': '+str(self.meas_par[key])+' outside limits '+str(test[1][0])+', '+str(test[1][1]))
							return
		#connect to instrumentation and pass handles through
		if 'm' in self.meas_par['mtype'] or 'M' in self.meas_par['mtype']:
			self.meas_par['mover'] = movement.findClass(self.settings['CORE']['motortype'])()

		elif 's' in self.meas_par['mtype']:
			self.meas_par['mover'] = movement.findClass(self.settings['CORE']['scannertype'])()

		
		if 'r' in self.meas_par['mtype']:
			self.meas_par['measurer'] = measurement.findClass(self.settings['CORE']['reflectype'])()

		elif 'c' in self.meas_par['mtype']:
			self.meas_par['measurer'] = measurement.findClass(self.settings['CORE']['countertype'])()

		#then launch the process and pass the values
		#print 'launching in separate thread...',
		self.x_forward = True
		self.y_forward = True
		if self.meas_par['xf']>self.meas_par['xt']:
			self.x_forward = False
		if self.meas_par['yf']>self.meas_par['yt']:
			self.y_forward = False
		self.obj_thread = QtCore.QThread()
		self.mapper_drone = MapperDrone(self.meas_par)
		self.mapper_drone.moveToThread(self.obj_thread)
		self.obj_thread.started.connect(self.mapper_drone.runScan)
		self.mapper_drone.newdata.connect(self.getData)
		self.mapper_drone.finished.connect(self.obj_thread.quit)
		self.mapper_drone.finished.connect(self.acquisitionFinished)
		self.mapper_drone.aborted.connect(self.resetPbar)
		self.mapper_drone.xSteps.connect(self.getXSteps)
		self.mapper_drone.ySteps.connect(self.getYSteps)
		self.x_steps = None
		self.y_steps = None
		self.obj_thread.start()
		#print 'launched'

	def getData(self, data):
		self.data.append(data)
		self.updatePreviewGrid()

	def getXSteps(self,x_steps):
		self.x_steps = x_steps

	def getYSteps(self,y_steps):
		self.y_steps = y_steps

	def updatePreview(self):
		self.data_array = np.array(self.data).transpose()
		self.fig.clear()
		self.ax.clear()
		try:
			self.contourf = plt.tricontourf(self.data_array[0],self.data_array[1],self.data_array[4],cmap=colormaps.viridis)
		except RuntimeError:
			pass
		except ValueError:
			pass

		try:
			self.cbar = plt.colorbar()
		except RuntimeError:
			pass

		self.colordata = []
		for value in [((x-min(self.data_array[4]))/(max(self.data_array[4]-min(self.data_array[4])))) for x in self.data_array[4]]:
			self.colordata.append(colormaps.viridis(value))

		for v, value in enumerate(self.data_array[0]):
			self.plot = plt.plot([self.data_array[0][v]], [self.data_array[1][v]],'o',color=self.colordata[v],ms=10)

		self.canvas.draw()

	def updatePreviewGrid(self):
		#
		# NOTE TO SELF:
		# http://stackoverflow.com/questions/17835302/how-to-update-matplotlibs-imshow-window-interactively
		# "much faster to use object's 'set_data' method" <-- use this instead of new imshow for efficiency
		#
		self.data_array = np.array(self.data).transpose()
		
		self.extent = [self.data_array[0].min(), self.data_array[0].max(), self.data_array[1].min(),self.data_array[1].max()]
		if self.x_steps != None:
			self.z_data = [list(self.data_array[4][x:x+self.x_steps]) for x in range(0,len(self.data_array[4]),self.x_steps)]
			if len(self.z_data[-1]) < self.x_steps:
				self.z_data[-1] += [np.nan]*(self.x_steps - len(self.z_data[-1]))
			self.extent[1] = max([self.data_array[0].max(),self.meas_par['xt'],self.meas_par['xf']])
			self.extent[0] = min([self.data_array[0].min(),self.meas_par['xt'],self.meas_par['xf']])
			if self.y_steps != None and len(self.z_data) < self.y_steps:
				self.z_data += [[np.nan]*self.x_steps]*(self.y_steps-len(self.z_data))
				self.extent[3] = max([self.data_array[1].max(),self.meas_par['yt'],self.meas_par['yf']])
				self.extent[2] = min([self.data_array[1].min(),self.meas_par['yt'],self.meas_par['yf']])
		else:
			self.z_data = [list(self.data_array[4])]
		if self.extent[2] == self.extent[3]:
			self.extent[3] += 0.000001
		if self.extent[0] == self.extent[1]:
			self.extent[1] += 0.000001

		#correct for swapped .extents()
		if not self.x_forward:
			for r, row in enumerate(self.z_data):
				self.z_data[r] = row[::-1]
		if self.y_forward:
			self.z_data = self.z_data[::-1]
		try:
			self.img.set_data(self.z_data)
			self.img.autoscale()
			self.img.set_extent(self.extent)
		except AttributeError:
			self.img = plt.imshow(self.z_data,extent=self.extent, interpolation='nearest',cmap=colormaps.viridis, aspect='auto')
			self.cbar = plt.colorbar()

		self.canvas.draw()


	def checkForGraph(self):
		try:
			self.canvas
		except AttributeError:
			self.data = np.array([[]])
			self.fig = plt.figure(figsize = (4.5,4), dpi=72, facecolor=(1,1,1), edgecolor=(0,0,0))
			self.ax = self.fig.add_subplot(1,1,1)
			#self.plot = plt.tricontourf(self.data)#*self.data)
			self.ax.set_ylabel('dunno')
			self.ax.set_xlabel('nobody told me')
			self.canvas = FigureCanvas(self.fig)
			self.fig.tight_layout()

	def acquisitionFinished(self):
		pass

	def resetPbar(self):
		pass

	def new(self):
		pass

	def newSequential(self):
		pass

	def open(self):
		pass

	def save(self):
		pass

	def saveAs(self):
		pass

	def halt(self):
		pass

	def plotExternal(self):
		pass

	def export(self):
		pass

	def openSettings(self):
		self.settings_window = SettingsDialog(self.settings,movement.findClass(),measurement.findClass())
		self.settings_window.exec_()


	def helpFile(self):
		pass

	def aboutProgram(self):
		pass

	def closeEvent(self,event):
		setSettings(self.settings)


class MapperDrone(QtCore.QObject):
	def __init__(self,meas_par):
		super(MapperDrone,self).__init__()
		#handle stuff passed in
		self.abort = False
		self.meas_par = meas_par
		self.mover = meas_par['mover']
		self.measurer = meas_par['measurer']
		
	finished = QtCore.Signal()
	newdata = QtCore.Signal(list)
	aborted = QtCore.Signal()
	xSteps = QtCore.Signal(int)
	ySteps = QtCore.Signal(int)

	def runScan(self):
		self.init() #readies mover/measurer
		self.mover.moveTo('x',self.meas_par['xf'])
		self.mover.moveTo('y',self.meas_par['yf'])
		#print 'homed to:',self.mover.getPos()
		self.xgoesup = self.meas_par['xt'] > self.meas_par['xf']
		self.ygoesup = self.meas_par['yt'] > self.meas_par['yf']
		self.dataset = []
		if 'M' in self.meas_par['mtype'] or 's' in self.meas_par['mtype']:
			self.runClosedLoopMap()
		elif 'm' in self.meas_par['mtype']:
			self.runOpenLoopMap()

		self.mover.moveTo('x',self.meas_par['xf'])
		self.mover.moveTo('y',self.meas_par['yf'])
		self.mover.close()
		self.measurer.close()
		self.finished.emit()

	def runClosedLoopMap(self):
		for j, y_step in enumerate(self.y_steplist):
			self.mover.moveTo('y',y_step)
			for i, x_step in enumerate(self.x_steplist):
				self.mover.moveTo('x',x_step)
				self.pos = self.mover.getPos()
				self.meas = self.measurer.getMeasurement()
				self.dataset.append([self.pos['x'],self.pos['y'],i,j,self.meas])
				self.newdata.emit(self.dataset[-1])
				if self.abort == True:
					self.aborted.emit()
					return
			if self.abort == True:
				self.aborted.emit()
				return	

	def runOpenLoopMap(self):
		self.step = {'x':0,'y':0}
		while True:
			while True:
				self.pos = self.mover.getPos()
				if (self.x_steps == float('inf') and self.xgoesup and self.pos['x'] > self.meas_par['xt']) or (
				   self.x_steps == float('inf') and not self.xgoesup and self.pos['x'] < self.meas_par['xt']):
					self.x_steps = self.step['x']
					self.xSteps.emit(int(self.x_steps)+1)
				self.meas = self.measurer.getMeasurement()
				self.dataset.append([self.pos['x'],self.pos['y'],self.step['x'],self.step['y'],self.meas])
				self.newdata.emit(self.dataset[-1])
				if self.step['x'] >= self.x_steps:
					break
				self.step['x'] += 1
				if self.xgoesup: #if xto > xfrom:
					self.mover.moveUp('x')
				else:
					self.mover.moveDown('x')
				if self.abort == True:
					self.aborted.emit()
					return

			self.step['x']=0
			if (self.y_steps == float('inf') and self.ygoesup and self.pos['y'] > self.meas_par['yt']) or (
			   self.y_steps == float('inf') and not self.ygoesup and self.pos['y'] < self.meas_par['yt']):
				self.y_steps = self.step['y']
				self.ySteps.emit(int(self.y_steps))
				break

			self.mover.moveTo('x',self.meas_par['xf'])
			self.step['y']+=1
			if self.ygoesup: #if xto > xfrom:
				self.mover.moveUp('y')
			else:
				self.mover.moveDown('y')

			if self.abort == True:
				self.aborted.emit()
				return

	def init(self):
		#perform setup of devices
		if 'm' in self.meas_par['mtype']:
			self.mover.setDefaults( self.meas_par['v'],
									self.meas_par['f'],
									self.meas_par['c'],
									self.meas_par['vr'])
			self.x_steps = float('inf')
			self.y_steps = float('inf')
		elif 'M' in self.meas_par['mtype']:
			self.mover.setClosedCircuitDefaults(1000,self.meas_par['vr'])
			self.x_steps = self.meas_par['n']+1
			self.y_steps = self.meas_par['n']+1
			self.xSteps.emit(int(self.x_steps))
			self.ySteps.emit(int(self.y_steps))
			self.x_steplist = np.linspace(self.meas_par['xf'],self.meas_par['xt'],self.x_steps)
			self.y_steplist = np.linspace(self.meas_par['yf'],self.meas_par['yt'],self.y_steps)
		elif 's' in self.meas_par['mtype']:
			self.mover.setDefaults(	self.meas_par['xv'],
									self.meas_par['yv'])
			self.x_steps = (abs(self.meas_par['xt']-self.meas_par['xf'])/self.meas_par['xv'])+1
			self.y_steps = (abs(self.meas_par['yt']-self.meas_par['yf'])/self.meas_par['yv'])+1
			self.x_steplist = np.linspace(self.meas_par['xf'],self.meas_par['xt'],self.x_steps)
			self.y_steplist = np.linspace(self.meas_par['yf'],self.meas_par['yt'],self.y_steps)
			self.xSteps.emit(int(self.x_steps))
			self.ySteps.emit(int(self.y_steps))
		if 'r' in self.meas_par['mtype']:
			self.measurer.setDefaults(	self.meas_par['tm'],
										self.meas_par['tp'])
		elif 'c' in self.meas_par['mtype']:
			self.measurer.setDefaults(	self.meas_par['tm'],
										self.meas_par['tp'])
		
class SettingsDialog(QtGui.QDialog):
	def __init__(self,settings,movers,measurers):
		super(SettingsDialog,self).__init__()
		self.settings = settings
		self.movers = movers
		self.measurers = measurers
		self.associations = {
			'a':{
				't':'Mapper',
				'w': QtGui.QFormLayout(),
				'v':'CORE',
				'c': {
					'a':{
						't':'Scanner controller:',
						'w': QtGui.QComboBox(),
						'p': self.movers,
						'v':'scannertype'
						},
					'b':{
						't':'Motor controller:',
						'w': QtGui.QComboBox(),
						'p': self.movers,
						'v':'motortype'
						},
					'c':{
						't':'Counter:',
						'w': QtGui.QComboBox(),
						'p': self.measurers,
						'v':'countertype'
						},
					'd':{
						't':'Reflection:',
						'w': QtGui.QComboBox(),
						'p': self.measurers,
						'v':'reflectype'
						}	
					}
				},
			'b':{
				't':'SIM900',
				'w':QtGui.QFormLayout(),
				'v':'SIM',
				'c':{
					'a':{
						't':'SIM900 address:',
						'w':QtGui.QLineEdit(),
						'v':'sim900addr'
						},
					'b':{
						't':'SIM928 voltage source module:',
						'w':QtGui.QSpinBox(),
						'v':'vsourcemod'
						},
					'c':{
						't':'SIM922 temperature module:',
						'w':QtGui.QSpinBox(),
						'v':'tsourcemod'
						},
					'd':{
						't':'SIM922 sensor channel:',
						'w':QtGui.QSpinBox(),
						'v':'tinput'
						}
					}
				},
			'c':{
				't':'Export',
				'w':QtGui.QFormLayout(),
				'v':'EXPORT',
				'c':{
					'a':{
						't':'Add title',
						'w':QtGui.QCheckBox(),
						'v':'title'
						},
					'b':{
						't':'Verbose graph',
						'w':QtGui.QCheckBox(),
						'v':'verbose'
						},
					'c':{
						't':'Manually-defined axis limits',
						'w':QtGui.QCheckBox(),
						'v':'manual_axes'
						},
					'd':{
						't':'Xmax',
						'w':QtGui.QDoubleSpinBox(),
						'v':'xmax'
						},
					'e':{
						't':'Xmin',
						'w':QtGui.QDoubleSpinBox(),
						'v':'xmin'
						},
					'f':{
						't':'Ymax',
						'w':QtGui.QDoubleSpinBox(),
						'v':'ymax'
						},
					'g':{
						't':'Ymin',
						'w':QtGui.QDoubleSpinBox(),
						'v':'ymin'
						},
					'h':{
						't':'Width',
						'w':QtGui.QDoubleSpinBox(),
						'v':'width'
						},
					'i':{
						't':'Height',
						'w':QtGui.QDoubleSpinBox(),
						'v':'height'
						},
					'j':{
						't':'Units',
						'w':QtGui.QComboBox(),
						'v':'unit',
						'p': ['in','cm','px']
						},
					'k':{
						't':'Plot DPI',
						'w':QtGui.QSpinBox(),
						'v':'dpi'
						}
					}
				}
			}

		self.initUI()

	def initUI(self):
		self.createLayoutsAndWidgets()
		self.populateLayoutsAndSetDefaults()
		self.setWindowTitle('Settings')

	def createLayoutsAndWidgets(self):
		self.tab_widget = QtGui.QTabWidget()
		self.button_box = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)

		self.button_box.accepted.connect(self.packageSettings)
		self.button_box.accepted.connect(self.accept)
		self.button_box.rejected.connect(self.reject)

		self.main_layout = QtGui.QVBoxLayout()
		self.main_layout.addWidget(self.tab_widget)
		self.main_layout.addWidget(self.button_box)
		self.setLayout(self.main_layout)

	def populateLayoutsAndSetDefaults(self):
		for tabkey in sorted(self.associations.keys()):
			self.tabtier = self.associations[tabkey]
			self.intermediary_widget = QtGui.QWidget()
			self.intermediary_widget.setLayout(self.tabtier['w'])
			self.tab_widget.addTab(self.intermediary_widget,self.tabtier['t'])
			for childkey in sorted(self.tabtier['c'].keys()):
				self.childtier = self.tabtier['c'][childkey]
				self.tabtier['w'].addRow(self.childtier['t'], self.childtier['w'])
				if isinstance(self.childtier['w'],QtGui.QComboBox):
					if type(self.childtier['p']) == list:
						for item in self.childtier['p']:
							self.childtier['w'].addItem(item)
						self.childtier['w'].setCurrentIndex(self.childtier['p'].index(self.settings[self.tabtier['v']][self.childtier['v']]))
					elif type(self.childtier['p']) == dict:
						for i, item in enumerate(sorted(self.childtier['p'].keys())):
							self.childtier['w'].addItem(self.childtier['p'][item].__name__)
							if item == self.settings[self.tabtier['v']][self.childtier['v']]:
								self.index = i 
						self.childtier['w'].setCurrentIndex(self.index)
				elif isinstance(self.childtier['w'],QtGui.QCheckBox):
					self.childtier['w'].setChecked(self.settings[self.tabtier['v']][self.childtier['v']])
				elif isinstance(self.childtier['w'],QtGui.QLineEdit):
					self.childtier['w'].setText(str(self.settings[self.tabtier['v']][self.childtier['v']]))
				elif isinstance(self.childtier['w'],QtGui.QSpinBox) or isinstance(self.childtier['w'],QtGui.QDoubleSpinBox):
					self.childtier['w'].setMaximum(1000)
					if self.settings[self.tabtier['v']][self.childtier['v']] != None:
						self.childtier['w'].setValue(self.settings[self.tabtier['v']][self.childtier['v']])
					else:
						self.childtier['w'].setSpecialValueText('None')

	def packageSettings(self):
		for tabkey in sorted(self.associations.keys()):
			self.tabtier = self.associations[tabkey]
			for childkey in sorted(self.tabtier['c'].keys()):
				self.childtier = self.tabtier['c'][childkey]
				if isinstance(self.childtier['w'],QtGui.QComboBox):
					if type(self.childtier['p']) == list:
						self.settings[self.tabtier['v']][self.childtier['v']] = self.childtier['w'].currentText()
					elif type(self.childtier['p']) == dict:
						for i, item in enumerate(sorted(self.childtier['p'].keys())):
							if self.childtier['p'][item].__name__ == self.childtier['w'].currentText():
								self.settings[self.tabtier['v']][self.childtier['v']] = item
				elif isinstance(self.childtier['w'],QtGui.QCheckBox):
					self.settings[self.tabtier['v']][self.childtier['v']] = self.childtier['w'].isChecked()
				elif isinstance(self.childtier['w'],QtGui.QLineEdit):
					self.settings[self.tabtier['v']][self.childtier['v']] = self.childtier['w'].text()
				elif isinstance(self.childtier['w'],QtGui.QSpinBox) or isinstance(self.childtier['w'],QtGui.QDoubleSpinBox):
					if self.childtier['w'].value() != 0:
						self.settings[self.tabtier['v']][self.childtier['v']] = self.childtier['w'].value()
					else:
						self.settings[self.tabtier['v']][self.childtier['v']] = None



def main():
	app = QtGui.QApplication(sys.argv)
	ex = MapperProg()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()