# -*- coding: utf-8 -*-
from serial import *
import math
from numpy.linalg import inv
import math
import numpy
import serial
import threading, time

from BridgeConf import BridgeClass, BridgeConfClass, BridgeCoordClass

IDLE                = 0
INIT_SYSTEM         = 1
DONNING             = 2
REST_POSITION       = 3
READY               = 4
RUNNING             = 5
ERROR               = 6
SPEED_CTRL          = 7
POS_CTRL            = 8

class Joint:

    def __init__(self, Num, COM, Patient, Exo, Coord):

        self.Num            = Num
        self.CommPort       = ""
        self.Ratio          = Exo.Jratio[Num-1]         # reduction ratio
        self.Offset         = Exo.Joffset[Num-1]        # home (0 step) position (deg)
        self.Jdef           = Patient.Jdef[Num-1]       # lo uso come target iniziale
        self.Jrest          = Patient.Jrest[Num-1]      # lo uso come posizione di rest post donning
        self.JminExo        = Exo.Jmin[Num-1]           # min joint angular position
        self.JmaxExo        = Exo.Jmax[Num-1]           # max joint angular position
        self.Jmin           = 0                         # patient min
        self.Jmax           = 0                         # patient max
        self.InitError      = False

        if not self.SetRange(Patient.Jmin[Num-1], Patient.Jmax[Num-1]):
            self.InitError = True

        " Degrees value of one step "
        self.StepDegrees    = 1.8

        " Current position "
        self.Position       = 0
        self.PositionDeg    = 0

        self.Connected      = False
        self.Homed          = False
        self.Coord          = Coord
        self.Timeout        = False

        self.Port           = serial.Serial()

        self.ForceExit      = False

        self.RestDone       = False

        self.SetPort(COM)
        

    " Set serial port "
    def SetPort(self, name):
        self.CommPort = name


    " Set joint range "
    def SetRange(self, jmin, jmax):
        if jmin > jmax:
            self.Jmin           = self.JminExo
            self.Jmax           = self.JmaxExo
            return False
            
        if jmin < self.JminExo:
            self.Jmin = self.JminExo
        else:
            self.Jmin = jmin
        
        if jmax > self.JmaxExo:
            self.Jmax = self.JmaxExo
        else:
            self.Jmax = jmax
    
    " Check the controller response "
    def ReplyCheck(self, sentcmd):

        stream  = str()
        looppa  = 1
        

#        while not stream.endswith("\r",stream):
        while looppa == 1:

            cnt     = 0

            " Wait for data in the RXbuffer "
            while self.Port.inWaiting() < 1:
                cnt += 1

                if cnt > 100:
                    self.Timeout = True
                    return False

                time.sleep(0.01)
                
            try:
                newchar = self.Port.read(1)
            except:
                return False

            if newchar == '\r':
                cmd_reply = stream + newchar
                looppa = 0
            else:
                stream += newchar
        
        # print 'reply:' + cmd_reply
        
        " escludo il cancelletto dal confronto "
        if cmd_reply == sentcmd[1 : ]:
            return True

        else:
            print " ReplyCheck() - Wrong Reply"
            return False
        
    " set up one or more parameters "
    def WriteCmd(self, command):

        for cmd_el in command:

            try:
                self.Port.write(cmd_el)
            except:
                print "WriteCmd() failed."
                return False

            ret = self.ReplyCheck(cmd_el)

            if ret == False:
                return False
                
        return True


    def WriteCmdOrig(self, command):

        ok_flag = True
        
        for cmd_el in command:
            
            try:
                self.Port.write(cmd_el)
                #print 'sent command: ' + cmd_el
                
                if self.ReplyCheck(cmd_el) == 1:
                    ok_flag = True
                    #print 'Config sent correctly'
                else:
                    ok_flag = False
                    print 'Wrong Reply to Config 2'
            except Exception, e:
                print 'WriteCmd() failed. ' + str(e)
                return False
                
        return ok_flag

    def ReadCmd(self, command):
        
        try:
            self.Port.write(command)
            #print 'parameter to read: ' + command
            
            stream = str()
            looppa = 1

