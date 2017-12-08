# -*- coding: utf-8 -*-
#!/usr/bin/env python

import os
import sys
import time
import threading
import datetime
import pygame
import numpy
import math

import BRIDGE_GUI

from BridgeConf        import *
from BridgeDialog      import *
from BridgeCtrl_V2     import *
from BridgeJoint       import *
from BridgeInput       import *

import wx
from wx.lib.wordwrap import wordwrap
from wx.lib.pubsub import setuparg1 #evita problemi con py2exe
from wx.lib.pubsub import pub as Publisher

import serial

import matplotlib
matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.axes3d import get_test_data
import matplotlib.animation as animation
from matplotlib.patches import Ellipse, Polygon
from matplotlib import cm
#import subprocess
import scipy.io as spio
import winsound

# TODO: sistemare audio
# audio_file = "/Users/AlessandraCalcagno/Desktop/Tesi/Vocale/"

" ############## "
" #PLOT 3D EXO # "
" ############## "

class CreatePlot3DExo(wx.Panel):

    def __init__(self,parent,Conf):

        wx.Panel.__init__(self,parent)

        self.Conf     = Conf
        self.dpi      = 75
        self.dim_pan  = parent.GetSize()
        self.figure   = Figure(figsize=(self.dim_pan[0]*1.0/self.dpi,(self.dim_pan[1])*1.0/self.dpi), dpi=self.dpi)
        
        sysTextColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        col_norm      = (sysTextColour[0]*1.0/255, sysTextColour[1]*1.0/255, sysTextColour[2]*1.0/255)
        
        self.figure.patch.set_facecolor(col_norm)


        # Canvas
        self.canvas = FigureCanvas(parent, -1, self.figure)
        sizer1 = wx.BoxSizer(wx.VERTICAL)
        sizer1.Add(self.canvas, 1, wx.ALL | wx.EXPAND)

        self.ax = self.figure.add_subplot(1, 1, 1, projection='3d')
        self.ax.axis('equal')

        self.ax.set_xlim3d(-(self.Conf.Patient.l1+self.Conf.Patient.l2+self.Conf.Patient.l3),(self.Conf.Patient.l1+self.Conf.Patient.l2+self.Conf.Patient.l3))
        self.ax.set_ylim3d(-(self.Conf.Patient.l1+self.Conf.Patient.l2+self.Conf.Patient.l3),(self.Conf.Patient.l1+self.Conf.Patient.l2+self.Conf.Patient.l3))
        self.ax.set_zlim3d(-(self.Conf.Patient.l1+self.Conf.Patient.l2+self.Conf.Patient.l3),(self.Conf.Patient.l1+self.Conf.Patient.l2+self.Conf.Patient.l3))

        marker_style = dict(linestyle='-', color=[0.2, 0.2, 0.2], markersize=20)
        self.line = self.ax.plot([], [], [], marker='o', **marker_style)[0]
        marker_style2 = dict(linestyle='-', color='red', markersize=15)
        self.line2 = self.ax.plot([], [], [], marker='o', **marker_style2)[0]

        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')

        #self.ax.set_xticklabels([])
        #self.ax.set_yticklabels([])
        #self.ax.set_zticklabels([])


        self.ax.view_init(elev=50., azim=50)
        #self.ax.view_init(elev=0, azim=270)

        parent.SetSizer(sizer1)
        parent.Fit()

" ################## "
" # TERMINAL CLASS # "
" ################## "

class ChildFrame(BRIDGE_GUI.BridgeTerminal):
    def __init__(self, parent):
        BRIDGE_GUI.BridgeTerminal.__init__(self, parent)


" ############# "
" # GUI CLASS # "
" ############# "

