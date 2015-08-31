#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import matplotlib
matplotlib.use('Qt4Agg')
import matplotlib.pyplot as plt
import numpy as np
import math
from PySide import QtGui, QtCore
import json
import time
import csv
import os
#!!!!!!!!!!!!!!!!!
from fakesim900 import Sim900
#!!!!!!!!!!!!!!!!!
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

settings_file = 'settings.ini'

def getSettings():
	try:
		with open(settings_file,'r') as f:
			settings = json.loads(f.read())
	except IOError:
		settings = defaultSettings()
	return settings

def defaultSettings():
	settings = {'sim900addr':'ASRL1',
				'vsourcemod':2,
				'tsourcemod':1,
				'vmeasmod':7,
				'vsourceinput':1,
				'vmeasinput':2,
				'tinput':3}
	return settings

def setSettings(settings):
	try:
		with open(settings_file,'w') as f:
			f.write(json.dumps(settings))
			return True
	except IOError:
		return False

class IVProg(QtGui.QMainWindow):

	def __init__(self):
		super(IVProg, self).__init__()
		self.initUI()

	def initUI(self):
		#
		#   Set up the MENU and TOOLBARS
		#
		exitAction = QtGui.QAction(QtGui.QIcon(r'icons\exit.png'),'&Exit',self)
		exitAction.setShortcut('Ctrl+Q')
		exitAction.setStatusTip('Exit application')
		exitAction.triggered.connect(self.close)

		newAction = QtGui.QAction(QtGui.QIcon(r'icons\new.png'),'&New...',self)
		newAction.setShortcut('Ctrl+N')
		newAction.setStatusTip('Blank dataset')
		newAction.triggered.connect(self.new)

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

		self.acquireAction = QtGui.QAction(QtGui.QIcon(r'icons\acquire.png'),'&Acquire',self)
		self.acquireAction.setShortcut('Ctrl+R')
		self.acquireAction.setStatusTip('Run I-V scan')
		self.acquireAction.triggered.connect(self.acquire)

		self.haltAction = QtGui.QAction(QtGui.QIcon(r'icons\abort.png'),'&Halt acquisition',self)
		self.haltAction.setShortcut('Ctrl+H')
		self.haltAction.setStatusTip('Halt I-V acquisition')
		self.haltAction.triggered.connect(self.halt)
		self.haltAction.setEnabled(False)

		plotAction = QtGui.QAction(QtGui.QIcon(r'icons\plot.png'),'&Plot',self)
		plotAction.setShortcut('Ctrl+P')
		plotAction.setStatusTip('Plot I-V data graphically')
		plotAction.triggered.connect(self.plotExternal)

		exportAction = QtGui.QAction(QtGui.QIcon(r'icons\export.png'),'&Export',self)
		exportAction.setShortcut('Ctrl+E')
		exportAction.setStatusTip('Export data to CSV')
		exportAction.triggered.connect(self.export)

		settingsAction = QtGui.QAction(QtGui.QIcon(r'icons\settings.png'),'&Device settings',self)
		settingsAction.setStatusTip('Edit SIM900 settings')
		settingsAction.triggered.connect(self.openSettings)

		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(newAction)
		fileMenu.addAction(openAction)
		fileMenu.addSeparator()
		fileMenu.addAction(saveAction)
		fileMenu.addAction(saveAsAction)
		fileMenu.addSeparator()
		fileMenu.addAction(exitAction)
		settingsMenu = menubar.addMenu('&Settings')
		settingsMenu.addAction(settingsAction)
		
		self.toolbar = self.addToolBar('Operations')
		self.toolbar.setMovable(False)
		self.toolbar.addAction(self.acquireAction)
		self.toolbar.addAction(self.haltAction)
		self.toolbar.addSeparator()
		self.toolbar.addAction(plotAction)
		self.toolbar.addAction(exportAction)
		
		mainthing = QtGui.QWidget()
		self.setCentralWidget(mainthing)
		self.pbar = QtGui.QProgressBar(self)
		self.pbar.setGeometry(30,40,200,25)
		#self.timer = QtCore.QTimer()
		#self.timer.timeout.connect(self.timerEvent)
		

		#
		#   Create and connect MEASUREMENT VALUE INPUTS
		#

		self.username = QtGui.QLineEdit('')
		self.dateandtime = QtGui.QLineEdit('')
		self.batchName = QtGui.QLineEdit('')
		self.deviceId = QtGui.QLineEdit('')
		self.sma = QtGui.QLineEdit('')
		self.manualtemp = QtGui.QCheckBox('Manual?')
		self.temp = QtGui.QLineEdit('')
		self.shunt = QtGui.QCheckBox('Shunt?')
		self.rBias = QtGui.QLineEdit('100000')
		self.rShunt = QtGui.QLineEdit('50')
		self.vMax = QtGui.QLineEdit('')
		self.vStep = QtGui.QLineEdit('')
		self.comment = QtGui.QLineEdit('')
		self.nSteps = QtGui.QLineEdit('')

		self.list_of_changeables = [self.username,
									self.dateandtime,
									self.batchName,
									self.deviceId,
									self.sma,
									self.manualtemp,
									self.temp,
									self.shunt,
									self.rBias,
									self.rShunt,
									self.vMax,
									self.vStep,
									self.comment,
									self.nSteps]

		for item in self.list_of_changeables:
			if isinstance(item,QtGui.QLineEdit):
				item.textChanged.connect(self.setNeedsSaving)
			elif isinstance(item,QtGui.QCheckBox):
				item.stateChanged.connect(self.setNeedsSaving)

		#self.vMax.setInputMask('00.00;_')
		#self.vStep.setInputMask('00.00;_')

		self.dateandtime.setEnabled(False)
		self.nSteps.setEnabled(False)
		self.shunt.stateChanged.connect(self.rShunt.setEnabled)
		self.shunt.setCheckState(QtCore.Qt.Checked)

		self.manualtemp.stateChanged.connect(self.temp.setEnabled)
		self.temp.setEnabled(False)

		self.vMax.textChanged.connect(self.recalculateMovement)
		self.vStep.textChanged.connect(self.recalculateMovement)
		#self.nSteps.textChanged.connect(self.recalculateMovement)
		self.lastEdited = [None,None]

		#
		#   Create layout
		#

		gridsection = QtGui.QGridLayout()
		gridsection.setSpacing(10)
		subgrid2 = QtGui.QGridLayout()
		subgrid1 = QtGui.QGridLayout()
		subgrid3 = QtGui.QGridLayout()

		gridsection.addWidget(QtGui.QLabel('User:'),0,0)
		gridsection.addWidget(self.username,0,1)
		gridsection.addWidget(QtGui.QLabel('At:'),0,2)
		gridsection.addWidget(self.dateandtime,0,3)

		gridsection.addWidget(QtGui.QLabel('Batch:'),1,0)
		gridsection.addWidget(self.batchName,1,1)
		gridsection.addWidget(QtGui.QLabel('Device:'),1,2)
		gridsection.addWidget(self.deviceId,1,3)

		gridsection.addWidget(QtGui.QLabel('SMA:'),2,0)
		gridsection.addWidget(self.sma,2,1)
		subgrid1.addWidget(self.manualtemp,0,0)
		subgrid1.addWidget(QtGui.QLabel('Temp:'),0,1)
		subgrid1.addWidget(self.temp,0,2)
		gridsection.addLayout(subgrid1,2,2,1,2)

		gridsection.addLayout(subgrid3,3,0,1,4)
		subgrid3.addWidget(QtGui.QLabel('Max voltage:'),0,0)
		subgrid3.addWidget(self.vMax,0,1)
		subgrid3.addWidget(QtGui.QLabel('Step size:'),0,2)
		subgrid3.addWidget(self.vStep,0,3)
		subgrid3.addWidget(QtGui.QLabel('Total steps:'),0,4)
		subgrid3.addWidget(self.nSteps,0,5)

		gridsection.addWidget(QtGui.QLabel('Rbias:'),4,0)
		gridsection.addWidget(self.rBias,4,1)
		subgrid2.addWidget(self.shunt,0,0)
		subgrid2.addWidget(QtGui.QLabel('Rshunt:'),0,1)
		subgrid2.addWidget(self.rShunt,0,2)
		gridsection.addLayout(subgrid2,4,2,1,2)

		gridsection.addWidget(QtGui.QLabel('Comments:'),5,0)
		gridsection.addWidget(self.comment,5,1,1,3)

		gridsection.addWidget(self.pbar,6,0,1,4)

		#
		#   Create matplotlib items
		#

		self.data=[[],[]]

		#self.fig =Figure(figsize=(250,250), dpi=72, facecolor=(1,1,1),edgecolor=(0,0,0))
		#self.ax = self.fig.add_subplot(1,1,1)
		self.fig = plt.figure(facecolor=(1,1,1),edgecolor=(0,0,0))
		self.ax = self.fig.add_subplot(1,1,1)
		self.plot, = plt.plot(*self.data)
		self.ax.set_ylabel('measured voltage (V)')
		self.ax.set_xlabel('supplied voltage (V)')
		#self.ax.set_xlim(-5,5)
		#self.ax.set_ylim(-5,5)
		self.canvas = FigureCanvas(self.fig)

		vbox = QtGui.QVBoxLayout()
		vbox.addLayout(gridsection)
		vbox.addWidget(self.canvas)
		#vbox.addStretch(1)

		#
		#   Final pre-flight checks
		#

		mainthing.setLayout(vbox)
		self.settings = getSettings()
		self.setGeometry(300,300,450,500)
		self.name_of_application = 'I-V Tester'
		self.setWindowTitle(self.name_of_application)
		self.setWindowIcon(QtGui.QIcon(r'icons\plot.png'))
		self.biases = []
		self.filename = ''
		self.statusBar().showMessage('Ready...')
		self.needs_saving = False
		self.show()

	#
	#   Function definitions
	#

	def closeEvent(self,event):
		setSettings(self.settings)
		self.checkNeedsSaving(event)

	def checkNeedsSaving(self, event=None):
		if self.needs_saving:
			if self.filename == '':
				self.question = 'Do you want to save data?'
			else:
				self.question = 'Do you want to save changes to '+str(self.filename)+'?'
			reply = QtGui.QMessageBox.question(self,'I-V Tester',
				self.question,QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Save)
			if reply == QtGui.QMessageBox.Discard:
				if event != None:
					event.accept()
				else:
					return False
			elif reply == QtGui.QMessageBox.Cancel:
				if event != None:
					event.ignore()
				else:
					return True
			elif reply == QtGui.QMessageBox.Save:
				self.save()
				if event != None:
					event.accept()
				else:
					return False
		else:
			if event != None:
				event.accept()
			else:
				return False

	def setNeedsSaving(self):
		self.needs_saving = True

	def open(self):
		self.filename_open, _ = QtGui.QFileDialog.getOpenFileName(self,'Open file...','',"I-V data (*.txt);;All data (*.*)")
		if self.checkNeedsSaving() == False:
			self.new()
			self.filename = self.filename_open
			if self.filename != '':
				with open(self.filename,'r') as f:
					self.csvfile = csv.reader(f)
					self.inputdata = []
					for row in self.csvfile:
						self.inputdata.append(row)
				if [] in self.inputdata:
					self.processMetadata(self.inputdata[:self.inputdata.index([])])
					self.data = []
					for row in self.inputdata[self.inputdata.index([])+1:]:
						self.data.append([])
						for column in row:
							self.data[-1].append(float(column))
				else:
					self.data = []
					for row in self.inputdata:
						self.data.append([])
						for column in row:
							self.data[-1].append(float(column))
			self.data = list(np.transpose(np.array(self.data)))
			if self.data == []:
				self.data = [[],[]]
			self.needs_saving = False
			self.replot()
			self.statusBar().showMessage('Loaded '+str(self.filename))
			self.updateWindowTitle()

	def updateWindowTitle(self):
		if self.filename == '':
			self.setWindowTitle(self.name_of_application)
		else:
			self.setWindowTitle(self.name_of_application+' - '+os.path.basename(self.filename))

	def save(self):
		if self.filename == '':
			self.saveAs()
		else:
			with open(self.filename,'w') as f:
				self.csvfile = csv.writer(f)
				for row in self.processMetadata()+['']+list(np.transpose(np.array(self.data))):
					self.csvfile.writerow(row)
			self.statusBar().showMessage('Saved to '+str(self.filename))
			self.updateWindowTitle()
			self.needs_saving = False

	def saveAs(self):
		self.filename, _ = QtGui.QFileDialog.getSaveFileName(self,'Save as...','',"I-V data (*.txt);;All data (*.*)")
		if self.filename != '':
			self.save()
		
	def processMetadata(self,source=None):
		self.metacategories = {
			'user':self.username,
			'date-time':self.dateandtime,
			'batch-name':self.batchName,
			'device-id':self.deviceId,
			'sma-number':self.sma,
			'manually-defined-temp':self.manualtemp,
			'temperature':self.temp,
			'shunt':self.shunt,
			'bias-resistor-value':self.rBias,
			'shunt-resistor-value':self.rShunt,
			'max-voltage':self.vMax,
			'step-size':self.vStep,
			'number-of-steps':self.nSteps,
			'comment':self.comment,
			}
		if source == None:
			self.metadata = []
			for category in sorted(self.metacategories.keys()):
				if isinstance(self.metacategories[category],QtGui.QLineEdit):
					self.metadata.append([category,self.metacategories[category].text()])
				elif isinstance(self.metacategories[category],QtGui.QCheckBox):
					self.metadata.append([category,self.metacategories[category].isChecked()])
			return self.metadata
		elif source != None:
			for row in source:
				if isinstance(self.metacategories[row[0]],QtGui.QLineEdit):
					self.metacategories[row[0]].setText(row[1])
				elif isinstance(self.metacategories[row[0]],QtGui.QCheckBox):
					if row[1] == 'True':
						self.metacategories[row[0]].setChecked(True)
					elif row[1] == 'False':
						self.metacategories[row[0]].setChecked(False)


	def new(self):
		print 'REINITIALISE THE STATE, BARRING VALUES WHICH DON\'T CHANGE'
		self.needs_saving = False
		self.filename = ''
		self.updateWindowTitle()
		self.statusBar().showMessage('Currently does nothing!')

	def replot(self):
		self.plot.set_xdata(self.data[0])
		self.plot.set_ydata(self.data[1])
		self.ax.relim()
		self.ax.autoscale_view()
		self.canvas.draw()

	def acquire(self):
		if len(self.biases) > 0:
			self.sim900 = Sim900(self.settings['sim900addr'])
			if self.sim900.check() != False:
				if not self.manualtemp.isChecked():
					self.sim900 = Sim900(self.settings['sim900addr'])
					self.temp.setText(str(self.sim900.query(self.settings['tsourcemod'],'TVAL? '+str(self.settings['tinput'])+',1')))
					self.sim900.close()
				self.haltAction.setEnabled(True)
				self.acquireAction.setEnabled(False)
				self.dateandtime.setText(time.asctime())
				#self.dataThread.finished.connect()
				self.step = 0
				print 'launching in separate thread...',
				self.objThread = QtCore.QThread()
				self.simThread = Sim900Thread(self.settings,self.biases)
				self.simThread.moveToThread(self.objThread)
				self.objThread.started.connect(self.simThread.longRunning)
				self.simThread.newdata.connect(self.awaitData)
				self.simThread.finished.connect(self.objThread.quit)
				self.simThread.finished.connect(self.acquisitionFinished)
				self.simThread.aborted.connect(self.resetPbar)
				#self.halt_acquisition.connect(self.simThread.breakout)
				self.objThread.start()
				print 'launched'
				self.replot()
			else:
				self.statusBar().showMessage('SIM900 not responding on '+str(self.settings['sim900addr']))

		else:
			self.statusBar().showMessage('No valid bias range set!')

	def acquisitionFinished(self):
		self.haltAction.setEnabled(False)
		self.acquireAction.setEnabled(True)

	def awaitData(self,data):
		self.data = data
		self.step += 1
		self.pbar.setValue(100*(self.step/float(len(self.biases))))
		self.replot()

	#halt_acquisition = QtCore.Signal()
	def halt(self):
		self.haltAction.setEnabled(False)
		self.acquireAction.setEnabled(True)
		self.simThread.abort = True
		#self.halt_acquisition.emit()

	def plotExternal(self):
		self.plotWindow = IVPlot(self.data,self.processMetadata())
		self.plotWindow.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
		self.plotWindow.hide()
		self.plotWindow.show()
		self.statusBar().showMessage('Currently does nothing!')

	def export(self):
		self.statusBar().showMessage('Currently does nothing!')

	def openSettings(self):
		self.settingsWindow = IVSettings(self.settings)
		self.settingsWindow.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
		self.settingsWindow.hide()
		self.settingsWindow.show()
		self.settingsWindow.ok.clicked.connect(self.receiveSettings)

	def receiveSettings(self):
		self.settings = self.settingsWindow.settings

	def recalculateMovement(self):
		try:
			if float(self.vStep.text())>0.0:
				self.biasPrimitive = np.array([x*float(self.vStep.text()) for x in range(int(math.ceil(float(self.vMax.text())/float(self.vStep.text())))+1)])
				self.biases = list(self.biasPrimitive) + list(self.biasPrimitive[::-1])[1:] + list(-self.biasPrimitive)[1:] + list((-self.biasPrimitive)[::-1])[1:-1] + [0]
				self.nSteps.setText(str(len(self.biases)))
			elif float(self.vStep.text())==0.0:
				self.biases = []
				self.nSteps.setText(str(float('inf')))
		except ValueError:
			pass


	def resetPbar(self):
		self.pbar.reset()

