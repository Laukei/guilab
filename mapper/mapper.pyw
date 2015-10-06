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
import time
import csv
import os

import colormaps
import movement
import measurement

# swappable for fake modules (modulename -> modulename.fake)
from sim900 import Sim900
from attenuator import Attenuator
# end swappable

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
	return {'DEVICES':{
				'scannertype':'fakescanner',
				'motortype':'fakemotor',
				'countertype':'fakecounter',
				'reflectype':'fakereflec',
				'sim900addr':'ASRL1',
				'vsourcemod':2,
				'tsourcemod':1,
				'tinput':3,
				'att1addr':'GPIB::10',
				'att2addr':'GPIB::15'},
			'EXPORT':{
					'title':True,
					'convert_to_sde':True,
					'verbose':False,
					'manual_axes':False,
					'xmax':None,
					'xmin':None,
					'ymax':None,
					'ymin':None,
					'width':8,
					'height':6,
					'unit':'in',
					'dpi':150,
					'plot_type':'Filled contour',
					'show_datapoints':True},
			'DEFAULTS':{
					'xfrom_m': None,
					'xto_m': None,
					'yfrom_m': None,
					'yto_m': None,
					'volt_m': 40,
					'freq_m': 100,
					'readv_m': 1,
					'clicks_m': 10,
					'closedloop_m': False,
					'numpoints_m': 20,
					'xfrom_s': 0,
					'xto_s': 10,
					'yfrom_s': 0,
					'yto_s': 10,
					'xvoltstep_s': 1,
					'yvoltstep_s': 1,
					'meastime_c': 0.7,
					'pausetime_c': 0.2,
					'meastime_r': 0.05,
					'pausetime_r': 0.05,
					'username':'',
					'dateandtime':'',
					'batchName':'',
					'deviceId':'',
					'sma':'',
					'manualtemp': False,
					'temp':'',
					'comment':'',
					'manualbias': False,
					'bias':'',
					'laserpower': -200,
					'manualatten': False,
					'atten':'',
					'wavelength':'',
					'dcr':''},
			'targetfolder':''
			}

def setSettings(settings):
	try:
		with open(settings_file,'w') as f:
			f.write(json.dumps(settings))
			return True
	except IOError:
		return False

def convert_to_builtin_type(obj):
	#from https://pymotw.com/2/json/
	print 'default(', repr(obj), ')'
	# Convert objects to a dictionary of their representation
	d = { '__class__':obj.__class__.__name__, '__module__':obj.__module__}
	d.update(obj.__dict__)
	return d