class MainWindow(BRIDGE_GUI.BridgeWin):
    def __init__(self, parent):

        BRIDGE_GUI.BridgeWin.__init__(self, parent)

        # Define bridge configurations
        self.Bridge = BridgeClass()
        self.Conf   = BridgeConfClass()
        self.Coord  = BridgeCoordClass()

        " Initialize plots "
        self.exo3d_plot     = CreatePlot3DExo(self.exo3d_container,self.Conf)
        self.ani            = animation.FuncAnimation(self.exo3d_plot.figure, self.animate, fargs=[],interval = 500)
        self.len 			= self.Conf.Patient.l1+self.Conf.Patient.l2+self.Conf.Patient.l3
        " Initialize plots "
        self.statusbar.SetFieldsCount(4)
        self.statusbar.SetStatusWidths([-23,-3,-3,-3])
        self.statusbar.SetStatusText('Ready', 0)
        self.statusbar.SetStatusText('COM: -', 1)
        self.statusbar.SetStatusText('Patient: None', 2)
        self.statusbar.SetStatusText('Joystick: None', 3)

        self.Jdesc_lbl          = [self.J1desc_lbl, self.J2desc_lbl, self.J3desc_lbl, self.J4desc_lbl, self.J5desc_lbl]
        self.Jvalue_lbl         = [self.J1value_lbl, self.J2value_lbl, self.J3value_lbl, self.J4value_lbl, self.J5value_lbl]

        for i, lbl in zip(range(0, len(self.Jvalue_lbl)), self.Jvalue_lbl):
            lbl.Name = str(i)

        self.Jmin_lbl           = [self.J1min_lbl, self.J2min_lbl, self.J3min_lbl, self.J4min_lbl, self.J5min_lbl]
        self.Jmax_lbl           = [self.J1max_lbl, self.J2max_lbl, self.J3max_lbl, self.J4max_lbl, self.J5max_lbl]
        self.Jdef_lbl           = [self.J1def_lbl, self.J2def_lbl, self.J3def_lbl, self.J4def_lbl, self.J5def_lbl]
        self.Jinitialized_lbl   = [self.J1initialized_lbl, self.J2initialized_lbl, self.J3initialized_lbl, self.J4initialized_lbl, self.J5initialized_lbl]
        self.Jboundaries_lbl    = [self.J1boundaries_lbl, self.J2boundaries_lbl, self.J3boundaries_lbl, self.J4boundaries_lbl, self.J5boundaries_lbl]
        self.Jfault_lbl         = [self.J1fault_lbl, self.J2fault_lbl, self.J3fault_lbl, self.J4fault_lbl, self.J5fault_lbl]
        self.Ctrl_lbl           = [self.ctrlIDLE_lbl, self.ctrlINIT_lbl, self.ctrlDONNING_lbl, self.ctrlRESTPOS_lbl, self.ctrlREADY_lbl, self.ctrlRUNNING_lbl, self.ctrlSTOP_lbl]
        self.button_list        = [self.disconnect_butt, self.init_butt, self.disableCtrl_butt, self.enableCtrl_butt, self.stop_butt, self.savePos_butt, self.gotoPos_butt]

        for lbl in self.Jvalue_lbl:
            lbl.Bind( wx.EVT_LEFT_DCLICK, self.open_jointDialog_command )

        for item in self.button_list:
            item.Disable()

        Publisher.subscribe(self.UpdateJointsInfo, "UpdateJointsInfo")
        Publisher.subscribe(self.ShowDonningDialog, "ShowDonningDialog")
        Publisher.subscribe(self.UpdateControlInfo, "UpdateControlInfo")
        Publisher.subscribe(self.UpdateInputInfo, "UpdateInputInfo")

        #self.UpdateControlInfo(None)

        '''
        "Redirect output to ctrl text "
        redir      = RedirectText(self.child.show_terminal)
        sys.stdout = redir
        '''

        " Create timer function - Update input values "
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.UpdateInputValues, self.timer)




    def update(self, event):
        print "updated: "
        print time.ctime()

    " ################### "
    " #### PUBLISHER #### "
    " ################### "
    def UpdateJointsInfo (self, msg):

        for i, Joint in zip(range(0,len(self.Bridge.Joints)), self.Bridge.Joints):
            if Joint.Homed:
                self.Jinitialized_lbl[i].SetLabel(u"●")
            else:
                self.Jinitialized_lbl[i].SetLabel(u"○")

            self.Jvalue_lbl[i].SetLabel(str(int(Joint.Position)))

    def ShowDonningDialog (self, msg):
        if self.Bridge.Status != DONNING:
            dialog = DialogError(self, "MEGA FAIL DONNING.")
            dialog.ShowModal()
            return

        dialog = DialogDonning(self)
        if dialog.ShowModal() == wx.ID_OK:
            self.Bridge.Status = REST_POSITION
            self.UpdateControlInfo(None)
        else:
            dialog = DialogError(self, "SYSTEM LOCKED.")
            dialog.ShowModal()
            return

    def UpdateControlInfo (self, msg):

        " Set status "
        for i, lbl in zip(range(0, len(self.Ctrl_lbl)), self.Ctrl_lbl):
            if self.Bridge.Status == i:

                if i != len(self.Ctrl_lbl):
                    lbl.SetBackgroundColour((57,232,149))
                else:
                    lbl.SetBackgroundColour((224,97,97))
            else:
                if i != len(self.Ctrl_lbl):
                    lbl.SetBackgroundColour((242,255,242))
                else:
                    lbl.SetBackgroundColour((255,232,232))

        " Force win refresh (background issue) "
        self.Refresh()


    def UpdateInputInfo (self, msg):

        self.inputDescription_lbl.SetLabel(str(self.Conf.Patient.Input))

        if not self.Bridge.Joystick.Mode:
            self.JoystickModeA_lbl.SetBackgroundColour((57,232,149))
            self.JoystickModeB_lbl.SetBackgroundColour((242,255,242))
        else:
            self.JoystickModeA_lbl.SetBackgroundColour((242,255,242))
            self.JoystickModeB_lbl.SetBackgroundColour((57,232,149))


        if self.Bridge.Joystick.SavePosition:
            self.JoystickSavePos_lbl.SetBackgroundColour((57,232,149))
        else:
            self.JoystickSavePos_lbl.SetBackgroundColour((242,255,242))

        if self.Bridge.Joystick.GotoSavedPosition:
            self.JoystickRecallPos_lbl.SetBackgroundColour((57,232,149))
        else:
            self.JoystickRecallPos_lbl.SetBackgroundColour((242,255,242))

        " Force win refresh (background issue) "
        self.Refresh()

    def UpdateInputValues (self, msg):
        self.P0_X_lbl.SetLabel("%.2f" % self.Coord.p0[0])
        self.P0_Y_lbl.SetLabel("%.2f" % self.Coord.p0[1])
        self.P0_Z_lbl.SetLabel("%.2f" % self.Coord.p0[2])
        self.P0_PS_lbl.SetLabel("%.2f" % self.Coord.p0[3])



    def animate(self, i):

        self.exo3d_plot.line.set_data([0, self.Coord.Elbow[0], self.Coord.EndEff_current[0]], [0, self.Coord.Elbow[1], self.Coord.EndEff_current[1]])
        self.exo3d_plot.line.set_3d_properties([0, self.Coord.Elbow[2], self.Coord.EndEff_current[2]])
        self.exo3d_plot.line2.set_data(self.Coord.EndEff_des[0], self.Coord.EndEff_des[1])
        self.exo3d_plot.line2.set_3d_properties(self.Coord.EndEff_des[2])

        # self.joystick_plot.line.set_data([0, p_elbow[0,i], EndEff0[0,i]], [0, p_elbow[1,i], EndEff0[1,i]])
        # for j, self.joystick_plot.line in enumerate(lines):
        #offset = [120, 120]

        '''
        offset = [self.Conf.w_plot_joy/2, self.Conf.h_plot_joy/2]
        self.joystick_plot.line.set_data([offset[0]+offset[0]*self.Coord.p0[1], offset[0]+offset[0]*self.Coord.p0[1]], [offset[1]+offset[1]*self.Coord.p0[0], offset[1]+offset[1]*self.Coord.p0[0]])
        
        if abs(self.Coord.p0[1]) > 0.4 and abs(self.Coord.p0[0]) > 0.4:
            self.joystick_plot.line.set_data([offset[0]+offset[0]*self.Coord.p0[0]*0.7, offset[0]+offset[0]*self.Coord.p0[0]*0.7], [offset[1]-offset[1]*self.Coord.p0[1]*0.7, offset[1]-offset[1]*self.Coord.p0[1]*0.7])
        else:
            self.joystick_plot.line.set_data([offset[0]+offset[0]*self.Coord.p0[0], offset[0]+offset[0]*self.Coord.p0[0]], [offset[1]-offset[1]*self.Coord.p0[1], offset[1]-offset[1]*self.Coord.p0[1]])

        if self.Coord.p0[2] >= 0.4:
            self.joystick_plot.line.set_markerfacecolor([1, 0, abs(self.Coord.p0[2])])
        elif self.Coord.p0[2] <= -0.4:
            self.joystick_plot.line.set_markerfacecolor([0, abs(self.Coord.p0[2]), 0])
        else:
            self.joystick_plot.line.set_markerfacecolor('black')
        
        #marker_style = dict(linestyle='-', color='red', markersize=15)
        #lines = [plt.plot([], [], marker='o', **marker_style)[0] for _ in range(N)]
        
    
        self.joystick_plot.figure.canvas.draw()
        
        for jj in range(0,self.monitorJoint_grid.GetNumberRows()):
            self.monitorJoint_grid.SetCellValue(jj, 1, str("{0:.3f}".format(round(self.Coord.Jpos[jj],3))))
            self.monitorCtrl_grid.SetCellValue(jj, 1, str("{0:.3f}".format(round(self.Coord.Jv[jj],3))))
            self.monitorJoint_grid.SetCellValue(jj, 5, str("{0:.3f}".format(round(self.Coord.SavedPos[jj],3))))
        '''

    def BridgeInitialization(self):

        print 'BridgeInitialization called.'

        " Joints Init "
        for i in range(0, self.Bridge.JointsNum):
            self.Bridge.Joints[i]   = Joint(i+1,
                                            self.Conf.Serial.COM[i],
                                            self.Conf.Exo,
                                            self.Conf.Exo,
                                            self.Coord)

        " Copy patient to Bridge "
        self.Bridge.Patient         = self.Conf.Patient
        self.Bridge.Control.Input   = self.Bridge.Patient.Input

        " Define Threads "

        self.Bridge.ControlThread = Thread_ControlClass("ControlThread", self.Bridge, self.Coord, self.Conf)
        self.Bridge.InputThread   = Thread_InputClass("InputThread", self.Bridge, self.Coord)

        for i, J in zip(range(0,self.Bridge.JointsNum), self.Bridge.Joints):
            " Define joint init threads "
            self.Bridge.JointInitThreads[i]     = Thread_JointInitClass("JointInitThread" + str(i), J)

            " Define joint update threads "
            self.Bridge.JointUpdateThreads[i]   = Thread_JointUpdateClass("JointUpdateThread" + str(i), J, self.Coord, self.Bridge)

        return True


    " ################## "
    " ####   MENU   #### "
    " ################## "

    def exo_setup_command (self, event):
        dialog = DialogExoSetup(self, self.Conf, self.Bridge)

        if dialog.ShowModal() == wx.ID_OK:
            self.Conf.Serial.Error = False

    def patient_setup_command (self, event):
        dialog = DialogPatientSetup(self, self.Conf, self.Bridge)

        if dialog.ShowModal() == wx.ID_OK:
            " Update joint values "
            for i, Jmin, Jmax, Jdef in zip(range(0,5), self.Jmin_lbl, self.Jmax_lbl, self.Jdef_lbl):
                Jmin.SetLabel(str(self.Conf.Patient.Jmin[i]))
                Jmax.SetLabel(str(self.Conf.Patient.Jmax[i]))
                Jdef.SetLabel(str(self.Conf.Patient.Jdef[i]))

            if self.Conf.Serial.AllConnected:
	            " Update patient ROM values "
	            for i in range (0, self.Bridge.JointsNum):
    	        	self.Bridge.Joints[i].SetRange(self.Bridge.Patient.Jmin[i], self.Bridge.Patient.Jmax[i])

            " Update input description "
            self.inputDescription_lbl.SetLabel(str(self.Conf.Patient.Input))

            self.statusbar.SetStatusText('Patient: Loaded', 2)

    def joystick_calibration_command(self,event):

    	dialog= DialogJoyCalibration(self, self.Conf, self.Bridge)
    	dialog.ShowModal()



    " ################## "
    " #### COMMANDS #### "
    " ################## "
    def connect_command(self, event):

        " Verifico che le il file paziente sia stato caricato "
        if not self.Conf.Patient.Loaded:
            dialog = DialogError(self, "Patient not loaded.")
            dialog.ShowModal()
            return

        " Verifico che le porte seriali siano state correttamente impostate "
        if not __debug__:
            if self.Conf.Serial.Error:
                dialog = DialogError(self, "Serial COM error.\nCheck preferences dialog.")
                dialog.ShowModal()
                return
        else:
            self.Conf.Serial.Error = False



        " Init Joints and threads "
        if not self.BridgeInitialization():
            " If BridgeInitialization() fails, return with error dialog"
            dialog = DialogError(self, "Bridge initialization failed.")
            dialog.ShowModal()
            return

        " Joystick Inizialization"
        if self.Bridge.Control.Input == "Joystick":
            try:
                print 'Init Joystick'
                " Init pygame "
                pygame.init()

                " Count available joysticks "
                if pygame.joystick.get_count() == 0:
                    dialog = DialogError(self, "Joystick missing.")
                    dialog.ShowModal()
                    return

                " Init Joystick "
                pygame.joystick.init()
                pygame.joystick.Joystick(0)


            except:
                dialog = DialogError(self, "Error: Pygame init failed.")
                dialog.ShowModal()
                return

        if not __debug__:

            " Open Serial Ports "
            try:
                for i, J in zip(range(0, len(self.Bridge.Joints)), self.Bridge.Joints):
                    if J.OpenPort():
                        print '+ %s Connected' % J.CommPort
                        self.Conf.Serial.Connected[i] = True
                    else:
                        print '- Error: couldn\'t open %s.' % J.CommPort
                        return
            except:
                dialog = DialogError(self, "Error: COM init failed.")
                dialog.ShowModal()
                return

            " Check if all COM are Connected "

            if all(i == True for i in self.Conf.Serial.Connected[0:self.Bridge.JointsNum]):
                self.Conf.Serial.AllConnected = True
                print "True All Connected"
            else:
                self.Conf.Serial.AllConnected = False
                print "False All Connected"
        else:
            self.Conf.Serial.AllConnected = True

        if self.Conf.Serial.AllConnected == True:
            print 'ok'
            " Get active threads "
            threads_list = threading.enumerate()
            controlThread_running = False
            inputThread_running = False

            for i in range(0, len(threads_list)):
                th = threads_list[i]
                if th.name == "ControlThread":
                    print '# Warning: ControlThread already running.'
                    controlThread_running = True

                if th.name == "InputThread":
                    print '# Warning: InputThread already running.'
                    inputThread_running = True

            " Run InputThread "
            if not inputThread_running:
                self.Bridge.InputThread.start()

            if not controlThread_running:
                self.Bridge.ControlThread.start()

            self.timer.Start(self.Conf.InputValuesRefreshTmr)


            " Disable connect button "
            self.connect_butt.Disable()

            " Enable init system button "
            self.init_butt.Enable()
            self.disconnect_butt.Enable()

            self.UpdateControlInfo(None)
            self.UpdateInputInfo(None)

            " Update statubar "
            self.statusbar.SetStatusText('Connected', 0)


        else:

            " Update statubar "
            self.statusbar.SetStatusText('Connection error', 0)

            if not __debug__:
                try:
                    " Close serial ports previously open "
                    for i, J in zip(range(0,self.Bridge.JointsNum), self.Bridge.Joints):
                        if self.Conf.Serial.Connected[i]:
                            J.ClosePort()
                            print '+ %s Disconnected' % J.CommPort
                            self.Conf.Serial.Connected[i] = False
                        else:
                            print '- Error: couldn\'t close %s.' % J.CommPort
                except Exception, e:
                    print 'Error  ' + str(e)





    def disconnect_command (self, event):

        if not __debug__:
            try:
                " Close Serial ports "
                for i, J in zip(range(0,self.Bridge.JointsNum), self.Bridge.Joints):
                    if self.Conf.Serial.Connected[i]:
                        J.ClosePort()
                        print '+ %s Closed' % J.CommPort
                        self.Conf.Serial.Connected[i] = False
                    else:
                        print '- Error: couldn\'t close %s.' % J.CommPort
            except Exception, e:
                print str(e)

        " Get active threads "
        threads_list = threading.enumerate()

        " Kill all the threads except MainThread "
        try:
            for i in range(0, len(threads_list)):
                th = threads_list[i]
                if th.name != "MainThread":
                    th.terminate()
        except Exception, e:
            print str(e)


        " Wait for the threads to end "
        for i in range(0, len(threads_list)):
            th = threads_list[i]
            if th.name != "MainThread":
                th.join()

        " Disable all buttons "

        for item in self.button_list:
            item.Disable()

        " Enable connect button "
        self.connect_butt.Enable()

        " Update statubar "
        self.statusbar.SetStatusText('Disconnected', 0)

        self.timer.Stop()


    def initialize_system_command (self, event):

        print '+ initialize_system_command() called.'

        try:
            " Get active threads "
            threads_list            = threading.enumerate()
            controlThread_running   = False

            for i in range(0,len(threads_list)):
                th = threads_list[i]
                if th.name == "ControlThread":
                    print '# Warning: ControlThread already running.'
                    controlThread_running = True

            " Update control status "
            if not __debug__:
                self.Bridge.Status = INIT_SYSTEM
            else:
                self.Bridge.Status = IDLE

            self.UpdateControlInfo(None)

            " Enable all buttons "
            for item in self.button_list:
                item.Enable()

            if not controlThread_running:
                self.Bridge.ControlThread.start()

        except Exception, e:
            dialog = DialogError(self, "System init failed.")
            dialog.ShowModal()
            print str(e)
            return


    def enableCtrl_command (self, event):

        " Run JointUpdateThreads "

        " Get active threads "
        threads_list            = threading.enumerate()
        print threads_list

        " Set control status "
        self.Bridge.Control.Status = POS_CTRL

        # TODO: SPOSTARE IN INIT-CONTROL
        if not __debug__:

            if all(i == 0 for i in self.Bridge.Patient.ROM_Defined):
                " Verifica ROM giunti paziente & Run update threads "
                for i in range(0,self.Bridge.JointsNum):

                    #ALE: se usassimo set range?

                    self.Bridge.Joints[i].Jmin = self.Bridge.Patient.Jmin[i]
                    self.Bridge.Joints[i].Jmax = self.Bridge.Patient.Jmax[i]

                    if not "JointUpdateThread"+str(i) in threads_list:
                        print 'JointUpdateThread: ', i
                        self.Bridge.JointUpdateThreads[i].start()
            else:

                dialog= DialogError(self, 'Please, calibrate the ROM first')
                dialog.ShowModal()
                return
        '''
        " TODO: da rendere pitonico (ciclo for) "
        if not "JointUpdateThread0" in threads_list:
            self.Bridge.JointUpdateThreads[0].start()

        if not "JointUpdateThread1" in threads_list:
            self.Bridge.JointUpdateThreads[1].start()
        '''
        ''' MARTA da ripristinare per Giunto 3
        if not "JointUpdateThread2" in threads_list:
            self.Bridge.JointUpdateThreads[2].start()
        '''
        '''
        if not "JointUpdateThread3" in threads_list:
            self.Bridge.JointUpdateThreads[3].start()
        '''

        ''' MARTA da ripristinare
        if not "JointUpdateThread4" in threads_list:
            self.Bridge.JointUpdateThreads[4].start()
        '''

        " Enable Control Flag "
        self.Bridge.Status = RUNNING
        self.Bridge.Control.FIRST_RUN = True
        self.UpdateControlInfo(None)

        self.Coord.FirstStart = [True, True, True, True, True]


    def disableCtrl_command (self, events):
        " Kill all the threads except MainThread and ControlThread"

        threads_list= threading.enumerate()
        try:
            for i in range(0, len(threads_list)):
                th = threads_list[i]
                if th.name != "MainThread" and th.name != "ControlThread":
                    th.terminate()
        except Exception, e:
            print str(e)

        " Wait for the threads to end "
        for i in range(1,len(threads_list)):
            th = threads_list[i]
            if th.name != "MainThread" and th.name != "ControlThread":
                th.join()

        " Disable Control Flag "
        self.Bridge.Status = READY
        self.Bridge.Control.Status = IDLE
        self.UpdateControlInfo(None)

        # TODO: CHECK FIRST START
        self.Coord.FirstStart = [True, True, True, True, True]

    def stop_command (self, event):

        if self.Bridge.Patient.Input== 'Joystick':
            if self.Bridge.Joystick.Mode == 0:
                self.Bridge.Joystick.Mode = 1
            else:
                self.Bridge.Joystick.Mode = 0

        elif self.Bridge.Patient.Input== 'Vocal':

            if self.Bridge.Control.Listen == 0:
                self.Bridge.Control.Listen = 1




        " Update input info in main window "
        wx.CallAfter(Publisher.sendMessage, "UpdateInputInfo", None)

    # TODO: verificare indentazione "
    def savePos_command (self):
        self.Coord.SavePos = [True, True, True, True, True, True]

    def gotoPos_command (self):
        self.Coord.GoToSavedPosMainTrigger = True


    def open_jointDialog_command (self, event):
        widget = event.GetEventObject()

        #if not self.Conf.Patient.Loaded:
        dialog = DialogJoint(self, int(widget.GetName()), self.Bridge.Joints[int(widget.GetName())], self.Bridge.Status)
        dialog.ShowModal()


# STDOUTPUT REDIRECT
class RedirectText(object):
    def __init__(self,aWxTextCtrl):
        self.out=aWxTextCtrl

    def write(self, string):
        wx.CallAfter(self.out.WriteText, string)


########
# MAIN #
########

print __debug__
# mandatory in wx, create an app, False stands for not deteriction stdin/stdout
app = wx.App(False)

# create an object
frame = MainWindow (None)
#terminal = ChildFrame(None)

# show the frame
frame.Show(True)
#terminal.Show(True)

# start the applications
app.MainLoop()