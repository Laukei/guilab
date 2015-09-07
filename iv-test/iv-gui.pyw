#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import matplotlib
matplotlib.use('Qt4Agg')
import matplotlib.pyplot as plt
import numpy as np
import math
from PySide import QtGui, QtCore, QtWebKit
import json
import time
import csv
import os
#!!!!!!!!!!!!!!!!!
from sim900 import Sim900
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
				'tinput':3,
				'export':{
					'title':True,
					'x_offset':True,
					'y_offset':True,
					'verbose':False,
					'manual_axes':False,
					'xmax':None,
					'xmin':None,
					'ymax':None,
					'ymin':None,
					'grids':True,
					'width':8,
					'height':6,
					'unit':'in',
					'dpi':150,
					'idvsv':True
				}}
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

	aboutToQuit = QtCore.Signal()

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
		self.acquireAction.setStatusTip('Run I-V scan (Ctrl+R)')
		self.acquireAction.triggered.connect(self.acquire)

		self.haltAction = QtGui.QAction(QtGui.QIcon(r'icons\abort.png'),'&Halt acquisition',self)
		self.haltAction.setShortcut('Ctrl+H')
		self.haltAction.setStatusTip('Halt I-V acquisition (Ctrl+H)')
		self.haltAction.triggered.connect(self.halt)
		self.haltAction.setEnabled(False)

		plotAction = QtGui.QAction(QtGui.QIcon(r'icons\plot.png'),'&Plot',self)
		plotAction.setShortcut('Ctrl+P')
		plotAction.setStatusTip('Plot I-V data graphically (Ctrl+P)')
		plotAction.triggered.connect(self.plotExternal)

		exportAction = QtGui.QAction(QtGui.QIcon(r'icons\export.png'),'&Export',self)
		exportAction.setShortcut('Ctrl+C')
		exportAction.setStatusTip('Export data to CSV (Ctrl+C)')
		exportAction.triggered.connect(self.export)

		settingsAction = QtGui.QAction(QtGui.QIcon(r'icons\settings.png'),'&Device settings',self)
		settingsAction.setStatusTip('Edit SIM900 settings')
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
		self.toolbar.addAction(self.acquireAction)
		self.toolbar.addAction(self.haltAction)
		self.toolbar.addSeparator()
		self.toolbar.addAction(plotAction)
		self.toolbar.addAction(exportAction)
		
		mainthing = QtGui.QWidget()
		self.setCentralWidget(mainthing)
		self.pbar = QtGui.QProgressBar(self)
		#self.pbar.setGeometry(30,40,200,25)
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

		self.list_of_default_values = []
		for item in self.list_of_changeables:
			if isinstance(item,QtGui.QLineEdit):
				item.textChanged.connect(self.setNeedsSaving)
				self.list_of_default_values.append(item.text())
			elif isinstance(item,QtGui.QCheckBox):
				item.stateChanged.connect(self.setNeedsSaving)
				self.list_of_default_values.append(item.isChecked())

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
		self.fig = plt.figure(figsize=(6,3.8), dpi=72, facecolor=(1,1,1),edgecolor=(0,0,0))
		self.ax = self.fig.add_subplot(1,1,1)
		self.plot, = plt.plot(*self.data)
		#self.fig.subplots_adjust(bottom = 0.2)
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
		#self.setGeometry(300,300,450,500)
		self.resize(450,500)
		self.name_of_application = 'I-V Tester'
		self.setWindowTitle(self.name_of_application + '[*]')
		self.setWindowIcon(QtGui.QIcon(r'icons\plot.png'))
		self.biases = []
		self.filename = ''
		self.statusBar().showMessage('Ready...')
		self.setNoNeedSaving()
		self.show()
		self.replot()
	#
	#   Function definitions
	#

	def resizeEvent(self,event):
		self.replot()
		event.accept()

	def closeEvent(self,event):
		setSettings(self.settings)
		self.aboutToQuit.emit()
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
		self.setWindowModified(True)

	def setNoNeedSaving(self):
		self.needs_saving = False
		self.setWindowModified(False)

	def open(self):
		self.filename_open, _ = QtGui.QFileDialog.getOpenFileName(self,'Open file...','',"I-V data (*.txt);;All data (*.*)")
		if self.checkNeedsSaving() == False:
			self.new(True)
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
			self.setNoNeedSaving()
			self.replot()
			self.statusBar().showMessage('Loaded '+str(self.filename))
			self.updateWindowTitle()

	def updateWindowTitle(self):
		if self.filename == '':
			self.setWindowTitle(self.name_of_application + '[*]')
		else:
			self.setWindowTitle(self.name_of_application+' - '+os.path.basename(self.filename) + '[*]')

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
			self.setNoNeedSaving()

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

	def new(self,save_already_checked = False):
		if save_already_checked == True or self.checkNeedsSaving() == False:
			self.filename = ''
			self.data = [[],[]]
			for i, item in enumerate(self.list_of_changeables):
				if isinstance(item,QtGui.QLineEdit):
					item.setText(self.list_of_default_values[i])
				elif isinstance(item,QtGui.QCheckBox):
					item.setChecked(self.list_of_default_values[i])
			self.replot()
			self.setNoNeedSaving()
			self.updateWindowTitle()
			self.statusBar().showMessage('NO YOU FOOL! REINITIALISE VALUES!')

	def newSequential(self,save_already_checked=False):
		if save_already_checked == True or self.checkNeedsSaving()== False:
			self.filename = ''
			self.data = [[],[]]
			self.dateandtime.setText(self.list_of_default_values[self.list_of_changeables.index(self.dateandtime)])
			self.replot()
			self.setNoNeedSaving()
			self.updateWindowTitle()
			self.statusBar().showMessage('New dataset (preserving metadata)')

	def replot(self):
		self.plot.set_xdata(self.data[0])
		self.plot.set_ydata(self.data[1])
		self.ax.relim()
		self.ax.autoscale_view()
		plt.tight_layout()
		self.canvas.draw()

	def acquire(self):
		if len(self.biases) > 0:
			if self.data == [[],[]]:
				self.sim900 = Sim900(self.settings['sim900addr'])
				self.sim900check = self.sim900.check()
				if type(self.sim900check) != str:
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
					self.statusBar().showMessage('ERROR: '+self.sim900check)
			elif self.checkNeedsSaving() == False:
				self.newSequential(True)
				self.acquire()
			else:
				self.statusBar().showMessage('Unsaved data!')
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
		self.plotWindow = IVPlot(self.data,self.processMetadata(),self.settings,self.filename)
		self.plotWindow.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
		self.plotWindow.hide()
		self.plotWindow.show()

	def export(self):
		self.clipboard = QtGui.QApplication.clipboard()
		self.clipboard_string = ''
		for row in list(np.array(self.data).transpose()):#
			for col in row:
				self.clipboard_string += str(col) +'\t'
			self.clipboard_string = self.clipboard_string[:-1] +'\n'
		self.clipboard.setText(self.clipboard_string[:-1])
		self.statusBar().showMessage('Raw data copied to clipboard')

	def openSettings(self):
		self.settingsWindow = IVSettings(self.settings)
		self.settingsWindow.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
		self.settingsWindow.hide()
		self.settingsWindow.show()
		self.settingsWindow.ok.clicked.connect(self.receiveSettings)

	def openPlotSettings(self):
		self.plotSettingsWindow = IVPlotSettings(self.settings)
		self.plotSettingsWindow.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
		self.plotSettingsWindow.hide()
		self.plotSettingsWindow.show()
		self.plotSettingsWindow.ok.clicked.connect(self.receivePlotSettings)

	def receiveSettings(self):
		self.settings = self.settingsWindow.settings

	def receivePlotSettings(self):
		self.settings = self.plotSettingsWindow.settings

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

	def helpFile(self):
		self.helpWindow = HelpWindow()
		#self.helpWindow.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
		self.helpWindow.hide()
		self.aboutToQuit.connect(self.helpWindow.close)
		self.helpWindow.show()

	def aboutProgram(self):
		self.aboutBox = QtGui.QMessageBox()
		self.aboutBox.setText("<b>I-V Tester</b>")
		self.aboutBox.setInformativeText("Written by Rob Heath (rob@robheath.me.uk) at the University of Glasgow in 2015")
		self.aboutBox.setIcon(QtGui.QMessageBox.Information)
		self.aboutBox.setWindowTitle('About program')
		self.aboutBox.exec_()

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
	def __init__(self,data,processed_metadata,settings,filename):
		super(IVPlot, self).__init__()
		self.supplied_voltages = data[0]
		self.measured_voltages = data[1]
		if data[0] != [] and data[1] != []:
			self.zeroed_supplied_voltages = self.deOffset(data[0],data[0][0])
			self.zeroed_measured_voltages = self.deOffset(data[1],data[1][0])
			self.offset_in_supplied_voltage = data[0][0]
			self.offset_in_measured_voltage = data[1][0]
		else:
			self.zeroed_supplied_voltages, self.zeroed_measured_voltages = data[0], data[1]
			self.offset_in_measured_voltage = 0
			self.offset_in_supplied_voltage = 0
		self.metadata = dict(processed_metadata)
		self.settings = settings
		self.se = self.settings['export']
		self.filename = filename
		self.initUI()

	def initUI(self):

		#self.fig =Figure(figsize=(250,250), dpi=72, facecolor=(1,1,1),edgecolor=(0,0,0))
		#self.ax = self.fig.add_subplot(1,1,1)
		self.data = [self.supplied_voltages,self.measured_voltages]
		self.fig = plt.figure(figsize=(8,6), dpi=300, facecolor=(1,1,1),edgecolor=(0,0,0))
		self.ax = self.fig.add_subplot(1,1,1)
		self.plot, = plt.plot(*self.data)
		self.ax.set_xlabel('Supplied voltage (V)')
		self.ax.set_ylabel('Measured voltage (V)')
		#self.ax.set_xlim(-5,5)
		#self.ax.set_ylim(-5,5)
		self.canvas = FigureCanvas(self.fig)

		self.yaxis_idevice = QtGui.QCheckBox('Supplied voltage vs device current')
		self.x_offset = QtGui.QCheckBox('Correct X offset')
		self.y_offset = QtGui.QCheckBox('Correct Y offset')
		self.verbose_graph = QtGui.QCheckBox('Verbose graph')
		self.manual_limits = QtGui.QCheckBox('Manual axes')
		self.x_max = QtGui.QLineEdit('')
		self.x_min = QtGui.QLineEdit('')
		self.y_max = QtGui.QLineEdit('')
		self.y_min = QtGui.QLineEdit('')
		self.gridlines = QtGui.QCheckBox('Axis gridlines')
		self.give_title = QtGui.QCheckBox('Graph title')
		self.title = QtGui.QLineEdit(self.autoTitle())
		self.dpi = QtGui.QLineEdit('')
		self.exp_width = QtGui.QLineEdit('')
		self.exp_height = QtGui.QLineEdit('')
		self.exp_units = QtGui.QComboBox(self)
		self.possible_units = ['in','cm','px']
		for unit in self.possible_units:
			self.exp_units.addItem(unit)

		self.exp_units.setCurrentIndex(self.possible_units.index(self.se['unit']))

		self.checkables = [ ['title',self.give_title],
							['x_offset',self.x_offset],
							['y_offset',self.y_offset],
							['verbose',self.verbose_graph],
							['manual_axes',self.manual_limits],
							['grids',self.gridlines],
							['idvsv',self.yaxis_idevice]]

		self.textables = [  ['ymax',self.y_max],
							['ymin',self.y_min],
							['xmax',self.x_max],
							['xmin',self.x_min],
							['width',self.exp_width],
							['height',self.exp_height],
							['dpi',self.dpi]]

		self.initFromSettings()

		self.resetButton = QtGui.QPushButton('Reset')
		self.closeButton = QtGui.QPushButton('Close')
		self.exportButton = QtGui.QPushButton('Export')

		self.manual_limits_widget = QtGui.QWidget()
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

		self.title_widget = QtGui.QWidget()
		self.title_widget.title_grid = QtGui.QGridLayout()
		self.title_widget.setLayout(self.title_widget.title_grid)
		self.title_widget.title_grid.addWidget(QtGui.QLabel('Title:'),0,0)
		self.title_widget.title_grid.addWidget(self.title,0,1)
		self.title_widget.setVisible(False)

		self.export_widget = QtGui.QWidget()
		self.export_widget.export_grid = QtGui.QGridLayout()
		self.export_widget.vbox = QtGui.QVBoxLayout()
		self.export_widget.vbox.addWidget(QtGui.QLabel('Export settings'))
		self.export_widget.vbox.addLayout(self.export_widget.export_grid)
		self.export_widget.setLayout(self.export_widget.vbox)
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

		self.gridsection2.addWidget(self.yaxis_idevice,0,0)
		self.gridsection2.addWidget(self.x_offset,1,0)
		self.gridsection2.addWidget(self.y_offset,2,0)
		self.gridsection2.addWidget(self.verbose_graph,3,0)
		self.gridsection2.addWidget(self.manual_limits,4,0)

		self.gridsection3.setSpacing(10)
		self.gridsection3.addWidget(self.gridlines)

		self.panel_widget.vbox.addLayout(self.gridsection1)
		self.panel_widget.vbox.addWidget(self.title_widget)
		self.panel_widget.vbox.addLayout(self.gridsection2)
		self.panel_widget.vbox.addWidget(self.manual_limits_widget)
		self.panel_widget.vbox.addLayout(self.gridsection3)
		self.panel_widget.vbox.addWidget(self.export_widget)
		self.panel_widget.vbox.addStretch(1)
		self.panel_widget.vbox.addLayout(self.bottombar)

		self.yaxis_idevice.stateChanged.connect(self.switchToCurrent)
		self.x_offset.stateChanged.connect(self.handleVoltageOffsets)
		self.y_offset.stateChanged.connect(self.handleVoltageOffsets)
		self.verbose_graph.stateChanged.connect(self.verboseGraphToggle)
		self.manual_limits.toggled.connect(self.manual_limits_widget.setVisible)
		self.manual_limits.toggled.connect(self.replot)
		self.x_max.textChanged.connect(self.replot)
		self.x_min.textChanged.connect(self.replot)
		self.y_max.textChanged.connect(self.replot)
		self.y_min.textChanged.connect(self.replot)
		self.gridlines.toggled.connect(self.setGridlines)
		self.give_title.toggled.connect(self.title_widget.setVisible)
		self.title.textChanged.connect(self.setGraphTitle)
		self.give_title.toggled.connect(self.setGraphTitle)
		self.exp_units.activated.connect(self.setExp)
		self.exp_width.textChanged.connect(self.setExp)
		self.exp_height.textChanged.connect(self.setExp)
		self.dpi.textChanged.connect(self.setExp)
		self.closeButton.clicked.connect(self.close)
		self.resetButton.clicked.connect(self.resetPlot)
		self.exportButton.clicked.connect(self.exportGraph)


		self.scroll_area = QtGui.QScrollArea()
		self.scroll_area.setBackgroundRole(QtGui.QPalette.Dark)
		self.scroll_area.setAlignment(QtCore.Qt.AlignCenter)
		self.scroll_area.setWidget(self.canvas)

		self.hbox.addWidget(self.scroll_area)
		self.hbox.addWidget(self.panel_widget)

		self.mainthing = QtGui.QWidget()
		self.setCentralWidget(self.mainthing)
		self.mainthing.setLayout(self.hbox)
		#self.setGeometry(300,300,500,400)
		self.resize(800,600)
		self.setWindowTitle('I-V Plotter')
		self.setWindowIcon(QtGui.QIcon(r'icons\plot.png'))
		self.updateGraph()
		self.showMaximized()
		self.show()

	def updateGraph(self):
		self.manual_limits_widget.setVisible(self.manual_limits.isChecked())
		self.title_widget.setVisible(self.give_title.isChecked())
		self.setExp()
		self.switchToCurrent()
		self.handleVoltageOffsets()
		self.setGraphTitle()
		#self.setExp()
		self.verboseGraphToggle()
		self.setGridlines()

	def initFromSettings(self):
		for checkable in self.checkables:
			if self.se[checkable[0]] == True:
				checkable[1].setCheckState(QtCore.Qt.Checked)
			else:
				checkable[1].setCheckState(QtCore.Qt.Unchecked)

		for textable in self.textables:
			if self.se[textable[0]] == None:
				textable[1].setText('')
			else:
				textable[1].setText(str(self.se[textable[0]]))
		self.exp_units.setCurrentIndex(self.possible_units.index(self.se['unit']))

	def resetPlot(self):
		self.initFromSettings()
		self.updateGraph()

	def exportGraph(self):
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
			self.target_path = ''
		else:
			self.target_path = os.path.dirname(self.filename)
		self.filename, _ = QtGui.QFileDialog.getSaveFileName(self,'Save as...',self.target_path,self.filetype_string,'Portable Network Graphics (*.png)')
		if self.filename != '':
			if os.path.splitext(self.filename)[1][1:] in self.graphical_extensions:
				plt.savefig(self.filename,dpi=float(self.dpi.text()))
			else:
				with open(self.filename,'w') as f:
					self.csvfile = csv.writer(f,delimiter = ',')
					self.csvfile.writerows(list(np.array(self.data).transpose()))
			self.statusBar().showMessage('Graph data saved to: '+str(self.filename))
			#plt.savefig()

	def autoTitle(self):
		self.titlestring = 'I-V data'
		if self.metadata['batch-name'] != '' or self.metadata['device-id']!= '':
			self.titlestring += ' for '
			if self.metadata['batch-name'] != '':
				self.titlestring += self.metadata['batch-name']+' '
			if self.metadata['device-id'] != '':
				self.titlestring += self.metadata['device-id']+' '
		if self.metadata['sma-number'] != '':
			self.titlestring += 'SMA'+self.metadata['sma-number']+' '
		if self.metadata['temperature'] != '':
			self.titlestring += 'at '+self.metadata['temperature']+'K'
		if self.metadata['shunt'] == True:
			self.titlestring += ', '+self.metadata['shunt-resistor-value']+'$\Omega$ shunt'
		else:
			self.titlestring += ', no shunt'
		if self.metadata['bias-resistor-value'] != '':
			self.titlestring += ', bias resistor '+self.metadata['bias-resistor-value']+'$\Omega$'
		if self.metadata['date-time'] != '' or self.metadata['user'] != '':
			self.titlestring += '\n'
			if self.metadata['user'] != '':
				self.titlestring += 'Data taken by '+self.metadata['user']
			if self.metadata['date-time'] != '':
				self.titlestring += ' on '+self.metadata['date-time']
		return self.titlestring

	def setGraphTitle(self):
		if self.give_title.isChecked():
			self.fig_title = self.fig.suptitle(self.title.text())
			self.fig_title.set_visible(True)
		else:
			self.fig_title.set_visible(False)
		self.replot()

	def setExp(self):
		self.fig.set_dpi(float(self.dpi.text()))
		self.conversion_factors = {'in':1,'cm':1.0/2.54,'px':(1.0/float(self.dpi.text()))}
		self.image_height_inches = float(self.exp_height.text())*self.conversion_factors[self.exp_units.currentText()]
		self.image_width_inches = float(self.exp_width.text())*self.conversion_factors[self.exp_units.currentText()]
		self.fig.set_size_inches(self.image_width_inches,self.image_height_inches, forward=True)
		self.canvas.resize(float(self.dpi.text())*self.image_width_inches,float(self.dpi.text())*self.image_height_inches)
		self.replot()

	def replot(self):
		self.plot.set_xdata(self.data[0])
		self.plot.set_ydata(self.data[1])
		if self.manual_limits.isChecked():
			try:
				float(self.x_min.text())
				float(self.x_max.text())
				self.ax.set_xlim(float(self.x_min.text()),float(self.x_max.text()))
			except ValueError:
				pass
			try:
				float(self.y_max.text())
				float(self.y_min.text())
				self.ax.set_ylim(float(self.y_min.text()),float(self.y_max.text()))
			except ValueError:
				pass
			if self.x_min.text() == self.x_max.text() == '':
				self.ax.set_xlim(auto = True)
			if self.y_min.text() == self.y_max.text() == '':
				self.ax.set_ylim(auto = True)
		else:
			self.ax.set_xlim(auto = True)
			self.ax.set_ylim(auto = True)
			self.ax.relim()
			self.ax.autoscale_view()
		plt.tight_layout()
		if self.give_title.isChecked():
			try:
				self.base_of_text = self.fig_title.get_window_extent().get_points()[0][1]
				self.height_of_plot = float(self.dpi.text())*self.image_height_inches
				self.fig.subplots_adjust(top=((self.base_of_text/self.height_of_plot)-0.015))
			except AttributeError:
				pass
			except RuntimeError:
				pass
		self.canvas.draw()

	def calculateCurrents(self):
		if self.y_offset.isChecked():
			self.source_dataset = self.zeroed_measured_voltages
		else:
			self.source_dataset = self.measured_voltages

		if self.metadata['shunt'] == True:
			self.r_shunt = float(self.metadata['shunt-resistor-value'])
		else:
			self.r_shunt = float('inf')

		self.r_bias = float(self.metadata['bias-resistor-value'])
		self.calculated_currents = []
		for v, voltage in enumerate(self.source_dataset):
			self.v_meas = float(voltage)
			self.v_supp = float(self.supplied_voltages[v])
			self.calculated_currents.append((((self.v_supp-self.v_meas)/self.r_bias) - (self.v_meas/self.r_shunt))*1.0e6)

	def switchToCurrent(self):
		if self.yaxis_idevice.isChecked():
			self.calculateCurrents()
			self.data[1] = self.calculated_currents
			self.ax.set_ylabel('Current over device ($\mu$A)')
			self.replot()
		else:
			if self.y_offset.isChecked():
				self.data[1] = self.zeroed_measured_voltages
			else:
				self.data[1] = self.measured_voltages
			try:
				if max(self.data[1]) > 0.01:
					self.ax.set_ylabel('Measured voltage (V)')
				else:
					self.ax.set_ylabel('Measured voltage (mV)')
					self.data[1] = 1000 * np.array(self.data[1])
			except ValueError:
				self.ax.set_ylabel('Measured voltage (V)')
			self.replot()

	def handleVoltageOffsets(self):			
		if self.x_offset.isChecked():
			self.data[0] = self.zeroed_supplied_voltages
		else:
			self.data[0] = self.supplied_voltages

		if self.y_offset.isChecked() and not self.yaxis_idevice.isChecked():
			self.data[1] = self.zeroed_measured_voltages
		elif not self.y_offset.isChecked() and not self.yaxis_idevice.isChecked():
			self.data[1] = self.measured_voltages
		else:
			self.switchToCurrent()		
		self.replot()

	def deOffset(self,dataset,offset):
		return list(np.array(dataset)-offset)

	def verboseGraphToggle(self):
		if self.verbose_graph.isChecked():
			self.textstr = ''
			for key in sorted(self.metadata.keys()):
				self.textstr += str(key)+': '+str(self.metadata[key])+'\n'
			self.text_on_graph = self.ax.text(0.01, 0.99, self.textstr[:-1], transform = self.ax.transAxes, fontsize = 12,
				verticalalignment = 'top')
			self.replot()
		else:
			try:
				self.text_on_graph.remove()
			except AttributeError:
				pass
			self.replot()

	def setGridlines(self):
		if self.gridlines.isChecked():
			self.ax.set_axisbelow(True)
			self.ax.grid(b=True, color='grey', linestyle = '-')
		else:
			self.ax.grid(b=False)
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
		#self.setGeometry(300,300,300,200)
		self.resize(300,200)
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