class Sim900Thread(QtCore.QObject):
	def __init__(self,settings,biases):
		QtCore.QObject.__init__(self,parent=None)
		self.biases = biases
		self.settings = settings
		self.abort = False
		
	finished = QtCore.Signal()
	newdata = QtCore.Signal(list)
	aborted = QtCore.Signal()

	def longRunning(self):
		self.initSim()
		self.step = 0
		self.data = [[],[]]
		while self.step < len(self.biases) and self.abort == False:
			self.setAndGetSimVoltages(self.biases[self.step])
			self.step += 1
			self.newdata.emit(self.data)
		if self.abort == True:
			self.aborted.emit()
		#print self.data
		self.closeSim()
		self.finished.emit()

	def initSim(self):
		self.sim = Sim900(self.settings['sim900addr'])
		self.sim.write(self.settings['vsourcemod'],'OPON')

	def closeSim(self):
		self.sim.write(self.settings['vsourcemod'],'OPOF')
		self.sim.close()

	def setAndGetSimVoltages(self,biaspoint):
		self.sim.write(self.settings['vsourcemod'],'VOLT '+str('%.3f' % biaspoint))
		time.sleep(0.8)
		self.data[0].append(float(self.sim.query(self.settings['vmeasmod'],'VOLT? '+str(self.settings['vsourceinput'])+',1')))
		self.data[1].append(float(self.sim.query(self.settings['vmeasmod'],'VOLT? '+str(self.settings['vmeasinput'])+',1')))


