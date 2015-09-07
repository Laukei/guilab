#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import matplotlib
matplotlib.use('Qt4Agg')
import matplotlib.pyplot as plt
import numpy as np
#import math
from PySide import QtGui, QtCore, QtWebKit
#import json
#import time
#import csv
#import os
#!!!!!!!!!!!!!!!!!
#from sim900 import Sim900
#!!!!!!!!!!!!!!!!!
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure



def getSettings():
	pass

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

		plotSettingsAction = QtGui.QAction(QtGui.QIcon(r'icons\plotsettings.png'),'&Plot settings',self)
		plotSettingsAction.setStatusTip('Edit settings for plotter')
		plotSettingsAction.triggered.connect(self.openPlotSettings)

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
		settingsMenu.addAction(plotSettingsAction)
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

		self.movement_tab.addTab(self.motor_widget,'Motor')
		self.movement_tab.addTab(self.scanner_widget,'Scanner')

		self.measurement_tab.addTab(self.reflec_widget,'Reflection')
		self.measurement_tab.addTab(self.count_widget,'Counts')

		#create graph
		self.data = [[],[]]
		self.fig = plt.figure(figsize = (4.5,4), dpi=72, facecolor=(1,1,1), edgecolor=(0,0,0))
		self.ax = self.fig.add_subplot(1,1,1)
		self.plot, = plt.plot(*self.data)
		self.ax.set_ylabel('dunno')
		self.ax.set_xlabel('nobody told me')
		self.canvas = FigureCanvas(self.fig)
		self.fig.tight_layout()

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

		self.dateandtime.setEnabled(False)
		self.manualtemp.stateChanged.connect(self.temp.setEnabled)
		self.temp.setEnabled(False)

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
		self.metadata_grid.addLayout(self.subgrid1,2,2,1,2)

		self.metadata_grid.addWidget(QtGui.QLabel('Comments:'),3,0)
		self.metadata_grid.addWidget(self.comment,3,1,1,3)

		#populate motor_grid
		self.xfrom_m = QtGui.QLineEdit('')
		self.xto_m = QtGui.QLineEdit('')
		self.yfrom_m = QtGui.QLineEdit('')
		self.yto_m = QtGui.QLineEdit('')
		self.volt_m = QtGui.QLineEdit('')
		self.freq_m = QtGui.QLineEdit('')
		self.readv_m = QtGui.QLineEdit('')
		self.closedloop_m = QtGui.QCheckBox('Closed-loop operation?')

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
		self.motor_grid.addWidget(QtGui.QLabel('V<sub>read</sub>:'),3,0)
		self.motor_grid.addWidget(self.readv_m,3,1)
		#self.motor_grid.addWidget(QtGui.QLabel('->'),1,2)
		self.motor_grid.addWidget(self.closedloop_m,3,2,1,2)


		#populate scanner grid
		self.xfrom_s = QtGui.QLineEdit('')
		self.xto_s = QtGui.QLineEdit('')
		self.yfrom_s = QtGui.QLineEdit('')
		self.yto_s = QtGui.QLineEdit('')
		self.voltstep_s = QtGui.QLineEdit('')

		self.scanner_grid.addWidget(QtGui.QLabel('X range:'),0,0)
		self.scanner_grid.addWidget(self.xfrom_s,0,1)
		self.scanner_grid.addWidget(QtGui.QLabel('->'),0,2)
		self.scanner_grid.addWidget(self.xto_s,0,3)
		self.scanner_grid.addWidget(QtGui.QLabel('Y range:'),1,0)
		self.scanner_grid.addWidget(self.yfrom_s,1,1)
		self.scanner_grid.addWidget(QtGui.QLabel('->'),1,2)
		self.scanner_grid.addWidget(self.yto_s,1,3)

		self.scanner_grid.addWidget(QtGui.QLabel('Step size:'),2,0)
		self.scanner_grid.addWidget(self.voltstep_s,2,1)


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


	def setDefaults(self):
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

	def acquire(self):
		pass

	def halt(self):
		pass

	def plotExternal(self):
		pass

	def export(self):
		pass

	def openSettings(self):
		pass

	def openPlotSettings(self):
		pass

	def helpFile(self):
		pass

	def aboutProgram(self):
		pass


class MapperDrone(QtCore.QObject):
	def __init__(self):
		super(MapperDrone,self).__init__()
		#handle stuff passed in
		self.abort = False
		

	def longRunning(self):
		#do the things that take a long time
		pass


def main():
	app = QtGui.QApplication(sys.argv)
	ex = MapperProg()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()