class MapperProg(QtGui.QMainWindow):
	def __init__(self):
		super(MapperProg,self).__init__()
		self.initUI()

	aboutToQuit = QtCore.Signal()

	def initUI(self):
		#create UI; maybe use lists? dicts? something more elegant!
		self.createMenuAndToolbar()
		self.createLayoutsAndWidgets()
		self.populateLayouts()

		#finalize things
		self.filename = ''
		self.data = []
		self.settings = getSettings()
		self.setDefaults()
		self.name_of_application = 'Mapper'
		#self.resize(800,500)
		self.setWindowTitle(self.name_of_application + '[*]')
		self.setWindowIcon(QtGui.QIcon(r'icons\mapper.png'))
		self.statusBar().showMessage('Ready...')
		self.show()
		self.setNeedsSaving(reset=True)

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

		self.acquireAction = QtGui.QAction(QtGui.QIcon(r'icons\acquire.png'),'&Run',self)
		self.acquireAction.setShortcut('Ctrl+R')
		self.acquireAction.setStatusTip('Run scan (Ctrl+R)')
		self.acquireAction.triggered.connect(self.acquire)

		self.haltAction = QtGui.QAction(QtGui.QIcon(r'icons\abort.png'),'&Halt acquisition',self)
		self.haltAction.setShortcut('Ctrl+H')
		self.haltAction.setStatusTip('Halt acquisition (Ctrl+H)')
		self.haltAction.triggered.connect(self.halt)
		self.haltAction.setEnabled(False)

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
		self.toolbar.addAction(newAction)
		self.toolbar.addAction(newSequentialAction)
		self.toolbar.addSeparator()
		self.toolbar.addAction(self.acquireAction)
		self.toolbar.addAction(self.haltAction)
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

		for grid, widget in [[self.metadata_grid, self.metadata_widget],
							 [self.motor_grid, self.motor_widget],
							 [self.scanner_grid, self.scanner_widget],
							 [self.count_grid, self.count_widget],
							 [self.reflec_grid, self.reflec_widget]]:
			layout = QtGui.QVBoxLayout()
			layout.addLayout(grid)
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
		self.vbox.addStretch(1)
		self.hbox.addLayout(self.vbox)
		self.hbox.addWidget(self.canvas)
		self.canvas.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding))
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
		self.laserpower = QtGui.QDoubleSpinBox()
		self.manualatten = QtGui.QCheckBox('Manual?')
		self.atten = QtGui.QLineEdit('')
		self.wavelength = QtGui.QLineEdit('')
		self.dcr = QtGui.QLineEdit('')

		self.dateandtime.setEnabled(False)
		self.manualtemp.stateChanged.connect(self.temp.setEnabled)
		self.manualbias.stateChanged.connect(self.bias.setEnabled)
		self.temp.setEnabled(False)
		self.bias.setEnabled(False)
		self.manualatten.stateChanged.connect(self.atten.setEnabled)
		self.manualatten.stateChanged.connect(self.wavelength.setEnabled)
		self.laserpower.setSuffix('dBm')
		self.laserpower.setRange(-200,20)
		self.laserpower.setSpecialValueText('Not measured')
		self.laserpower.setValue(-200)
		self.laserpower.setAccelerated(True)
		self.atten.setEnabled(False)
		self.wavelength.setEnabled(False)

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
		self.subgrid1.addWidget(QtGui.QLabel('K'),0,3)
		self.subgrid1.addWidget(self.manualbias,1,0)
		self.subgrid1.addWidget(QtGui.QLabel('Bias:'),1,1)
		self.subgrid1.addWidget(self.bias,1,2)
		self.subgrid1.addWidget(QtGui.QLabel('V'),1,3)
		self.subgrid1.addWidget(self.manualatten,2,0)
		self.subgrid1.addWidget(QtGui.QLabel('Atten:'),2,1)
		self.subgrid1.addWidget(self.atten,2,2)
		self.subgrid1.addWidget(QtGui.QLabel('dB'),2,3)
		self.subgrid1.addWidget(QtGui.QLabel(u'λ:'),3,1)
		self.subgrid1.addWidget(self.wavelength,3,2)
		self.subgrid1.addWidget(QtGui.QLabel('nm'),3,3)

		self.metadata_grid.addLayout(self.subgrid1,2,2,4,2)
		self.metadata_grid.addWidget(QtGui.QLabel('Comments:'),3,0)
		self.metadata_grid.addWidget(self.comment,3,1)
		self.metadata_grid.addWidget(QtGui.QLabel('Laser power:'),4,0)
		self.metadata_grid.addWidget(self.laserpower,4,1)
		self.metadata_grid.addWidget(QtGui.QLabel('DCR:'),5,0)
		self.metadata_grid.addWidget(self.dcr,5,1)

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

		self.key_object_map = {
								'username': self.username,
								'dateandtime': self.dateandtime,
								'batchName': self.batchName,
								'deviceId': self.deviceId,
								'sma': self.sma,
								'manualtemp': self.manualtemp,
								'temp': self.temp,
								'comment': self.comment,
								'manualbias': self.manualbias,
								'bias': self.bias,
								'laserpower': self.laserpower,
								'manualatten': self.manualatten,
								'atten': self.atten,
								'wavelength': self.wavelength,
								'dcr': self.dcr,
								'xfrom_m':self.xfrom_m,
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
		for key in self.key_object_map.keys():
			if isinstance(self.key_object_map[key],QtGui.QLineEdit):
				self.key_object_map[key].setText(str(self.settings['DEFAULTS'][key]))
				self.key_object_map[key].textChanged.connect(self.setNeedsSaving)
			elif isinstance(self.key_object_map[key],QtGui.QCheckBox):
				self.key_object_map[key].setChecked(self.settings['DEFAULTS'][key])
				self.key_object_map[key].stateChanged.connect(self.setNeedsSaving)
			elif isinstance(self.key_object_map[key],QtGui.QSpinBox) or isinstance(self.key_object_map[key],QtGui.QDoubleSpinBox):
				self.key_object_map[key].setValue(self.settings['DEFAULTS'][key])
				self.key_object_map[key].valueChanged.connect(self.setNeedsSaving)

	def setNeedsSaving(self,**kwargs):
		if 'reset' in kwargs.keys() and kwargs['reset'] == True:
			self.setWindowModified(False)
		else:
			self.setWindowModified(True)

	def checkNeedsSaving(self, event=None):
		if self.isWindowModified():
			if self.filename == '':
				self.question = 'Do you want to save data?'
			else:
				self.question = 'Do you want to save changes to '+str(self.filename)+'?'
			reply = QtGui.QMessageBox.question(self,'Mapper',
				self.question,QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Save)
			if reply == QtGui.QMessageBox.Discard:
				if event != None:
					event.accept()
				return False
			elif reply == QtGui.QMessageBox.Cancel:
				if event != None:
					event.ignore()
				return True
			elif reply == QtGui.QMessageBox.Save:
				self.save()
				if event != None:
					event.accept()
				return False
		else:
			if event != None:
				event.accept()
			return False

	def acquire(self):
		#first: work out what measurement we're trying to run
		#by finding which tabs are selected
		if self.data != []:
			reply = QtGui.QMessageBox.question(self,'Mapper',
				'Overwrite existing dataset?',QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Cancel)
			if reply == QtGui.QMessageBox.Cancel:
				self.statusBar().showMessage('Measurement cancelled')
				return
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
			self.meas_par['mover'] = movement.findClass(self.settings['DEVICES']['motortype'])()

		elif 's' in self.meas_par['mtype']:
			self.meas_par['mover'] = movement.findClass(self.settings['DEVICES']['scannertype'])()

		
		if 'r' in self.meas_par['mtype']:
			self.meas_par['measurer'] = measurement.findClass(self.settings['DEVICES']['reflectype'])()

		elif 'c' in self.meas_par['mtype']:
			self.meas_par['measurer'] = measurement.findClass(self.settings['DEVICES']['countertype'])()

		if not any(x in self.meas_par['mover'].devicetype for x in self.meas_par['mtype']):
			self.statusBar().showMessage('Movement device different type from expected! Check settings. Aborting...')
			return
		if not any(x in self.meas_par['measurer'].devicetype for x in self.meas_par['mtype']):
			self.statusBar().showMessage('Measurement device different type from expected! Check settings. Aborting...')
			return


		#perform final metadata stuff
		if not self.manualtemp.isChecked() or not self.manualbias.isChecked():
			self.sim900 = Sim900(self.settings['DEVICES']['sim900addr'])
			self.sim900check = self.sim900.check()
			if type(self.sim900check) != str:
				self.sim900 = Sim900(self.settings['DEVICES']['sim900addr'])
				if not self.manualtemp.isChecked():
					self.temp.setText('%.2f' % float(self.sim900.query(self.settings['DEVICES']['tsourcemod'],'TVAL? '+str(self.settings['DEVICES']['tinput'])+',1')))
				if not self.manualbias.isChecked():
					self.bias.setText(str(float(self.sim900.query(self.settings['DEVICES']['vsourcemod'],'VOLT?'))*int(self.sim900.query(self.settings['DEVICES']['vsourcemod'],'EXON?'))))
				self.sim900.close()

		if not self.manualatten.isChecked():
			self.set_wavelength = None
			self.set_attenuation = 0
			for attenaddr in [self.settings['DEVICES']['att1addr'],self.settings['DEVICES']['att2addr']]:
				self.attenuator_device = Attenuator(attenaddr)
				self.attencheck = self.attenuator_device.check()
				if type(self.attencheck) != str:
					self.set_attenuation += float(self.attenuator_device.query(':INP:ATT?').strip('\x00'))
					if self.set_wavelength == None:
						self.set_wavelength = float(self.attenuator_device.query(':INP:WAV?'))
					elif self.set_wavelength != float(self.attenuator_device.query(':INP:WAV?')):
						self.statusBar().showMessage('Warning: attenuators disagree on wavelength!')
						return
					self.attenuator_device.close()
				else:
					self.statusBar().showMessage('Warning: problem communicating to attenuator on: '+str(attenaddr))
					return
			self.atten.setText(str(self.set_attenuation))
			self.wavelength.setText(str(self.set_wavelength*1e9))
		self.dateandtime.setText(time.asctime())
		self.haltAction.setEnabled(True)
		self.acquireAction.setEnabled(False)

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
		self.mapper_drone.xSteps.connect(self.getXSteps)
		self.mapper_drone.ySteps.connect(self.getYSteps)
		self.x_steps = None
		self.y_steps = None
		self.setNeedsSaving()
		self.obj_thread.start()
		#print 'launched'

	def getData(self, data):
		self.data.append(data)
		self.updatePreviewGrid()

	def getXSteps(self,x_steps):
		self.x_steps = x_steps

	def getYSteps(self,y_steps):
		self.y_steps = y_steps

	def updatePreviewGrid(self):
		plt.figure('preview')
		self.data_array = np.array(self.data).transpose()
		if any(x in 'mM' for x in self.meas_par['mtype']):
			self.ax.set_xlabel('X position (mm)')
			self.ax.set_ylabel('Y position (mm)')
		elif any(x in 's' for x in self.meas_par['mtype']):
			self.ax.set_xlabel('X position (V)')
			self.ax.set_ylabel('Y position (V)')


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
		self.fig.tight_layout()
		self.canvas.draw()

	def checkForGraph(self):
		try:
			self.canvas
		except AttributeError:
			self.data = np.array([[]])
			self.fig = plt.figure('preview',figsize = (4.5,4), dpi=72, facecolor=(1,1,1), edgecolor=(0,0,0))
			self.ax = self.fig.add_subplot(1,1,1)
			#self.plot = plt.tricontourf(self.data)#*self.data)
			#self.ax.set_ylabel('dunno')
			#self.ax.set_xlabel('nobody told me')
			self.canvas = FigureCanvas(self.fig)
			self.fig.tight_layout()

	def acquisitionFinished(self):
		self.haltAction.setEnabled(False)
		self.acquireAction.setEnabled(True)

	def new(self,save_already_checked = False):
		if save_already_checked == True or self.checkNeedsSaving() == False:
			self.setDefaults()
			self.newSequential(True)


	def newSequential(self,save_already_checked=False):
		if save_already_checked == True or self.checkNeedsSaving() == False:
			self.filename = ''
			self.setNewDataset([])
			self.meas_par = None
			self.dateandtime.setText('')
			self.setNeedsSaving(reset=True)
			self.updateWindowTitle()
			self.statusBar().showMessage('Begun next dataset')

	def open(self):
		self.filename_open, _ = QtGui.QFileDialog.getOpenFileName(self,'Open file...',self.settings['targetfolder'],"I-V data (*.txt);;All data (*.*)")
		if self.checkNeedsSaving() == False:
			if self.filename_open != '':
				#self.new(True)
				self.filename = self.filename_open
				self.settings['targetfolder'] = self.filename
				with open(self.filename,'r') as f:
					try:
						self.loaded_data = json.loads(f.read())
					except ValueError as e:
						self.statusBar().showMessage('Problem loading file '+str(self.filename))
						reply = QtGui.QMessageBox.question(self,'Mapper', 'Problem loading '+str(self.filename)+':\n'+str(e),
								QtGui.QMessageBox.Ok)
						return
				self.processMetadata(self.loaded_data['metadata'])
				self.setNewDataset(self.loaded_data['data'])

				try:
					if 'mtype' in self.meas_par.keys():
						if 'm' in self.meas_par['mtype'] or 'M' in self.meas_par['mtype']:
							self.movement_tab.setCurrentWidget(self.motor_widget)
						elif 's' in self.meas_par['mtype']:
							self.movement_tab.setCurrentWidget(self.scanner_widget)
						if 'c' in self.meas_par['mtype']:
							self.measurement_tab.setCurrentWidget(self.count_widget)
						elif 'r' in self.meas_par['mtype']:
							self.measurement_tab.setCurrentWidget(self.reflec_widget)
				except AttributeError:
					pass


				self.setNeedsSaving(reset=True)
				self.statusBar().showMessage('Loaded '+str(self.filename))
				self.updateWindowTitle()

	def setNewDataset(self,data):
		self.data = data
		if self.data != []:
			self.updatePreviewGrid()
		else:
			try:
				self.img.set_data([[]])
				self.img.set_extent([0,0.000001,0,0.000001])
				self.canvas.draw()
			except AttributeError:
				pass

	def save(self):
		if self.filename == '':
			self.saveAs()
		else:
			with open(self.filename,'w') as f:
				f.write(json.dumps({'metadata':self.processMetadata(),'data':self.data},default=convert_to_builtin_type))
			self.statusBar().showMessage('Saved to '+str(self.filename))
			self.updateWindowTitle()
			self.setNeedsSaving(reset=True)


	def saveAs(self):
		self.filename, _ = QtGui.QFileDialog.getSaveFileName(self,'Save as...',self.settings['targetfolder'],"Mapper data (*.txt);;All data (*.*)")
		if self.filename != '':
			self.folder_for_dialogs = self.filename
			self.save()

	def updateWindowTitle(self):
		if self.filename == '':
			self.setWindowTitle(self.name_of_application + '[*]')
		else:
			self.setWindowTitle(self.name_of_application+' - '+os.path.basename(self.filename) + '[*]')

	def halt(self):
		self.haltAction.setEnabled(False)
		self.acquireAction.setEnabled(True)
		self.mapper_drone.abort = True

	def plotExternal(self):
		self.plotWindow = MapperPlot(self.data,self.processMetadata(),self.settings,self.filename)
		self.plotWindow.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
		self.plotWindow.hide()
		self.plotWindow.show()

	def processMetadata(self,source=None):
		#bundles values in the plotter screen for display in plotter and saving/loading
		if source != None:
			for key in source.keys():
				if key not in ['meas_par','x_steps','y_steps','x_forward','y_forward']:
					if isinstance(self.key_object_map[key],QtGui.QLineEdit):
						self.key_object_map[key].setText(source[key])
					if isinstance(self.key_object_map[key],QtGui.QCheckBox):
						self.key_object_map[key].setChecked(source[key])
					if isinstance(self.key_object_map[key],QtGui.QSpinBox) or isinstance(self.key_object_map[key],QtGui.QDoubleSpinBox):
						if key == 'laserpower':
							if source[key] == 'Not measured':
								self.key_object_map[key].setValue(-float('inf'))
							else:
								self.key_object_map[key].setValue(float(source[key].strip('dBm')))

						else:
							self.key_object_map[key].setValue(float(source[key]))
			try:
				self.meas_par = source['meas_par']
				self.x_steps = source['x_steps']
				self.y_steps = source['y_steps']
				self.x_forward = source['x_forward']
				self.y_forward = source['y_forward']
			except KeyError:
				self.meas_par = {}
				del self.meas_par

		else:
			self.appstate = {
				'username':self.username.text(),
				'dateandtime':self.dateandtime.text(),
				'batchName':self.batchName.text(),
				'deviceId':self.deviceId.text(),
				'sma':self.sma.text(),
				'manualtemp':self.manualtemp.isChecked(),
				'temp':self.temp.text(),
				'comment':self.comment.text(),
				'manualbias':self.manualbias.isChecked(),
				'bias':self.bias.text(),
				'manualatten':self.manualatten.isChecked(),
				'atten':self.atten.text(),
				'wavelength':self.wavelength.text(),
				'laserpower':self.laserpower.text(),
				'dcr':self.dcr.text(),
				'xfrom_m':self.xfrom_m.text(),
				'xto_m':self.xto_m.text(),
				'yfrom_m':self.yfrom_m.text(),
				'yto_m':self.yto_m.text(),
				'volt_m':self.volt_m.text(),
				'freq_m':self.freq_m.text(),
				'readv_m':self.readv_m.text(),
				'clicks_m':self.clicks_m.text(),
				'numpoints_m':self.numpoints_m.text(),
				'closedloop_m':self.closedloop_m.isChecked(),
				'xfrom_s':self.xfrom_s.text(),
				'xto_s':self.xto_s.text(),
				'yfrom_s':self.yfrom_s.text(),
				'yto_s':self.yto_s.text(),
				'xvoltstep_s':self.xvoltstep_s.text(),
				'yvoltstep_s':self.yvoltstep_s.text(),
				'meastime_c':self.meastime_c.text(),
				'pausetime_c':self.pausetime_c.text(),
				'meastime_r':self.meastime_r.text(),
				'pausetime_r':self.pausetime_r.text()
				}

			try:
				self.appstate['meas_par']=self.meas_par
				self.appstate['x_steps']=self.x_steps
				self.appstate['y_steps']=self.y_steps
				self.appstate['x_forward']=self.x_forward
				self.appstate['y_forward']=self.y_forward
			except AttributeError:
				self.appstate['meas_par']=None
			return self.appstate


	def export(self):
		self.clipboard = QtGui.QApplication.clipboard()
		self.clipboard_string = ''
		for row in self.data:#
			for col in row:
				self.clipboard_string += str(col) +'\t'
			self.clipboard_string = self.clipboard_string[:-1] +'\n'
		self.clipboard.setText(self.clipboard_string[:-1])
		self.statusBar().showMessage('Raw data copied to clipboard')

	def openSettings(self):
		self.settings_window = SettingsDialog(self.settings,movement.findClass(),measurement.findClass())
		self.settings_window.exec_()


	def helpFile(self):
		self.helpWindow = HelpWindow()
		#self.helpWindow.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
		self.helpWindow.hide()
		self.aboutToQuit.connect(self.helpWindow.close)
		self.helpWindow.show()

	def aboutProgram(self):
		self.aboutBox = QtGui.QMessageBox()
		self.aboutBox.setText("<b>Mapper</b>")
		self.aboutBox.setInformativeText("Written by Rob Heath (rob@robheath.me.uk) at the University of Glasgow in 2015")
		self.aboutBox.setIcon(QtGui.QMessageBox.Information)
		self.aboutBox.setWindowTitle('About program')
		self.aboutBox.exec_()

	def closeEvent(self,event):
		setSettings(self.settings)
		if self.checkNeedsSaving(event) == False:
			self.aboutToQuit.emit()

	def resizeEvent(self,event):
		try:
			self.fig.tight_layout()
			self.canvas.draw()
		except ValueError:
			pass
		except np.linalg.linalg.LinAlgError:
			pass
		event.accept()

class MapperTool(QtGui.QMainWindow):
	def __init__(self):
		super(MapperTool,self).__init__()
		self.initUI()
	aboutToQuit = QtCore.Signal()


	def initUI(self):
		#create UI; maybe use lists? dicts? something more elegant!
		self.createLayoutsAndWidgets()
		self.populateLayouts()

		#finalize things
		self.data = []
		self.setWindowTitle('Mapper Tools')
		self.setWindowIcon(QtGui.QIcon(r'icons\mapper.png'))
		self.statusBar().showMessage('Ready...')
		self.show()

	def createLayoutsAndWidgets(self):
		self.tool_grid = QtGui.QGridLayout()
		self.tool_widget = QtGui.QGroupBox('Move to')

		self.scan_grid = QtGui.QGridLayout()
		self.scan_widget = QtGui.QGroupBox('Continous reflection')

		for grid, widget in [[self.tool_grid, self.tool_widget],
							 [self.scan_grid, self.scan_widget]]:
			layout = QtGui.QVBoxLayout()
			layout.addLayout(grid)
			widget.setLayout(layout)
			widget.setFixedWidth(250)
	
		self.checkForGraph() #does the graph

		self.hbox = QtGui.QHBoxLayout()
		self.vbox = QtGui.QVBoxLayout()
		self.vbox.addWidget(self.tool_widget)
		self.vbox.addWidget(self.scan_widget)
		self.vbox.addStretch(1)
		self.hbox.addLayout(self.vbox)
		self.hbox.addWidget(self.canvas)
		self.canvas.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding))

		self.main_widget = QtGui.QWidget()
		self.main_widget.setLayout(self.hbox)
		self.setCentralWidget(self.main_widget)

	def populateLayouts(self):
		self.x_m = QtGui.QLineEdit('')
		self.y_m = QtGui.QLineEdit('')
		self.move = QtGui.QPushButton('Go')

		self.tool_grid.addWidget(QtGui.QLabel('X:'),0,0)
		self.tool_grid.addWidget(self.x_m,0,1)
		self.tool_grid.addWidget(QtGui.QLabel('Y:'),0,2)
		self.tool_grid.addWidget(self.y_m,0,3)
		self.tool_grid.addWidget(self.move,1,0,1,4)

		#populate scanner grid
		self.xfrom_s = QtGui.QLineEdit('')
		self.xto_s = QtGui.QLineEdit('')
		self.yfrom_s = QtGui.QLineEdit('')
		self.yto_s = QtGui.QLineEdit('')
		self.xvoltstep_s = QtGui.QLineEdit('')
		self.yvoltstep_s = QtGui.QLineEdit('')
		self.scan = QtGui.QPushButton('Run')

		self.scan_grid.addWidget(QtGui.QLabel('X range:'),1,0)
		self.scan_grid.addWidget(self.xfrom_s,1,1)
		self.scan_grid.addWidget(QtGui.QLabel('->'),1,2)
		self.scan_grid.addWidget(self.xto_s,1,3)
		self.scan_grid.addWidget(QtGui.QLabel('Y range:'),2,0)
		self.scan_grid.addWidget(self.yfrom_s,2,1)
		self.scan_grid.addWidget(QtGui.QLabel('->'),2,2)
		self.scan_grid.addWidget(self.yto_s,2,3)

		self.scan_grid.addWidget(QtGui.QLabel('X step:'),3,0)
		self.scan_grid.addWidget(self.xvoltstep_s,3,1)
		self.scan_grid.addWidget(QtGui.QLabel('Y step:'),3,2)
		self.scan_grid.addWidget(self.yvoltstep_s,3,3)

		self.scan_grid.addWidget(self.scan,4,0,1,4)

	def checkForGraph(self):
		try:
			self.canvas
		except AttributeError:
			self.data = np.array([[]])
			self.fig = plt.figure('preview',figsize = (4.5,4), dpi=72, facecolor=(1,1,1), edgecolor=(0,0,0))
			self.ax = self.fig.add_subplot(1,1,1)
			self.canvas = FigureCanvas(self.fig)
			self.fig.tight_layout()

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
			'b':{
				''
				't':'Metadata',
				'w': QtGui.QFormLayout(),
				'v':'DEFAULTS',
				'c': {
					'a':{
						't': 'Username:',
						'w': QtGui.QLineEdit(),
						'v': 'username'
						},
					'c':{
						't': 'Batch:',
						'w': QtGui.QLineEdit(),
						'v': 'batchName'
						},
					'd':{
						't': 'Device:',
						'w': QtGui.QLineEdit(),
						'v': 'deviceId'
						},
					'e':{
						't': 'SMA:',
						'w': QtGui.QLineEdit(),
						'v': 'sma'
						},
					'f':{
						't': 'Manual temp:',
						'w': QtGui.QCheckBox(),
						'v': 'manualtemp'
						},
					'g':{
						't': 'Temp (K):',
						'w': QtGui.QLineEdit(),
						'v': 'temp'
						},
					'h':{
						't': 'Comment',
						'w': QtGui.QLineEdit(),
						'v': 'comment'
						},
					'i':{
						't': 'Manual bias:',
						'w': QtGui.QCheckBox(),
						'v': 'manualbias'
						},
					'j':{
						't': 'Bias (V):',
						'w': QtGui.QLineEdit(),
						'v': 'bias'
						},
					'k':{
						't': 'Laser power:',
						'w': QtGui.QDoubleSpinBox(),
						'v': 'laserpower'
						},
					'l':{
						't': 'Manual attenuation:',
						'w': QtGui.QCheckBox(),
						'v': 'manualatten'
						},
					'm':{
						't': 'Attenuation (dB):',
						'w': QtGui.QLineEdit(),
						'v': 'atten'
						},
					'n':{
						't': 'Wavelength (nm)',
						'w': QtGui.QLineEdit(),
						'v': 'wavelength'
						}
					}
				},
			'a':{
				't':'Devices',
				'w':QtGui.QFormLayout(),
				'v':'DEVICES',
				'c':{
					'a':{
						't':'Scanner type:',
						'w': QtGui.QComboBox(),
						'p': self.movers,
						'v':'scannertype'
						},
					'b':{
						't':'Motor type:',
						'w': QtGui.QComboBox(),
						'p': self.movers,
						'v':'motortype'
						},
					'c':{
						't':'Counter type:',
						'w': QtGui.QComboBox(),
						'p': self.measurers,
						'v':'countertype'
						},
					'd':{
						't':'Reflection type:',
						'w': QtGui.QComboBox(),
						'p': self.measurers,
						'v':'reflectype'
						},
					'e':{
						't':'SIM900 address:',
						'w':QtGui.QLineEdit(),
						'v':'sim900addr'
						},
					'f':{
						't':'SIM928 voltage source module:',
						'w':QtGui.QSpinBox(),
						'v':'vsourcemod'
						},
					'g':{
						't':'SIM922 temperature module:',
						'w':QtGui.QSpinBox(),
						'v':'tsourcemod'
						},
					'h':{
						't':'SIM922 sensor channel:',
						'w':QtGui.QSpinBox(),
						'v':'tinput'
						},
					'i':{
						't':'Attenuator 1 address:',
						'w':QtGui.QLineEdit(),
						'v':'att1addr'
						},
					'j':{
						't':'Attenuator 2 address:',
						'w':QtGui.QLineEdit(),
						'v':'att2addr'
						}
					}
				},
			'c':{
				't':'Motor',
				'w':QtGui.QFormLayout(),
				'v':'DEFAULTS',
				'c':{
					'a':{
						't':'X from:',
						'w':QtGui.QLineEdit(),
						'v':'xfrom_m'
						},
					'b':{
						't':'X to:',
						'w':QtGui.QLineEdit(),
						'v':'xto_m'
						},
					'c':{
						't':'Y from:',
						'w':QtGui.QLineEdit(),
						'v':'yfrom_m'
						},
					'd':{
						't':'Y to:',
						'w':QtGui.QLineEdit(),
						'v':'yto_m'
						},
					'e':{
						't':'Move voltage:',
						'w':QtGui.QSpinBox(),
						'v':'volt_m'
						},
					'f':{
						't':'Motor move frequency:',
						'w':QtGui.QSpinBox(),
						'v':'freq_m'
						},
					'h':{
						't':'Read voltage:',
						'w':QtGui.QDoubleSpinBox(),
						'v':'readv_m'
						},
					'g':{
						't':'Move clicks:',
						'w':QtGui.QSpinBox(),
						'v':'clicks_m'
						},
					'i':{
						't':'Closed loop:',
						'w':QtGui.QCheckBox(),
						'v':'closedloop_m'
						},
					'j':{
						't':'Closed loop points',
						'w':QtGui.QSpinBox(),
						'v':'numpoints_m'
						}
					}
				},
			'd':{
				't':'Scanner',
				'w':QtGui.QFormLayout(),
				'v':'DEFAULTS',
				'c':{
					'k':{
						't':'X from:',
						'w':QtGui.QLineEdit(),
						'v':'xfrom_s'
						},
					'l':{
						't':'X to:',
						'w':QtGui.QLineEdit(),
						'v':'xto_s'
						},
					'm':{
						't':'Y from:',
						'w':QtGui.QLineEdit(),
						'v':'yfrom_s'
						},
					'n':{
						't':'Y to:',
						'w':QtGui.QLineEdit(),
						'v':'yto_s'
						},
					'o':{
						't':'X voltage step:',
						'w':QtGui.QDoubleSpinBox(),
						'v':'xvoltstep_s'
						},
					'p':{
						't':'Y voltage step:',
						'w':QtGui.QDoubleSpinBox(),
						'v':'yvoltstep_s'
						}
					}
				},
			'e':{
				't':'Measurement',
				'w':QtGui.QFormLayout(),
				'v':'DEFAULTS',
				'c':{
					'q':{
						't':'Counter measurement time:',
						'w':QtGui.QLineEdit(),
						'v':'meastime_c'
						},
					'r':{
						't':'Counter pause time:',
						'w':QtGui.QLineEdit(),
						'v':'pausetime_c'
						},
					's':{
						't':'Reflection measurement time:',
						'w':QtGui.QLineEdit(),
						'v':'meastime_r'
						},
					't':{
						't':'Reflection pause time:',
						'w':QtGui.QLineEdit(),
						'v':'pausetime_r'
						}
					}
				},
			'f':{
				't':'Export',
				'w':QtGui.QFormLayout(),
				'v':'EXPORT',
				'c':{
					'a':{
						't':'Add title:',
						'w':QtGui.QCheckBox(),
						'v':'title'
						},
					'b1':{
						't':'Convert counts map to SDE:',
						'w':QtGui.QCheckBox(),
						'v':'convert_to_sde'
						},
					'b2':{
						't':'Verbose graph:',
						'w':QtGui.QCheckBox(),
						'v':'verbose'
						},
					'c':{
						't':'Manually-defined axis limits:',
						'w':QtGui.QCheckBox(),
						'v':'manual_axes'
						},
					'd':{
						't':'Xmax:',
						'w':QtGui.QDoubleSpinBox(),
						'v':'xmax'
						},
					'e':{
						't':'Xmin:',
						'w':QtGui.QDoubleSpinBox(),
						'v':'xmin'
						},
					'f':{
						't':'Ymax:',
						'w':QtGui.QDoubleSpinBox(),
						'v':'ymax'
						},
					'g':{
						't':'Ymin:',
						'w':QtGui.QDoubleSpinBox(),
						'v':'ymin'
						},
					'h':{
						't':'Plot type:',
						'w':QtGui.QComboBox(),
						'v':'plot_type',
						'p':['Contour','Filled contour','Grid']
						},
					'i':{
						't':'Show datapoints on contours:',
						'w':QtGui.QCheckBox(),
						'v':'show_datapoints'
						},
					'w':{
						't':'Figure width:',
						'w':QtGui.QDoubleSpinBox(),
						'v':'width'
						},
					'x':{
						't':'Figure height:',
						'w':QtGui.QDoubleSpinBox(),
						'v':'height'
						},
					'y':{
						't':'Width/height units:',
						'w':QtGui.QComboBox(),
						'v':'unit',
						'p': ['in','cm','px']
						},
					'z':{
						't':'Plot dots-per-inch (DPI):',
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
		self.setWindowIcon(QtGui.QIcon(r'icons\settings.png'))
		self.resize(500,500)

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
					if self.childtier['v'] == 'laserpower':
						self.childtier['w'].setMinimum(-200)
						self.childtier['w'].setSpecialValueText('Not measured')
						self.childtier['w'].setSuffix('dBm')
						self.childtier['w'].setValue(self.settings[self.tabtier['v']][self.childtier['v']])
					else:
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

class MapperPlot(QtGui.QMainWindow):
	def __init__(self,data,metadata,settings,filename):
		super(MapperPlot, self).__init__()
		self.data = data
		self.pm = metadata
		self.settings = settings
		self.se = settings['EXPORT']
		self.filename = filename
		try:
			self.meas_par = self.pm['meas_par']
		except KeyError:
			self.meas_par = None
		self.initUI()

	def initUI(self):
		#lay out window
		self.checkForGraph()
		self.createLayoutAndWidgets()
		#set settings from settings
		self.populateLayouts()
		self.connectWidgets()
		#update plot

		#booom shake the roooom
		self.resize(800,600)
		self.setWindowTitle('Mapper Plotter')
		self.setWindowIcon(QtGui.QIcon(r'icons\plot.png'))
		self.showMaximized()
		self.updatePreview()
		self.show()

	def createLayoutAndWidgets(self):
		self.give_title = QtGui.QCheckBox('Graph title')
		self.title = QtGui.QLineEdit(self.autoTitle())
		self.verbose_graph = QtGui.QCheckBox('Verbose graph')
		self.plot_type = QtGui.QComboBox(self)
		self.manual_limits = QtGui.QCheckBox('Manual axes')
		self.x_max = QtGui.QLineEdit('')
		self.x_min = QtGui.QLineEdit('')
		self.y_max = QtGui.QLineEdit('')
		self.y_min = QtGui.QLineEdit('')
		self.convert_to_sde = QtGui.QCheckBox('Convert to SDE')
		self.exp_width = QtGui.QLineEdit('8')
		self.exp_height = QtGui.QLineEdit('6')
		self.dpi = QtGui.QLineEdit('150')
		self.exp_units = QtGui.QComboBox(self)
		self.possible_units = ['in','cm','px']
		for unit in self.possible_units:
			self.exp_units.addItem(unit)
		self.possible_plots = ['Contour','Filled contour','Grid']
		for plot in self.possible_plots:
			self.plot_type.addItem(plot)
		self.show_datapoints = QtGui.QCheckBox('Show datapoints')

		self.checkables = [ ['title',self.give_title],
							['verbose',self.verbose_graph],
							['manual_axes',self.manual_limits],
							['show_datapoints',self.show_datapoints],
							['convert_to_sde',self.convert_to_sde]]

		self.textables = [  ['ymax',self.y_max],
							['ymin',self.y_min],
							['xmax',self.x_max],
							['xmin',self.x_min],
							['width',self.exp_width],
							['height',self.exp_height],
							['dpi',self.dpi]]

		self.resetButton = QtGui.QPushButton('Reset')
		self.closeButton = QtGui.QPushButton('Close')
		self.exportButton = QtGui.QPushButton('Export')

		self.manual_limits_widget = QtGui.QGroupBox()
		self.manual_limits_widget.manual_grid = QtGui.QGridLayout()
		self.manual_limits_widget.setLayout(self.manual_limits_widget.manual_grid)
		self.manual_limits_widget.manual_grid.addWidget(QtGui.QLabel('X<sub>min</sub>'),0,0)
		self.manual_limits_widget.manual_grid.addWidget(self.x_min,0,1)
		self.manual_limits_widget.manual_grid.addWidget(QtGui.QLabel('X<sub>max</sub>'),0,2)
		self.manual_limits_widget.manual_grid.addWidget(self.x_max,0,3)
		self.manual_limits_widget.manual_grid.addWidget(QtGui.QLabel('Y<sub>min</sub>'),1,0)
		self.manual_limits_widget.manual_grid.addWidget(self.y_min,1,1)
		self.manual_limits_widget.manual_grid.addWidget(QtGui.QLabel('Y<sub>max</sub>'),1,2)
		self.manual_limits_widget.manual_grid.addWidget(self.y_max,1,3)
		self.manual_limits_widget.setVisible(False)

		self.title_widget = QtGui.QGroupBox()
		self.title_widget.title_grid = QtGui.QGridLayout()
		self.title_widget.setLayout(self.title_widget.title_grid)
		self.title_widget.title_grid.addWidget(QtGui.QLabel('Title:'),0,0)
		self.title_widget.title_grid.addWidget(self.title,0,1)
		self.title_widget.setVisible(False)

		self.export_widget = QtGui.QGroupBox('Export settings')
		self.export_widget.export_grid = QtGui.QGridLayout()
		self.export_widget.setLayout(self.export_widget.export_grid)
		self.export_widget.export_grid.addWidget(QtGui.QLabel('Width:'),0,0)
		self.export_widget.export_grid.addWidget(self.exp_width,0,1)
		self.export_widget.export_grid.addWidget(QtGui.QLabel('Height:'),0,2)
		self.export_widget.export_grid.addWidget(self.exp_height,0,3)
		self.export_widget.export_grid.addWidget(QtGui.QLabel('DPI:'),1,0)
		self.export_widget.export_grid.addWidget(self.dpi,1,1)
		self.export_widget.export_grid.addWidget(QtGui.QLabel('Units:'),1,2)
		self.export_widget.export_grid.addWidget(self.exp_units,1,3)

		self.panel_widget = QtGui.QWidget()
		self.panel_widget.vbox = QtGui.QVBoxLayout()
		self.panel_widget.setLayout(self.panel_widget.vbox)
		self.panel_widget.setFixedWidth(200)

		self.gridsection1 = QtGui.QGridLayout()
		self.gridsection2 = QtGui.QGridLayout()
		self.gridsection3 = QtGui.QGridLayout()
		#self.vbox = QtGui.QVBoxLayout()
		self.hbox = QtGui.QHBoxLayout()

		self.gridsection1.setSpacing(10)
		self.gridsection1.addWidget(self.give_title,0,0)

		self.bottombar = QtGui.QHBoxLayout()
		self.bottombar.addWidget(self.exportButton)
		self.bottombar.addWidget(self.resetButton)
		self.bottombar.addWidget(self.closeButton)

		self.gridsection2.addWidget(self.verbose_graph,0,0)
		self.gridsection2.addWidget(self.manual_limits,1,0)

		self.gridsection3.addWidget(QtGui.QLabel('Plot type:'),0,0)
		self.gridsection3.addWidget(self.plot_type,0,1)

		self.sdp_widget = QtGui.QGroupBox('Contour settings')
		self.sdp_widget.sdp_grid = QtGui.QGridLayout()
		self.sdp_widget.setLayout(self.sdp_widget.sdp_grid)
		self.sdp_widget.sdp_grid.addWidget(self.show_datapoints,0,0)
		self.sdp_widget.setVisible(False)

		self.panel_widget.vbox.addLayout(self.gridsection1)
		self.panel_widget.vbox.addWidget(self.title_widget)
		if self.meas_par != None and 'c' in self.meas_par['mtype']:
			if self.pm['wavelength'] != '' and self.pm['laserpower'] != 'Not measured' \
				and self.pm['atten'] != '' and self.pm['dcr']!= '':
				self.panel_widget.vbox.addWidget(self.convert_to_sde)
			else:
				self.panel_widget.vbox.addWidget(self.convert_to_sde)
				self.convert_to_sde.setDisabled(True)
				self.convert_to_sde.setChecked(False)
				self.statusBar().showMessage('Unable to calculate SDE: insufficient data (power/attenuation/wavelength/dcr)')
		elif self.meas_par != None and 'c' not in self.meas_par['mtype']:
			self.convert_to_sde.setDisabled(True)
			self.convert_to_sde.setChecked(False)

		self.panel_widget.vbox.addLayout(self.gridsection2)
		self.panel_widget.vbox.addWidget(self.manual_limits_widget)
		self.panel_widget.vbox.addLayout(self.gridsection3)
		self.panel_widget.vbox.addWidget(self.sdp_widget)
		self.panel_widget.vbox.addWidget(self.export_widget)
		self.panel_widget.vbox.addStretch(1)
		self.panel_widget.vbox.addLayout(self.bottombar)

		self.scroll_area = QtGui.QScrollArea()
		self.scroll_area.setBackgroundRole(QtGui.QPalette.Dark)
		self.scroll_area.setAlignment(QtCore.Qt.AlignCenter)
		self.scroll_area.setWidget(self.canvas)

		self.hbox.addWidget(self.scroll_area)
		self.hbox.addWidget(self.panel_widget)

		self.mainthing = QtGui.QWidget()
		self.setCentralWidget(self.mainthing)
		self.mainthing.setLayout(self.hbox)

	def connectWidgets(self):
		self.verbose_graph.stateChanged.connect(self.checkVerbosity)

		self.manual_limits.toggled.connect(self.manual_limits_widget.setVisible)
		self.manual_limits.toggled.connect(self.replot)
		self.x_max.textChanged.connect(self.replot)
		self.x_min.textChanged.connect(self.replot)
		self.y_max.textChanged.connect(self.replot)
		self.y_min.textChanged.connect(self.replot)

		self.give_title.toggled.connect(self.title_widget.setVisible)
		self.title.textChanged.connect(self.checkTitle)
		self.give_title.toggled.connect(self.checkTitle)

		self.plot_type.activated.connect(self.updatePreview)
		self.plot_type.activated.connect(self.plotTypeOptions)
		self.show_datapoints.toggled.connect(self.updatePreview)
		self.convert_to_sde.toggled.connect(self.updatePreview)

		self.exp_units.activated.connect(self.updateCanvasSize)
		self.exp_width.textChanged.connect(self.updateCanvasSize)
		self.exp_height.textChanged.connect(self.updateCanvasSize)
		self.dpi.textChanged.connect(self.updateCanvasSize)

		self.closeButton.clicked.connect(self.close)
		self.resetButton.clicked.connect(self.resetPlot)
		self.exportButton.clicked.connect(self.exportGraph)

	def populateLayouts(self):
		for value in self.checkables:
			value[1].setChecked(self.se[value[0]])
		for value in self.textables:
			if self.se[value[0]] == None:
				value[1].setText('')
			else:
				value[1].setText(str(self.se[value[0]]))
		self.exp_units.setCurrentIndex(self.possible_units.index(self.se['unit']))
		self.plot_type.setCurrentIndex(self.possible_plots.index(self.se['plot_type']))
		self.plotTypeOptions()

	def autoTitle(self):
		self.titlestring = 'Map'
		if self.pm['batchName'] != '' or self.pm['deviceId']!= '':
			self.titlestring += ' of'
			if self.pm['batchName'] != '':
				self.titlestring += ' '+self.pm['batchName']
			if self.pm['deviceId'] != '':
				self.titlestring += ' '+self.pm['deviceId']
		if self.pm['sma'] != '':
			self.titlestring += ' SMA'+self.pm['sma']+' '
		if self.pm['temp'] != '':
			self.titlestring += 'at '+self.pm['temp']+'K '
		if self.pm['temp'] != '':
			self.titlestring += 'biased at '+self.pm['bias']+'V '
		if self.pm['dateandtime'] != '' or self.pm['username'] != '':
			self.titlestring += '\n'
			if self.pm['username'] != '':
				self.titlestring += 'Data taken by '+self.pm['username']
			if self.pm['dateandtime'] != '':
				self.titlestring += ' on '+self.pm['dateandtime']
		return self.titlestring

	def plotTypeOptions(self):
		if self.plot_type.currentText() in ['Contour','Filled contour']:
			self.sdp_widget.setVisible(True)
		else:
			self.sdp_widget.setVisible(False)

	def updatePreview(self):
		if self.meas_par != None:
			plt.figure('plotter')
			self.data_array = np.array(self.data).transpose()
			if self.checkSde() != False:
				self.data_array[4] -= self.dc
				for i, item in enumerate(self.data_array[4]):
					if item < 0:
						self.data_array[4][i] = 0.0
				self.data_array[4] *= self.scaling_factor
			#print 'current plot type:',self.plot_type.currentText()
			if self.plot_type.currentText() == 'Grid':
				self.fig.clear()
				self.ax = self.fig.add_subplot(1,1,1)
				self.extent = [self.data_array[0].min(), self.data_array[0].max(), self.data_array[1].min(),self.data_array[1].max()]
				if self.pm['x_steps'] != None:
					self.z_data = [list(self.data_array[4][x:x+self.pm['x_steps']]) for x in range(0,len(self.data_array[4]),self.pm['x_steps'])]
					if len(self.z_data[-1]) < self.pm['x_steps']:
						self.z_data[-1] += [np.nan]*(self.pm['x_steps'] - len(self.z_data[-1]))
					self.extent[1] = max([self.data_array[0].max(),self.meas_par['xt'],self.meas_par['xf']])
					self.extent[0] = min([self.data_array[0].min(),self.meas_par['xt'],self.meas_par['xf']])
					if self.pm['y_steps'] != None and len(self.z_data) < self.pm['y_steps']:
						self.z_data += [[np.nan]*self.pm['x_steps']]*(self.pm['y_steps']-len(self.z_data))
						self.extent[3] = max([self.data_array[1].max(),self.meas_par['yt'],self.meas_par['yf']])
						self.extent[2] = min([self.data_array[1].min(),self.meas_par['yt'],self.meas_par['yf']])
				else:
					self.z_data = [list(self.data_array[4])]
				if self.extent[2] == self.extent[3]:
					self.extent[3] += 0.000001
				if self.extent[0] == self.extent[1]:
					self.extent[1] += 0.000001
				#correct for swapped .extents()
				if not self.pm['x_forward']:
					for r, row in enumerate(self.z_data):
						self.z_data[r] = row[::-1]
				if self.pm['y_forward']:
					self.z_data = self.z_data[::-1]

				self.img = plt.imshow(self.z_data,extent=self.extent, interpolation='nearest',cmap=colormaps.viridis, aspect='auto')
				self.cbar = plt.colorbar()


			elif self.plot_type.currentText() in ['Contour','Filled contour']:
				self.fig.clear()
				self.ax = self.fig.add_subplot(1,1,1)
				if self.plot_type.currentText() == 'Contour':
					self.plotwith = plt.tricontour
				elif self.plot_type.currentText() == 'Filled contour':
					self.plotwith = plt.tricontourf
				try:
					self.contourf = self.plotwith(self.data_array[0],self.data_array[1],self.data_array[4],cmap=colormaps.viridis)
				except RuntimeError:
					pass
				except ValueError:
					pass
				try:
					self.cbar = plt.colorbar()
				except RuntimeError:
					pass

				print 'began adding datapoints'
				self.start_time = time.time()
				if self.show_datapoints.isChecked():
					self.colordata = []
					for value in [((x-min(self.data_array[4]))/(max(self.data_array[4]-min(self.data_array[4])))) for x in self.data_array[4]]:
						self.colordata.append(colormaps.viridis(value))
					print 'finished doing colordata at:',time.time()-self.start_time
					for v, value in enumerate(self.data_array[0]):
						self.plot = plt.plot([self.data_array[0][v]], [self.data_array[1][v]],'o',color=self.colordata[v],ms=10)
					print 'finished plotting at:',time.time()-self.start_time
			if self.checkSde() == True:
				self.cbar.set_label('SDE (%)')
			elif 'c' in self.meas_par['mtype'] and self.checkSde() != True:
				self.cbar.set_label('Counts ($s^{-1}$)')
			elif 'r' in self.meas_par['mtype']:
				self.cbar.set_label('Reflection (arbitrary)')

		self.updateCanvasSize()
		self.checkVerbosity()
		self.checkAxes()
		self.checkTitle()

	def checkForGraph(self):
		try:
			self.canvas
		except AttributeError:
			self.fig = plt.figure('plotter',figsize = (8,6), dpi=150, facecolor=(1,1,1), edgecolor=(0,0,0))
			self.ax = self.fig.add_subplot(1,1,1)
			#self.plot = plt.tricontourf(self.data)#*self.data)
			#self.ax.set_ylabel('dunno')
			#self.ax.set_xlabel('nobody told me')
			self.canvas = FigureCanvas(self.fig)

	def checkTitle(self):
		plt.figure('plotter')
		if self.give_title.isChecked():
			self.fig_title = self.fig.suptitle(self.title.text())
			self.fig_title.set_visible(True)
		else:
			self.fig_title.set_visible(False)
		self.replot()

	def replot(self):
		plt.figure('plotter')
		if self.manual_limits.isChecked():
			try:
				float(self.x_min.text())
				float(self.x_max.text())
				self.ax.set_xlim(float(self.x_min.text()),float(self.x_max.text()))
			except ValueError:
				self.ax.set_xlim(auto = True)
			try:
				float(self.y_max.text())
				float(self.y_min.text())
				self.ax.set_ylim(float(self.y_min.text()),float(self.y_max.text()))
			except ValueError:
				self.ax.set_ylim(auto = True)
		else:
			self.ax.set_xlim(auto = True)
			self.ax.set_ylim(auto = True)
			#self.ax.relim()
			self.ax.autoscale_view()

		self.checkAxes()
		self.fig.tight_layout()

		if self.give_title.isChecked():
			try:
				self.base_of_text = self.fig_title.get_window_extent(renderer=self.canvas.renderer).get_points()[0][1]
				self.height_of_plot = float(self.dpi.text())*self.image_height_inches
				self.fig.subplots_adjust(top=((self.base_of_text/self.height_of_plot)-0.015))
			except AttributeError:
				pass

		self.canvas.draw()

	def updateCanvasSize(self):
		self.fig.set_dpi(float(self.dpi.text()))
		self.conversion_factors = {'in':1,'cm':1.0/2.54,'px':(1.0/float(self.dpi.text()))}
		self.image_height_inches = float(self.exp_height.text())*self.conversion_factors[self.exp_units.currentText()]
		self.image_width_inches = float(self.exp_width.text())*self.conversion_factors[self.exp_units.currentText()]
		self.fig.set_size_inches(self.image_width_inches,self.image_height_inches, forward=True)
		self.canvas.resize(float(self.dpi.text())*self.image_width_inches,float(self.dpi.text())*self.image_height_inches)
		self.replot()

	def checkVerbosity(self):
		plt.figure('plotter')
		if self.verbose_graph.isChecked():
			self.textstr = ''
			for key in sorted(self.pm.keys()):
				if key in ['batchName','comment','dateandtime','readv_m','bias','temp','sma','username','deviceId','meas_par','atten','wavelength','laserpower','dcr']:
					if key != 'meas_par':
						self.textstr += str(key)+': '+str(self.pm[key])+'\n'
					elif self.meas_par != None:
						for key2 in sorted(self.pm['meas_par'].keys()):
							if key2 in ['measurer','mover']:
								if type(self.pm[key][key2])!=dict:
									self.textstr += str(key2)+': '+str(self.pm[key][key2].__class__.__name__)+'\n'
								else:
									self.textstr += str(key2)+': '+str(self.pm[key][key2]['__class__'])+'\n'
							else:
								self.textstr += str(key2)+': '+str(self.pm[key][key2])+'\n'
			self.text_on_graph = self.ax.text(0.01, 0.99, self.textstr[:-1], transform = self.ax.transAxes, fontsize = 9,
				verticalalignment = 'top')
		else:
			try:
				self.text_on_graph.remove()
			except:
				pass
		self.replot()

	def checkAxes(self):
		plt.figure('plotter')
		if self.meas_par != None:
			if any(x in 'mM' for x in self.meas_par['mtype']):
				self.ax.set_xlabel('X position (mm)')
				self.ax.set_ylabel('Y position (mm)')
			elif any(x in 's' for x in self.meas_par['mtype']):
				self.ax.set_xlabel('X position (V)')
				self.ax.set_ylabel('Y position (V)')

	def checkSde(self):
		if self.convert_to_sde.isChecked() and self.convert_to_sde.isEnabled():
			try:
				self.lp = float(self.pm['laserpower'].strip('dBm'))
				self.ta = float(self.pm['atten'])
				self.la = float(self.pm['wavelength'])*1e-9
				self.dc = float(self.pm['dcr'])
				self.input_power = 0.001 * (10.0 ** ((self.lp-self.ta)/10.0))
				self.photon_energy = (6.626070040e-34 * 299792458.0) / self.la
				self.scaling_factor = 100 * self.photon_energy / self.input_power
				return True
			except ValueError:
				self.statusBar().showMessage('Unable to convert power/atten/wavelength to number, is there text in the field?')
				return False
		else:
			return False

	def exportGraph(self):
		plt.figure('plotter')
		self.filetype_string = ''
		self.graphical_extensions = []
		for key in sorted(self.canvas.get_supported_filetypes_grouped().keys()):
			self.filetype_string += key + ' ('
			for value in self.canvas.get_supported_filetypes_grouped()[key]:
				self.filetype_string += '*.'+value+' '
				self.graphical_extensions.append(value)
			self.filetype_string = self.filetype_string[:-1]+');;'
		#self.filetype_string = self.filetype_string[:-2]
		self.filetype_string = self.filetype_string + 'Raw text (*.txt)'

		if self.filename == '':
			self.target_path = self.settings['targetfolder']
		else:
			self.target_path = os.path.dirname(self.filename)
		self.filename, _ = QtGui.QFileDialog.getSaveFileName(self,'Save as...',self.target_path,self.filetype_string,'Portable Network Graphics (*.png)')
		if self.filename != '':
			if os.path.splitext(self.filename)[1][1:] in self.graphical_extensions:
				plt.savefig(self.filename,dpi=float(self.dpi.text()))
			else:
				with open(self.filename,'w') as f:
					self.data_for_export = self.data
					if self.checkSde() != False:
						for r, row in enumerate(self.data_for_export):
							self.data_for_export[r][4] -= self.dc
							if self.data_for_export[r][4] < 0:
								self.data_for_export[r][4] == 0.0
							self.data_for_export[r][4] *= self.scaling_factor
					self.csvfile = csv.writer(f,delimiter = ',')
					self.csvfile.writerows(list(np.array(self.data)))
			self.statusBar().showMessage('Graph data saved to: '+str(self.filename))

	def resetPlot(self):
		pass

	def closeEvent(self,event):
		self.fig.clear()
		event.accept()

class HelpWindow(QtGui.QWidget):
	def __init__(self):
		super(HelpWindow,self).__init__()
		self.view = QtWebKit.QWebView(self)
		self.view.load('help\help.html')
		
		self.layout = QtGui.QHBoxLayout()
		self.layout.addWidget(self.view)

		self.setLayout(self.layout)
		self.resize(800,600)
		self.setWindowTitle('Mapper help')
		self.setWindowIcon(QtGui.QIcon(r'icons\help.png'))
		self.show()

def main():
	app = QtGui.QApplication(sys.argv)
	ex = MapperProg()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()