class IVPlotSettings(QtGui.QMainWindow):
	def __init__(self,settings):
		super(IVPlotSettings, self).__init__()
		self.settings = settings
		self.se = self.settings['export']
		self.initUI()

	def initUI(self):
		self.yaxis_idevice = QtGui.QCheckBox('Supplied voltage vs device current')
		self.x_offset = QtGui.QCheckBox('Correct X offset')
		self.y_offset = QtGui.QCheckBox('Correct Y offset')
		self.verbose_graph = QtGui.QCheckBox('Verbose graph')
		self.manual_limits = QtGui.QCheckBox('Manual axes')
		self.x_max = QtGui.QLineEdit('')
		self.x_min = QtGui.QLineEdit('')
		self.y_max = QtGui.QLineEdit('')
		self.y_min = QtGui.QLineEdit('')
		self.gridlines = QtGui.QCheckBox('Axis gridlines')
		self.give_title = QtGui.QCheckBox('Graph title')
		self.dpi = QtGui.QLineEdit('')
		self.exp_width = QtGui.QLineEdit('')
		self.exp_height = QtGui.QLineEdit('')
		self.exp_units = QtGui.QComboBox(self)
		self.possible_units = ['in','cm','px']
		for unit in self.possible_units:
			self.exp_units.addItem(unit)

		self.checkables = [ ['title',self.give_title],
							['x_offset',self.x_offset],
							['y_offset',self.y_offset],
							['verbose',self.verbose_graph],
							['manual_axes',self.manual_limits],
							['grids',self.gridlines],
							['idvsv',self.yaxis_idevice]]

		self.textables = [  ['ymax',self.y_max],
							['ymin',self.y_min],
							['xmax',self.x_max],
							['xmin',self.x_min],
							['width',self.exp_width],
							['height',self.exp_height],
							['dpi',self.dpi]]

		self.ok = QtGui.QPushButton('OK')
		self.cancel = QtGui.QPushButton('Cancel')
		self.cancel.clicked.connect(self.close)
		self.ok.clicked.connect(self.passValuesBackAndClose)

		self.initFromSettings()

		self.grid = QtGui.QGridLayout()
		self.grid.setSpacing(10)

		self.manual_limits_widget = QtGui.QWidget()
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
		self.manual_limits_widget.setVisible(self.manual_limits.isChecked())

		self.export_widget = QtGui.QWidget()
		self.export_widget.export_grid = QtGui.QGridLayout()
		self.export_widget.vbox = QtGui.QVBoxLayout()
		self.export_widget.vbox.addWidget(QtGui.QLabel('Export settings'))
		self.export_widget.vbox.addLayout(self.export_widget.export_grid)
		self.export_widget.setLayout(self.export_widget.vbox)
		self.export_widget.export_grid.addWidget(QtGui.QLabel('Width:'),0,0)
		self.export_widget.export_grid.addWidget(self.exp_width,0,1)
		self.export_widget.export_grid.addWidget(QtGui.QLabel('Height:'),0,2)
		self.export_widget.export_grid.addWidget(self.exp_height,0,3)
		self.export_widget.export_grid.addWidget(QtGui.QLabel('DPI:'),1,0)
		self.export_widget.export_grid.addWidget(self.dpi,1,1)
		self.export_widget.export_grid.addWidget(QtGui.QLabel('Units:'),1,2)
		self.export_widget.export_grid.addWidget(self.exp_units,1,3)

		self.vbox = QtGui.QVBoxLayout()
		self.setLayout(self.vbox)

		self.gridsection1 = QtGui.QGridLayout()
		self.gridsection2 = QtGui.QGridLayout()
		self.gridsection3 = QtGui.QGridLayout()
		self.hbox = QtGui.QHBoxLayout()

		self.gridsection2.setSpacing(10)
		self.gridsection2.addWidget(self.give_title,0,0)
		self.gridsection2.addWidget(self.yaxis_idevice,1,0)
		self.gridsection2.addWidget(self.x_offset,2,0)
		self.gridsection2.addWidget(self.y_offset,3,0)
		self.gridsection2.addWidget(self.verbose_graph,4,0)
		self.gridsection2.addWidget(self.manual_limits,5,0)

		self.gridsection3.setSpacing(10)
		self.gridsection3.addWidget(self.gridlines)

		self.vbox.addLayout(self.gridsection2)
		self.vbox.addWidget(self.manual_limits_widget)
		self.vbox.addLayout(self.gridsection3)
		self.vbox.addWidget(self.export_widget)
		self.vbox.addLayout(self.grid)
		self.vbox.addStretch(1)

		self.manual_limits.toggled.connect(self.manual_limits_widget.setVisible)

		self.grid.addWidget(self.ok,10,0)
		self.grid.addWidget(self.cancel,10,1)

		self.mainthing = QtGui.QWidget()
		self.setCentralWidget(self.mainthing)
		self.mainthing.setLayout(self.vbox)
		#self.setGeometry(300,300,300,200)
		self.resize(300,200)
		self.setWindowTitle('I-V Settings')
		self.setWindowIcon(QtGui.QIcon(r'icons\settings.png'))
		self.show()

	def initFromSettings(self):
		for checkable in self.checkables:
			if self.se[checkable[0]] == True:
				checkable[1].setCheckState(QtCore.Qt.Checked)
			else:
				checkable[1].setCheckState(QtCore.Qt.Unchecked)

		for textable in self.textables:
			if self.se[textable[0]] == None:
				textable[1].setText('')
			else:
				textable[1].setText(str(self.se[textable[0]]))

		self.exp_units.setCurrentIndex(self.possible_units.index(self.se['unit']))

	def passValuesBackAndClose(self):
		for checkable in self.checkables:
			self.se[checkable[0]] = checkable[1].isChecked()

		for textable in self.textables:
			if textable[1].text() == '':
				self.se[textable[0]] = None
			else:
				self.se[textable[0]] = float(textable[1].text())
		self.se['unit'] = self.exp_units.currentText() 
		self.close()

class HelpWindow(QtGui.QWidget):
	def __init__(self):
		super(HelpWindow,self).__init__()
		self.view = QtWebKit.QWebView(self)
		self.view.load('help\help.html')
		
		self.layout = QtGui.QHBoxLayout()
		self.layout.addWidget(self.view)

		self.setLayout(self.layout)
		self.resize(800,600)
		self.setWindowTitle('I-V Tester help')
		self.setWindowIcon(QtGui.QIcon(r'icons\help.png'))
		self.show()

def main():
	app = QtGui.QApplication(sys.argv)
	ex = IVProg()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()