#           while not stream.endswith("\r",stream):
            while looppa == 1:

                #wait for data in the RXbuffer
                while self.Port.inWaiting() < 1:
                    time.sleep(0.01)
                
                newchar = self.Port.read(1)

                if newchar == '\r':
                    cmd_reply = stream + newchar
                    looppa = 0               
                    #print cmd_reply      
                else:
                    stream += newchar

                if self.ForceExit:
                    return
            #print 'reply:' + cmd_reply
            #cmd_reply = cmd_reply[1 : ] #ELIMINO CANCELLETTO DA RIMUOVERE!!!
            #print 'mod reply: ' + cmd_reply
            #print 'comm_t', command[1:len(command)-1]            
            #print 'reply_t', cmd_reply[ : len(command)-2]
            
            #command = command[1 : ]
#            if cmd_reply[ : 2] == command[1:3] :  #escludo il cancelletto dal confronto
            if cmd_reply[ : len(command)-2] == command[1:len(command)-1] :  #escludo il cancelletto dal confronto
                #if true, the controller response is relative to my query
                #so the value is after the header (and before the terminator)
                #value = int(cmd_reply[2: -1])
                #print 'valstring', cmd_reply[len(command)-2: -1]
                value = int(cmd_reply[len(command)-2: -1])
                #print 'val', value
                #print "Config sent correctly"
                return value
            else:
                print 'Wrong Reply to Read'
                return 0
        except Exception, e:
            print 'ReadCmd() failed | ' + str(e)
            return 0

                
    def OpenPort(self):
        try:
            self.Port.port     = self.CommPort
            self.Port.baudrate = 115200
            self.Port.parity   = serial.PARITY_NONE
            self.Port.stopbits = serial.STOPBITS_ONE
            self.Port.bytesize = serial.EIGHTBITS
            self.Port.timeout  = 0.1
            
            self.Port.open()
            self.Port.isOpen()

            self.Port.flush()
            self.Port.flushInput()
            self.Port.flushOutput()
            self.Connected = True

            return True
        except Exception, e:
            self.Connected = False
            print e
            return False

    " Close serial port "
    def ClosePort(self):

        " Stop the joint motor "
        command = "#1S\r"
        
        try:            
            self.Port.write(command)
            self.Port.flush()
        
            time.sleep(0.1)
            
            self.Port.flushInput()
            self.Port.flushOutput()
            self.Port.close()
            self.Connected = False
            return True

        except Exception, e:
            print e
            return False
    
    " Send the target position to the controller (deg) "
    def SetPositionDeg(self, p0deg):

        " Check if the desired value is in the correct range "
        if p0deg >= self.Jmin and p0deg <= self.Jmax:
            " Calculate deg to step "
            p0step = self.deg2step(p0deg - self.Offset)

        '''
        elif p0deg <= self.Jmin + 3:

            print 'J%d out of range (<min)' % self.Num
            p0step = self.deg2step(self.Jmin + 3 - self.Offset)

        elif p0deg >= self.Jmax - 3:

            print 'J%d out of range (>max)' % self.Num
            p0step = self.deg2step(self.Jmax - 3 - self.Offset)
        '''
        " Get current position "
        self.Position = self.GetPositionDeg()
        print self.Position
        self.PositionStep = self.GetPositionStep()
        print self.PositionStep
        # print '!!! Posizione corrente thread set position: ', self.Position

        print 'J%d p0step: '   % self.Num, p0step
        print 'J%d p0step actual: ' % self.Num, self.PositionStep


        if abs(p0step - self.PositionStep) <= 2:

            print 'J%d Stop' % self.Num
            return True, self.Position

        else:

            print 'J%d Move' % self.Num
            targetpos = "#1s%d\r" % p0step
            command = [targetpos, "#1A\r"]  #Target Position, Start Movement
            self.WriteCmd(command)
            return False, self.Position


    def SetMinSpeedHz(self, speed ):

        if speed > 0:
            " Orario "
            targetdirection = "#1d0\r"
        else:
            " Antiorario "
            targetdirection = "#1d1\r"

        speed = abs(speed)



        " Check if the desired value is in the correct range "
        if speed > 25 and speed <= 25000:
            targetspeed = "#1u%d\r" % speed
            command = [targetdirection, targetspeed]
            return self.WriteCmd(command)
        else:
            print 'velocity out of range'
            return False, -1

    def SetMaxSpeedHz(self, speed):

        # TODO: check array [1 1 -1 1 1] "

        # if self.Num == 3:
        #    speed = speed * -1

        " NON PUOI DARE RIFERIMENTO 0 "
        if speed == 0:
            speed = 1

       
        if speed > 0:
            " Antiorario "
            targetdirection = "#1d1\r"
        else:
            " Orario "
            targetdirection = "#1d0\r"



        speed = abs(speed)

        if speed < 5:
            speed = 5

        #check che sia nel range
        if speed >= 0 and speed <= 25000:
            targetspeed = "#1o%d\r" % speed
            command = [targetdirection, targetspeed]  #target position, start movement
            print 'Speed J%d: ' % self.Num + targetspeed
            return self.WriteCmd(command)
        else:
            print 'Velocity out of range'
            return False, -1

    def StartSpeed(self):
        command = ["#1D0\r", "#1D0\r"]
        self.WriteCmd(command)
        time.sleep(1)

        command = ["#1y10\r","#1A\r"]    #first record (homing) and start
        self.WriteCmd(command)

    def Stop(self):
        command = ["#1S\r","#1S\r"]
        self.WriteCmd(command)
        time.sleep(0.01)

    def Start(self):
        command = ["#1A\r"]
        self.WriteCmd(command)
        time.sleep(0.01)

    def HomingQuery(self):

        "Reset the position error "
        command = ["#1D0\r", "#1D0\r"]
        self.WriteCmd(command)

        time.sleep(0.5)

        " First Reference Query"
        if self.ReadCmd("#1:is_referenced\r") == 0:

            " Select record #2 (homing) and run the motor "
            command = ["#1y2\r","#1A\r"]
            self.WriteCmd(command)

            while self.ReadCmd("#1:is_referenced\r") == 0:

                if not self.Port.isOpen():
                    return False

                time.sleep(0.5)

        return True


    def DriveErrorClear(self):
        command = ["#1D0\r", "#1D0\r"]
        self.WriteCmd(command)
        #print 'DriveErrorClear'
    
    "Read the actual position from the controller (deg)"
    def GetPositionDeg(self):
        return self.step2deg(self.ReadCmd("#1I\r")) + self.Offset

    "Read the actual position from the controller (step)"
    def GetPositionStep(self):
        return self.ReadCmd("#1I\r")

    "Return the conversion deg -> step"
    def deg2step(self,pdeg):
        return int(pdeg * self.Ratio / self.StepDegrees)
        
    "Return the conversion step -> deg"
    def step2deg(self, pstep):
        return (pstep / (self.Ratio / self.StepDegrees))

    "Set the Position Mode: Profile #1"
    def SetPositionMode(self):
        command = ["#1y1\r", "#1p2\r"]

        while self.WriteCmd(command) == False:
            time.sleep(1)

    "Start the Motor"
    def MotorStart(self):
        command = ["#1A\r"]

        try:
            while self.WriteCmd(command) == False:
                time.sleep(1)
        except Exception, e:
            print 'WriteCmd() failed. ' + str(e)
            return False

    "Test the Motor"
    def MotorTest(self):

        command = ["#1D0\r","#1y1\r", "#1p2\r"]

        try:
            while self.WriteCmd(command) == False:

                if self.Timeout:
                    return False

                time.sleep(1)

        except Exception, e:
            print 'WriteCmd() failed. ' + str(e)
            return False

        command = ["#1s100\r","#1A\r"]

        try:
            while self.WriteCmd(command) == False:
                if self.Timeout:
                    return False

                time.sleep(1)

        except Exception, e:
            print 'WriteCmd() failed. ' + str(e)
            return False

        time.sleep(2)

        command = ["#1s-100\r","#1A\r"]
        try:
            while self.WriteCmd(command) == False:
                if self.Timeout:
                    return False

                time.sleep(1)

        except Exception, e:
            print 'WriteCmd() failed. ' + str(e)
            return False

        time.sleep(2)

        return True

    def joint_increment(self,step_number):

        #imposto modalità di controllo in posizione, posizione assoluta (é necessario ? dopo l'inizializzazione non è già impostata?)

        command = ["#1y1\r", "#1p2\r"]

        try:
            while self.WriteCmd(command) == False:

                if self.Timeout:
                    return False

                time.sleep(1)
        except Exception, e:
            print 'WriteCmd() failed. ' + str(e)
            return False

        targetpos = "#1s%d\r" % (step_number*100)

        command=[targetpos, "1A\r"]

        try:
            while self.WriteCmd(command) == False:
                if self.Timeout:
                    return False

                time.sleep(1)

        except Exception, e:
            print 'WriteCmd() failed. ' + str(e)
            return False

        time.sleep(2)

        return True

    def joint_decrease(self,step_number):

        command = ["#1y1\r", "#1p2\r"]

        try:
            while self.WriteCmd(command) == False:

                if self.Timeout:
                    return False

                time.sleep(1)
        except Exception, e:
            print 'WriteCmd() failed. ' + str(e)
            return False

        targetpos = "#1s%d\r" % (step_number*-100)

        command=[targetpos, "1A\r"]

        try:
            while self.WriteCmd(command) == False:
                if self.Timeout:
                    return False

                time.sleep(1)

        except Exception, e:
            print 'WriteCmd() failed. ' + str(e)
            return False

        time.sleep(2)

        return True

