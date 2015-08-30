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
	print 'Warning: NO CHECKING IS PERFORMED ON SETTINGS! this could be unwise'
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
		saveAsAction.triggered.connect(self.save_as)

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

		settingsAction = QtGui.QAction(QtGui.QIcon(r'icons\settings.png'),'&Settings',self)
		settingsAction.setStatusTip('Edit global settings')
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

		#self.vMax.setInputMask('00.00;_')
		#self.vStep.setInputMask('00.00;_')

		self.shunt.stateChanged.connect(self.rShunt.setEnabled)
		self.shunt.setCheckState(QtCore.Qt.Checked)

		self.manualtemp.stateChanged.connect(self.temp.setEnabled)
		self.temp.setEnabled(False)

		self.vMax.returnPressed.connect(self.recalculateMovement)
		self.vStep.returnPressed.connect(self.recalculateMovement)
		self.nSteps.returnPressed.connect(self.recalculateMovement)
		self.lastEdited = [None,None]

		#
		#   Create layout
		#

		gridsection = QtGui.QGridLayout()
		gridsection.setSpacing(10)
		subgrid2 = QtGui.QGridLayout()
		subgrid1 = QtGui.QGridLayout()
		subgrid3 = QtGui.QGridLayout()

		gridsection.addWidget(QtGui.QLabel('Batch:'),0,0)
		gridsection.addWidget(self.batchName,0,1)
		gridsection.addWidget(QtGui.QLabel('Device:'),0,2)
		gridsection.addWidget(self.deviceId,0,3)

		gridsection.addWidget(QtGui.QLabel('SMA:'),1,0)
		gridsection.addWidget(self.sma,1,1)
		subgrid1.addWidget(self.manualtemp,0,0)
		subgrid1.addWidget(QtGui.QLabel('Temp:'),0,1)
		subgrid1.addWidget(self.temp,0,2)
		gridsection.addLayout(subgrid1,1,2,1,2)

		gridsection.addLayout(subgrid3,2,0,1,4)
		subgrid3.addWidget(QtGui.QLabel('Max voltage:'),0,0)
		subgrid3.addWidget(self.vMax,0,1)
		subgrid3.addWidget(QtGui.QLabel('Step size:'),0,2)
		subgrid3.addWidget(self.vStep,0,3)
		subgrid3.addWidget(QtGui.QLabel('Total steps:'),0,4)
		subgrid3.addWidget(self.nSteps,0,5)

		gridsection.addWidget(QtGui.QLabel('Rbias:'),3,0)
		gridsection.addWidget(self.rBias,3,1)
		subgrid2.addWidget(self.shunt,0,0)
		subgrid2.addWidget(QtGui.QLabel('Rshunt:'),0,1)
		subgrid2.addWidget(self.rShunt,0,2)
		gridsection.addLayout(subgrid2,3,2,1,2)

		gridsection.addWidget(QtGui.QLabel('Comments:'),4,0)
		gridsection.addWidget(self.comment,4,1,1,3)

		gridsection.addWidget(self.pbar,5,0,1,4)

		#
		#   Create matplotlib items
		#

		self.data=[[],[]]

		#self.fig =Figure(figsize=(250,250), dpi=72, facecolor=(1,1,1),edgecolor=(0,0,0))
		#self.ax = self.fig.add_subplot(1,1,1)
		self.fig = plt.figure(facecolor=(1,1,1),edgecolor=(0,0,0))
		self.ax = self.fig.add_subplot(1,1,1)
		self.plot, = plt.plot(*self.data)
		self.ax.set_xlabel('measured voltage (V)')
		self.ax.set_ylabel('supplied voltage (V)')
		#self.ax.set_xlim(-5,5)
		#self.ax.set_ylim(-5,5)
		self.canvas = FigureCanvas(self.fig)

		vbox = QtGui.QVBoxLayout()
		vbox.addLayout(gridsection)
		vbox.addWidget(self.canvas)
		vbox.addStretch(1)

		#
		#   Final pre-flight checks
		#

		mainthing.setLayout(vbox)
		self.settings = getSettings()
		self.setGeometry(300,300,450,500)
		self.setWindowTitle('I-V Tester')
		self.setWindowIcon(QtGui.QIcon(r'icons\plot.png'))
		self.biases = []
		self.filename = None
		self.statusBar().showMessage('Ready...')
		self.show()

	#
	#   Function definitions
	#

	def closeEvent(self,event):
		setSettings(self.settings)
		event.accept()

	def open(self):
		self.filename, _ = QtGui.QFileDialog.getOpenFileName(self,'Open file...','',"I-V data (*.txt);;All data (*.*)")
		print 'HANDLE PROCESSING OF FILE TO INPUT'
		self.statusBar().showMessage('Selected filename: '+str(self.filename)+' (Currently does nothing!)')

	def save(self):
		if self.filename == None:
			self.save_as()
		else:
			with open(self.filename,'w') as f:
				self.csvfile = csv.writer(f)
				for row in self.processMetadata()+['']+list(np.transpose(np.array(self.data))):
					self.csvfile.writerow(row)
			self.statusBar().showMessage('Saved to '+str(self.filename))

	def save_as(self):
		self.filename, _ = QtGui.QFileDialog.getSaveFileName(self,'Save as...','',"I-V data (*.txt);;All data (*.*)")
		if self.filename != None:
			self.save()
		
	def processMetadata(self,source=None):
		self.metacategories = {
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
					self.metacategories[row[0]].setChecked(row[1])


	def new(self):
		print 'REINITIALISE THE STATE, BARRING VALUES WHICH DON\'T CHANGE'
		self.statusBar().showMessage('Currently does nothing!')

	def replot(self):
		self.plot.set_xdata(self.data[0])
		self.plot.set_ydata(self.data[1])
		self.ax.relim()
		self.ax.autoscale_view()
		self.canvas.draw()

	def acquire(self):
		if len(self.biases) > 0:
			print 'RUN TEST FOR SIM900 BEFORE PROCEEDING, POST FAILURE TO STATUSBAR!!!'
			if not self.manualtemp.isChecked():
				self.sim900 = Sim900(self.settings['sim900addr'])
				self.temp.setText(str(self.sim900.query(self.settings['tsourcemod'],'TVAL? '+str(self.settings['tinput'])+',1')))
				self.sim900.close()
			self.haltAction.setEnabled(True)
			self.acquireAction.setEnabled(False)
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
		self.biasesChanged = False
		if not (self.sender() == self.lastEdited[0] and None not in self.lastEdited):
			self.lastEdited = [self.sender(),self.lastEdited[0]]
		if self.vMax in self.lastEdited and self.vStep in self.lastEdited:
			try:
				self.nSteps.setText(str( int(float(self.vMax.text())/float(self.vStep.text())*4 + 1 )))
				self.biasesChanged = True
			except ZeroDivisionError:
				pass
		if self.vMax in self.lastEdited and self.nSteps in self.lastEdited:
			try:
				self.vStep.setText(str( float(self.vMax.text())/((float(self.nSteps.text())-1)/4.0) ))
				self.biasesChanged = True
			except ZeroDivisionError:
				pass
		if self.vStep in self.lastEdited and self.nSteps in self.lastEdited:
			try:
				self.vMax.setText(str( ((float(self.nSteps.text())-1)/4.0)*float(self.vStep.text()) ))
				self.biasesChanged = True
			except ZeroDivisionError:
				pass
		if self.biasesChanged == True:
			self.biasPrimitive = np.linspace(0,float(self.vMax.text()),int((float(self.nSteps.text())-1)/4.0)+1)
			self.biases = list(self.biasPrimitive) + list(self.biasPrimitive[::-1])[1:] + list(-self.biasPrimitive)[1:] + list((-self.biasPrimitive)[::-1])[1:-1] + [0]

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
		self.finished.emit()

	def initSim(self):
		self.sim = Sim900(self.settings['sim900addr'])
		self.sim.write(self.settings['vsourcemod'],'OPON')

	def setAndGetSimVoltages(self,biaspoint):
		self.sim.write(self.settings['vsourcemod'],'VOLT '+str('%.3f' % biaspoint))
		time.sleep(0.5)
		self.data[0].append(float(self.sim.query(self.settings['vmeasmod'],'VOLT? '+str(self.settings['vsourceinput'])+',1')))
		self.data[1].append(float(self.sim.query(self.settings['vmeasmod'],'VOLT? '+str(self.settings['vmeasinput'])+',1')))


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
		self.grid.addWidget(QtGui.QLabel('\tSensor input channel:'),4,0)
		self.grid.addWidget(self.tinput,4,1)
		self.grid.setRowMinimumHeight(5,10)
		self.grid.addWidget(QtGui.QLabel('<b>SIM970 voltmeter module:</b>'),6,0)
		self.grid.addWidget(self.vmeasmod,6,1)
		self.grid.addWidget(QtGui.QLabel('\tSource input channel:'),7,0)
		self.grid.addWidget(self.vmeasinput,7,1)
		self.grid.addWidget(QtGui.QLabel('\tMeasured input channel:'),8,0)
		self.grid.addWidget(self.vsourceinput,8,1)
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