class IVPlot(QtGui.QMainWindow):
	def __init__(self,data,processed_metadata):
		super(IVPlot, self).__init__()
		self.supplied_voltages = data[0]
		self.measured_voltages = data[1]
		self.metadata = dict(processed_metadata)
		self.initUI()

	def initUI(self):

		#self.fig =Figure(figsize=(250,250), dpi=72, facecolor=(1,1,1),edgecolor=(0,0,0))
		#self.ax = self.fig.add_subplot(1,1,1)
		self.data = [self.supplied_voltages,self.measured_voltages]
		self.fig = plt.figure(facecolor=(1,1,1),edgecolor=(0,0,0))
		self.ax = self.fig.add_subplot(1,1,1)
		self.plot, = plt.plot(*self.data)
		self.ax.set_xlabel('supplied voltage (V)')
		self.ax.set_ylabel('measured voltage (V)')
		#self.ax.set_xlim(-5,5)
		#self.ax.set_ylim(-5,5)
		self.canvas = FigureCanvas(self.fig)

		self.yaxis_idevice = QtGui.QCheckBox('Calculate current through device')

		self.gridsection = QtGui.QGridLayout()
		self.gridsection.setSpacing(10)
		self.gridsection.addWidget(self.yaxis_idevice,0,0)
		self.yaxis_idevice.stateChanged.connect(self.switchToCurrent)

		self.hbox = QtGui.QHBoxLayout()
		self.hbox.addWidget(self.canvas)
		self.hbox.addLayout(self.gridsection)

		self.mainthing = QtGui.QWidget()
		self.setCentralWidget(self.mainthing)
		self.mainthing.setLayout(self.hbox)
		self.setGeometry(300,300,500,400)
		self.setWindowTitle('I-V Plot')
		self.setWindowIcon(QtGui.QIcon(r'icons\plot.png'))
		self.show()

	def replot(self):
		self.plot.set_xdata(self.data[0])
		self.plot.set_ydata(self.data[1])
		self.ax.relim()
		self.ax.autoscale_view()
		self.canvas.draw()

	def calculateCurrents(self):
		if self.metadata['shunt'] == True:
			self.r_shunt = float(self.metadata['shunt-resistor-value'])
		else:
			self.r_shunt = float('inf')
		self.r_bias = float(self.metadata['bias-resistor-value'])
		self.calculated_currents = []
		for v, voltage in enumerate(self.measured_voltages):
			self.v_meas = float(voltage)
			self.v_supp = float(self.supplied_voltages[v])
			self.calculated_currents.append(((self.v_supp-self.v_meas)/self.r_bias) - (self.v_meas/self.r_shunt))

	def switchToCurrent(self):
		if self.yaxis_idevice.isChecked():
			self.calculateCurrents()
			self.data[1] = self.calculated_currents
			self.ax.set_ylabel('current over device (A)')
			self.replot()
		else:
			self.data[1] = self.measured_voltages
			self.ax.set_ylabel('measured voltage (V)')
			self.replot()