" ####################"
"  JOINT INIT THREAD  "
" ####################"
class Thread_JointInitClass(threading.Thread):

    def __init__(self, Name, Jj):
        threading.Thread.__init__(self)
        self.Name           = Name
        self.Running        = False
        self.Jn             = Jj
        
    def run(self):

        self.Running = True
        
        " Start Homing Procedure "

        print 'J%d - Homing start' % self.Jn.Num

        if self.Jn.HomingQuery() == False:

            print '# ERROR: J%d HomingQuery() failed' % self.Jn.Num
            return

        print 'J%d - Homing done' % self.Jn.Num

        command = ["#1D0\r", "#1D0\r"]
        self.Jn.WriteCmd(command)
        time.sleep(0.5)
        
        " Get motor position "
        homing_position = self.Jn.GetPositionDeg()
        print 'J%d - Homing position (deg: %d | step: %d):' % (self.Jn.Num, homing_position, self.Jn.deg2step(homing_position))
        
        time.sleep(0.5)
        
        " Configure the controller with the following settings:"
        " a) record 2 "
        " b) absolute position "
        command = ["#1y1\r", "#1p2\r"]
        
        while self.Jn.WriteCmd(command) == False:
            time.sleep(1)
        
        time.sleep(0.1)
        
        
        " Set the donning position "
        if self.Jn.Num != 1:         
            self.Jn.SetPositionDeg(self.Jn.Jdef)
     
            while abs(self.Jn.GetPositionDeg() - self.Jn.Jdef) > 2.0:
                print '**** Sto andando a target position, J%d - %d' % (self.Jn.Num, self.Jn.GetPositionDeg())
                time.sleep(1)

        self.Jn.Position = self.Jn.GetPositionDeg()

        print 'J%d - In position (%f)' % (self.Jn.Num, self.Jn.GetPositionDeg())       

        " Set home flag "
        self.Jn.Homed = True

        print ' J%d - target position (%f)' % (self.Jn.Num, self.Jn.Jdef)
        
    def terminate(self):
        " Exit the thread "
        self.Running = False

