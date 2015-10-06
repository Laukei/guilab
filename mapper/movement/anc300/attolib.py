#
#   ~Rob Heath's Amazing, Flying~
#          ~ANC300/ANP200 Easy-Access Library!~
#
#  !! WARNING: NEITHER EASY NOR ACCESSIBLE !!
#         !! PROCEED WITH CAUTION !!
#
#         TRESSPASSERS WILL BE SHOT
#
#    Version 0.3 Implemented better homing
#      Version 0.2 PyVISA 1.6 compatible
#        Version 0.1 Proof-of-concept
#

import visa
import time
import math
import numpy as np

# Desirable features:
#  o Single-command setup of stages/readout
#  o Single-command movement (up/down)
#  o Single-command movement *to a location*

class Stages:
    '''
    class Stages connects to Stages_port and sets up motors using aidmap
    '''
    def __init__(self,Stages_port,**kwargs):
        '''
        initialises Stages; takes x/y/z freq+volt kwargs
        (xvolt, yvolt, zvolt, xyvolt, yzvolt, xzvolt, xyzvolt
        and analogues for freq where volt is replaced textually)
        also takes aidmap kwarg, which redefines the Axis ID map
        (connecting a channel to an alias). This is by default:
        aidmap = {'x':3, 'y':2, 'z':1}
        '''
        self.aidmap = {'x':3, 'y':2, 'z':1} #axis ID map
        #print 'initialising device on',Stages_port
        self.rm = visa.ResourceManager()
        self.instrument = self.rm.open_resource(Stages_port, baud_rate = 38400)
        #self.instrument = visa.SerialInstrument(Stages_port, baud_rate = 38400, data_bits = 8, stop_bits = 1, parity = visa.no_parity)
        self.instrument.query_delay = 0.05
        self.instrument.write('echo on')
        self.empty_buffer()
        #self.get_capacitances()
        for key, value in kwargs.iteritems():
            if key == 'aidmap':
                if type(value)!=dict:
                    print 'malformed aidmap, should be dict'
                else:
                    self.aidmap = value
                continue
            self.axes = []
            for self.key in self.aidmap.keys():
                if self.key in key:
                    self.axes.append(self.key)
            if 'volt' in key:
                for axis in self.axes:
                    self.set_voltage(axis,value)
            elif 'freq' in key:
                for axis in self.axes:
                    self.set_frequency(axis,value)
            else:
                print 'malformed kwarg:',key,'=',value
        self.ground()

    def empty_buffer(self):
        while True:
            try:
                self.rawread()
            except visa.VisaIOError:
                break
    
    def write(self,command):
        '''
        args: command
        writes command to instrument
        NOTE: INSTRUMENT WILL REPLY 'OK' BECAUSE IT'S HATEFUL
        USE THE ASK COMMAND NOT THE WRITE COMMAND FOR EVERYDAY
        BUSINESS TO ENSURE THERE ISN'T A BUILDUP OF JUNK IN THE
        BUFFER!
        '''
        self.instrument.write(command)

    def rawread(self):
        '''
        raw reads from buffer; VisaIOError after timeout if nothing
        '''
        return self.instrument.read()

    def read(self):
        self.readbuffer = []
        while True:
            try:
                self.readbuffer.append(self.rawread().strip('\n').strip('>').strip())
                if self.readbuffer[-1] == 'OK':
                    break
            except visa.VisaIOError as e:
                raise e
        return self.readbuffer

    def query(self,command):
        '''
        writes command; returns read() result
        '''
        self.write(command)
        self.output = self.read()
        if self.output[0] != command:
            print 'Potentially malformed output; asked for '+str(command)+' but received '+str(self.output[0])
        if self.output[-1] != 'OK':
            print 'Output not OK'
        return self.output[1:-1]

    def lazyask(self,command):
        '''
        writes command, returns first line of meaningful read() result
        '''
        return self.query(command)[0]

    def tell(self,command):
        '''
        does an ask(), discards the returned value (because you're telling)
        '''
        self.result = self.query(command)
        if self.result != []:
            print self.result,'was unexpectedly returned from tell()'

    def set_voltage(self,axis,voltage):
        '''
        args: aidmap'able axis, voltage (V)
        will auto-cap at limit level
        '''
        self.tell('setv '+str(self.aidmap[axis])+' '+str(voltage))

    def set_frequency(self,axis,frequency):
        '''
        args: aidmap'able axis, freq (Hz)
        will auto-cap at limit level
        '''
        self.tell('setf '+str(self.aidmap[axis])+' '+str(frequency))

    def get_capacitances(self):
        '''
        prints all aidmap'able capacitances to screen (not returned)
        '''
        print 'Capacitances:'
        for self.key in sorted(self.aidmap.keys()):
            self.query('setm '+str(self.aidmap[self.key])+' cap')
            self.query('capw '+str(self.aidmap[self.key]))
            print self.key + ':',self.query('getc '+str(self.aidmap[self.key]))[0].split('= ')[1]
        
    def ground(self, axes = 'xyz'):
        '''
        optional arg: aidmap'able axes in string (eg: 'xy','xyz','z')
        '''
        self.axes = []
        for axis in self.aidmap.keys():
            if axis in axes:
                self.axes.append(axis)
        for axis in self.axes:
            self.query('setm '+str(self.aidmap[axis])+' gnd')

    def set_step(self,axis):
        '''
        sets system to step mode
        '''
        if self.lazyask('getm '+str(self.aidmap[axis])) != 'mode = stp':
            self.tell('setm '+str(self.aidmap[axis])+' stp')

    def stepu(self,axis,steps):
        '''
        steps up
        '''
        self.set_step(axis)
        self.tell('stepu '+str(self.aidmap[axis])+' '+str(steps))
        self.tell('stepw '+str(self.aidmap[axis]))

    def stepd(self,axis,steps):
        '''
        steps down
        '''
        self.set_step(axis)
        self.tell('stepd '+str(self.aidmap[axis])+' '+str(steps))
        self.tell('stepw '+str(self.aidmap[axis]))