class IVSettings(QtGui.QMainWindow):
	def __init__(self,settings):
		super(IVSettings, self).__init__()
		self.settings = settings
		self.initUI()

	def initUI(self):
		self.sim900addr = QtGui.QLineEdit(str(self.settings['sim900addr']))
		self.vsourcemod = QtGui.QLineEdit(str(self.settings['vsourcemod']))
		self.tsourcemod = QtGui.QLineEdit(str(self.settings['tsourcemod']))
		self.tinput = QtGui.QLineEdit(str(self.settings['tinput']))
		self.vmeasmod = QtGui.QLineEdit(str(self.settings['vmeasmod']))
		self.vsourceinput = QtGui.QLineEdit(str(self.settings['vsourceinput']))
		self.vmeasinput = QtGui.QLineEdit(str(self.settings['vmeasinput']))
		self.ok = QtGui.QPushButton('OK')
		self.cancel = QtGui.QPushButton('Cancel')
		self.cancel.clicked.connect(self.close)
		self.ok.clicked.connect(self.passValuesBackAndClose)

		self.grid = QtGui.QGridLayout()
		self.grid.setSpacing(10)
		self.grid.addWidget(QtGui.QLabel('<b>SIM900 address:</b>'),0,0)
		self.grid.addWidget(self.sim900addr,0,1)
		self.grid.addWidget(QtGui.QLabel('<b>SIM928 voltage source module:</b>'),1,0)
		self.grid.addWidget(self.vsourcemod,1,1)
		self.grid.setRowMinimumHeight(2,10)
		self.grid.addWidget(QtGui.QLabel('<b>SIM922 temperature module:</b>'),3,0)
		self.grid.addWidget(self.tsourcemod,3,1)
		self.grid.addWidget(QtGui.QLabel('\tSensor channel:'),4,0)
		self.grid.addWidget(self.tinput,4,1)
		self.grid.setRowMinimumHeight(5,10)
		self.grid.addWidget(QtGui.QLabel('<b>SIM970 voltmeter module:</b>'),6,0)
		self.grid.addWidget(self.vmeasmod,6,1)
		self.grid.addWidget(QtGui.QLabel('\tSupplied voltage channel:'),7,0)
		self.grid.addWidget(self.vsourceinput,7,1)
		self.grid.addWidget(QtGui.QLabel('\tMeasured voltage channel:'),8,0)
		self.grid.addWidget(self.vmeasinput,8,1)
		self.grid.setRowMinimumHeight(9,10)
		self.grid.addWidget(self.ok,10,0)
		self.grid.addWidget(self.cancel,10,1)

		self.vbox = QtGui.QVBoxLayout()
		self.vbox.addLayout(self.grid)
		self.vbox.addStretch(1)
		self.mainthing = QtGui.QWidget()
		self.setCentralWidget(self.mainthing)
		self.mainthing.setLayout(self.vbox)
		self.setGeometry(300,300,300,200)
		self.setWindowTitle('I-V Settings')
		self.setWindowIcon(QtGui.QIcon(r'icons\settings.png'))
		self.show()

	def passValuesBackAndClose(self):
		self.settings['sim900addr'] = self.sim900addr.text()
		self.settings['vsourcemod'] = int(self.vsourcemod.text())
		self.settings['tsourcemod'] = int(self.tsourcemod.text())
		self.settings['vmeasmod'] = int(self.vmeasmod.text())
		self.settings['vmeasinput'] = int(self.vmeasinput.text())
		self.settings['vsourceinput'] = int(self.vsourceinput.text())
		self.settings['tinput'] = int(self.tinput.text())
		self.close()


def main():
	app = QtGui.QApplication(sys.argv)
	ex = IVProg()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()