" ################################# "
"  JOINT INIT REST POSITION THREAD  "
" ################################# "
class Thread_JointRestPositionClass(threading.Thread):

    def __init__(self, Name, Jj):
        threading.Thread.__init__(self)
        self.Name           = Name
        self.Running        = False
        self.Jn             = Jj
        
    def run(self):
        self.Running = True
        
        " Leggo posizone in STEP "
        currentPosition = str(self.Jn.ReadCmd("#1I\r"))

        " Resetto "
        # command = ['#1D0', '#1D'+ currentPosition +'\r']
        
        command = ['#1D0\r']
        try:
            while self.Jn.WriteCmd(command) == False:
                
                if self.Jn.Timeout:
                    return False

                time.sleep(1)

        except Exception, e:
            print 'WriteCmd() failed. ' + str(e)
            return False

        command = ['#1D'+ currentPosition +'\r']

        try:
            while self.Jn.WriteCmd(command) == False:
                
                if self.Jn.Timeout:
                    return False

                time.sleep(1)

        except Exception, e:
            print 'WriteCmd() failed. ' + str(e)
            return False


        " Set the rest position "
        self.Jn.SetPositionDeg(self.Jn.Jrest)

        while abs(self.Jn.Jrest - self.Jn.GetPositionDeg()) > 1:
            if not self.Running:
                print 'parte sbagliata del while'
                self.Jn.RestDone = False
                return False

            time.sleep(0.5)

        self.Jn.Position = self.Jn.GetPositionDeg()
        print self.Jn.Position
        self.Jn.RestDone = True
        
    def terminate(self):
        " Exit the thread "
        self.Running = False
    