class Readout:
    '''
    A class to encapsulate communication with the ARC200 readout
    '''
    def __init__(self,Read_port,**kwargs):
        '''
        initialises Readout
        also takes aidmap kwarg, which redefines the Axis ID map
        (connecting a channel to an alias). This is by default:
        aidmap = {'x':1, 'y':2, 'z':3} (reverse of Stages!)
        '''
        #print 'initialising device on',Read_port
        self.aidmap = {'x':1, 'y':2, 'z':3} #axis ID map
        self.rm = visa.ResourceManager()
        self.instrument = self.rm.open_resource(Read_port, baud_rate = 57600, data_bits = 8, stop_bits=visa.constants.StopBits.one, read_termination='', write_termination='')
        #self.instrument = visa.SerialInstrument( term_chars="")
        self.set_single_shot()
        self.empty_buffer()
        #print 'buffer clear'

    def set_single_shot(self):
        self.instrument.write('SM1')
        time.sleep(1)
        self.instrument.write('\r')

    def set_continuous(self):
        self.instrument.write('SM0')
        self.instrument.write('\r')

    def empty_buffer(self):
        '''
        empties the buffer
        '''
        while True:
            try:
                #print self.instrument.read()
                self.instrument.read()
            except:# visa.VisaIOError:
                break

    def position(self,axis=False):
        '''
        reads positions to dict of floats; takes optional axis argument to return just one value
        '''
        self.positionstring = [float(i) for i in self.query('C').split(',')]
        self.positions = {key:self.positionstring[self.aidmap[key]-1] for key in self.aidmap.keys()}
        if axis==False or axis not in self.aidmap:
            return self.positions
        else:
            return self.positions[axis]
        
        
    def read(self):
        '''
        read your favourite book
        '''
        return self.instrument.read()

    def write(self,command):
        '''
        write command
        '''
        self.instrument.write(command+'\r')

    def query(self,command):
        '''
        write then read command
        '''
        self.write(command)
        return self.read()

    def close(self):
        '''
        closes gracefully
        '''
        self.set_continuous()
        self.instrument.close()