" ##################### "
"  JOINT UPDATE THREAD  "
" ##################### "
class Thread_JointUpdateClass(threading.Thread):
    def __init__(self, Name, Jj, Coord, Bridge):
        threading.Thread.__init__(self)
        self.Name           = Name
        self.Running        = False
        self.Jn             = Jj
        self.FirstStart     = True
        " TODO: valutare tempi meno stringenti (originale 0.1) "
        self.Period         = 0.2
        self.StopPosition   = None
        self.OldStatus      = IDLE
        self.Bridge         = Bridge
        self.Coord          = Coord
        
    def run(self):

        self.Running   = True

        " Position ctrl, absolute position "
        #command = ["#1y2\r", "#1p2\r"]

        command = ["#1y3\r", "#1s0\r", "#1A\r"]

        while self.Jn.WriteCmd(command) == False:
            time.sleep(1)

        " Get current position "
        self.Jn.Position = self.Jn.GetPositionDeg()
        print 'J%d Pos: %f' % (self.Jn.Num, self.Jn.Position)
        
        while self.Running:

            try:
                " Measure process time "
                t0 = time.clock()

                " Detecting New Status (POSITION vs SPEED Control)"
                if self.Bridge.Control.Status != self.OldStatus:
                    self.OldStatus = self.Bridge.Control.Status

                    self.Jn.Position = self.Jn.GetPositionDeg()
                    print 'J%d Pos: %.1f' % (self.Jn.Num, self.Jn.Position)


                    if self.Bridge.Control.Status == SPEED_CTRL:

                        print ' J%d Speed Control ' % self.Jn.Num

                        " Speed Control, Speed Reference  "
                        command = ["#1y10\r", "#1o1\r", "#1A\r"]

                    elif self.Bridge.Control.Status == POS_CTRL:

                        print ' J%d Position Control ' % self.Jn.Num

                        # "Position Control - Absolute Position"
                        # command = ["#1y1\r", "#1p2\r", "#1A\r"]

                        "Position Control - Relative Position"
                        command = ["#1y3\r", "#1s0\r", "#1A\r"]

                    else:
                        command = ["#1y3\r", "#1p2\r"]

                    while self.Jn.WriteCmd(command) == False:
                        time.sleep(1)

                    if self.Bridge.Control.Status == POS_CTRL:
                        time.sleep(0.1)
                        #self.Position = self.Jn.GetPositionDeg()



                " If the control is enabled "
                if self.Bridge.Control.Status == SPEED_CTRL:
                    
                    " Set speed "
                    #print '!!! Sono a set speed !!!'
                    self.Jn.Position = self.Jn.GetPositionDeg()
                    self.Jn.SetMaxSpeedHz(self.Jn.deg2step(self.Coord.Jv[self.Jn.Num-1]))
                    # print (self.Coord.Jv[self.Jn.Num-1] * self.Jn.Ratio/360)

                elif self.Bridge.Control.Status == POS_CTRL:

                    self.Jn.Position = self.Jn.GetPositionDeg()


                    " TODO: cosa succede se il sistema e' forzato? "
                    #self.Jn.SetPositionDeg(self.Jn.GetPositionDeg())

                elapsed_time = time.clock() - t0

                if elapsed_time > self.Period:
                    print ' - JointUpdate %d: overrun' % self.Jn.Num

                else:

                    time.sleep(self.Period - elapsed_time)

            except Exception, e:
                print 'Thread_JointUpdate %d failure. %s' % (self.Jn.Num, str(e))


        print ' - JointUpdate %d: thread exit' % self.Jn.Num

    def terminate(self):
        print 'AAAAAAAAAAAAAAAAAAAAA 1'
        " Close the serial port "
        try:
            print 'AAAAAAAAAAAAAAAAAAAAA 2'
            self.Jn.ForceExit = True
            time.sleep(0.1)
            self.Jn.ClosePort()
        except:
            print 'Errore chiusura Port seriale'

        
        " Exit the thread "
        self.Running = False