class LockIn:
    '''
    smart object that allows smart movement
    '''
    def __init__(self,LockIn_port):
        self.rm = visa.ResourceManager()
        self.instrument = self.rm.open_resource(LockIn_port, read_termination = '\r\n')
        self.aidmap = {'x':2, 'y':3}
        
    def write(self,command):
        self.instrument.write(command)

    def read(self):
        return self.instrument.read()

    def query(self,command):
        return self.instrument.query(command)

    def get_reflection(self):
        return float(self.instrument.query('ADC. 1'))

    def rawmove(self,axis,value):
        try:
            self.write('DAC. '+str(self.aidmap[axis])+" %.3f" % (value))
        except KeyError as e:
            print 'Unrecognised key! {0}: {1}'.format(e.errno, e.strerror)
        
    def move(self,axis,value):
        try:
            self.current_position = float(self.query('DAC. '+str(self.aidmap[axis])))
            if abs(value - self.current_position)<=1.0:
                self.write('DAC. '+str(self.aidmap[axis])+" %.3f" % (value))
            else:
                self.steps = np.linspace(self.current_position, value, math.ceil(abs(value-self.current_position))+1)[1:]
                for step in self.steps:
                    self.write('DAC. '+str(self.aidmap[axis])+" %.3f" % (step))
                    time.sleep(0.05)
        except KeyError as e:
            print 'Unrecognised key! {0}: {1}'.format(e.errno, e.strerror)

    def close(self):
        self.instrument.close()
    

class SmartStage:
    '''
    smart object that uses stages and readout to allow 'closed loop' operation
    '''
    def __init__(self,Stages_port,Read_port,**kwargs):
        self.ANC300 = Stages(Stages_port,**kwargs)
        self.ARC200 = Readout(Read_port)

    def check_input_pos(self,pos):
        if pos > 5 or pos < 0:
            raise ValueError

    def close(self):
        self.ARC200.close()

    def move_past(self,axis,pos,clicks=10):
        self.check_input_pos(pos)
        self.curpos = self.ARC200.position(axis)
        self.direction = math.copysign(1,pos-self.curpos)
        if self.direction == -1:
            self.move = self.ANC300.stepd
        elif  self.direction == 1:
            self.move = self.ANC300.stepu
        self.steps = 0
        while True:
            self.steps += 1
            self.move(axis,clicks)
            if self.direction == -1 and self.ARC200.position(axis) <= pos:
                break
            if self.direction == 1 and self.ARC200.position(axis) >= pos:
                break
        return self.steps

    def move_to_near(self,axis,pos,clicks=10):
        self.tolerance = 0.001 #accurate to 1micron
        self.check_input_pos(pos)
        self.curpos = self.ARC200.position(axis)
        self.direction = math.copysign(1,pos-self.curpos)
        if self.direction == -1:
            self.move = self.ANC300.stepd
        elif  self.direction == 1:
            self.move = self.ANC300.stepu
        while True:
            self.move(axis,clicks)
            time.sleep(0.01)
            self.curpos = self.ARC200.position(axis)
            if abs(self.curpos-pos) <= self.tolerance:
                #print 'STOP! Arrived!'
                return True
            elif (self.direction == -1 and self.curpos < pos) or (
                  self.direction == 1 and self.curpos > pos):
                #print 'on this pass, we overshot'
                return False


    def move_to(self,axis,pos,start_steps=100):
        self.check_input_pos(pos)
        if start_steps == 10**math.floor(math.log10(start_steps)):
            self.step_size = list(np.logspace(math.floor(math.log10(start_steps)),0,math.floor(math.log10(start_steps))+1))
        else:
            self.step_size = [float(start_steps)]+list(np.logspace(math.floor(math.log10(start_steps)),0,math.floor(math.log10(start_steps))+1))
        for steps in self.step_size:
            self.result = self.move_to_near(axis,pos,int(steps))
            if self.result == True:
                return True
        return False