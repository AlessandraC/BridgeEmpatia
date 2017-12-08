
# -*- coding: utf-8 -*-
#!/usr/bin/env python


import os
import sys

import BRIDGE_GUI
import wx
from wx.lib.wordwrap import wordwrap
from wx.lib.pubsub  import setuparg1 #evita problemi con py2exe
from wx.lib.pubsub  import pub as Publisher

import unicodedata

from BridgeConf     import *
from BridgeJoint    import *
from BridgeInput    import *

from serial import *



# PORTE DISPONIBILI
def availableSerialPort():
    suffixes = "S", "USB", "ACM", "AMA"
    nameList = ["COM"] + ["/dev/tty%s" % suffix for suffix in suffixes]
    portList = []
    for name in nameList:
        for number in range(48):
            portName = "%s%s" % (name, number)
            try:
                Serial(portName).close()
                portList.append(portName)
            except IOError:
                pass
    return tuple(portList)


" Dialog exo setup "
class DialogExoSetup(BRIDGE_GUI.Dialog_ExoSetup):
    def __init__(self,parent,Conf, Bridge):
        BRIDGE_GUI.Dialog_ExoSetup.__init__(self,parent)

        self.Conf   = Conf
        self.Bridge = Bridge
        self.Error  = False


        self.Jmin_entry_list        = [self.J1min_entry, self.J2min_entry, self.J3min_entry, self.J4min_entry, self.J5min_entry]
        self.Jmax_entry_list        = [self.J1max_entry, self.J2max_entry, self.J3max_entry, self.J4max_entry, self.J5max_entry]
        self.Joffset_entry_list     = [self.J1offset_entry, self.J2offset_entry, self.J3offset_entry, self.J4offset_entry, self.J5offset_entry]
        self.Jratio_entry_list      = [self.J1ratio_entry, self.J2ratio_entry, self.J3ratio_entry, self.J4ratio_entry, self.J5ratio_entry]

        " Motor plot choice "
        self.choice_COM_list        = [self.choice_COM_M1, self.choice_COM_M2, self.choice_COM_M3, self.choice_COM_M4, self.choice_COM_M5]

        " Test button list "
        self.test_button_list       = [self.J1test_butt, self.J2test_butt, self.J3test_butt, self.J4test_butt, self.J5test_butt]

        for i, but in zip(range(0, len(self.test_button_list)), self.test_button_list):
            " Set widget name - Index number "
            but.Name = str(i)

        # Get available serial port
        self.portList = availableSerialPort()


        if len(self.portList) < 5:
            self.error_lbl.SetLabel("ERROR: not enough serial COM (%d found)" % len(self.portList))
            self.Error = True

        for i, choice in zip(range(0,6), self.choice_COM_list):

            for j in range(0,len(self.portList)):
                choice.Append(self.portList[j])

            # Try to set COM from conf
            try:
                choice.SetSelection(self.portList.index(self.Conf.Serial.COM[i]))
            except:
                choice.SetSelection(0)



        for i, Jmin, Jmax, Joffset, Jratio in zip(range(0,5), self.Jmin_entry_list, self.Jmax_entry_list, self.Joffset_entry_list, self.Jratio_entry_list):
            Jmin.SetValue(str(self.Conf.Exo.Jmin[i]))
            Jmax.SetValue(str(self.Conf.Exo.Jmax[i]))
            Joffset.SetValue(str(self.Conf.Exo.Joffset[i]))
            Jratio.SetValue(str(self.Conf.Exo.Jratio[i]))


    def ok_command(self,event):

        " get serial port only if no error condition occurs "
        if not self.Error:
            for isig, choice_COM in zip(range(0,5), self.choice_COM_list):
                self.Conf.Serial.COM[isig]      = self.portList[choice_COM.GetSelection()]

        for isig, Jmin, Jmax, Joffset, Jratio in zip(range(0,5), self.Jmin_entry_list, self.Jmax_entry_list, self.Joffset_entry_list, self.Jratio_entry_list):
            " Remove accents and get values "
            self.Conf.Exo.Jmin[isig]            = int(unicodedata.normalize('NFKD',Jmin.GetValue()).encode("ascii","ignore"))
            self.Conf.Exo.Jmax[isig]            = int(unicodedata.normalize('NFKD',Jmax.GetValue()).encode("ascii","ignore"))
            self.Conf.Exo.Joffset[isig]         = int(unicodedata.normalize('NFKD',Joffset.GetValue()).encode("ascii","ignore"))
            self.Conf.Exo.Jratio[isig]          = float(unicodedata.normalize('NFKD',Jratio.GetValue()).encode("ascii","ignore"))

        self.Conf.Exo.Loaded    = True

        self.Conf.WriteConfFile()

        self.EndModal(wx.ID_OK)
        self.Destroy()

    def cancel_command(self,event):
        self.Destroy()

    def test_command(self,event):
        " Get widget "
        widget = event.GetEventObject()

        " Get COM "
        serialcom = self.portList[self.choice_COM_list[int(widget.GetName())].GetSelection()]
        '''
        joint = Joint(   0,         # Num
                        serialcom,  # COM
                        5,          # Max
                        -5,         # Min
                        75,         # Ratio
                        0,          # Offset
                        0,          # Default
                        None)       # Coord
        '''
        PatientEs       = PatientClass()
        ExoEs           = ExoClass()

        joint = Joint(   0,         # Num
                        serialcom,  # COM
                        PatientEs,  # Ratio
                        ExoEs,      # offset
                        None)       # Coord

        " Open serial port "
        if not joint.OpenPort():
            dialog = DialogError(self, "Unable to open %s" % serialcom)
            dialog.ShowModal()
            return

        " Run test motor "
        ret = joint.MotorTest()

        " Close serial port "
        if not joint.ClosePort():
            dialog = DialogError(self, "Unable to close %s" % serialcom)
            dialog.ShowModal()
            return

        if ret:
            dialog = DialogError(self, "Test procedure done", "Bridge - Note")
            dialog.ShowModal()
        else:
            error = ''
            if joint.Timeout:
                error = ' | Timeout occurred'

            dialog = DialogError(self, "Test procedure failed %s" % error)
            dialog.ShowModal()


        joint = None

class DialogJoyCalibration(BRIDGE_GUI.Dialog_JoyCalibration):

    def __init__(self,parent, Conf, Bridge):

        BRIDGE_GUI.Dialog_JoyCalibration.__init__(self, parent)

        self.Conf = Conf
        self.Bridge = Bridge

        self.calib_buttlist= [self.calib_butt1,self.calib_butt2,self.calib_butt3,self.calib_butt4]

        for i, but in zip(range(0, len(self.calib_buttlist)), self.calib_buttlist):
            " Set widget name - Index number "
            but.Name = str(i)



    def calibrate_command (self,event):

        widget = event.GetEventObject()
        direction=int(widget.GetName())

        if self.Bridge.Patient.Input== 'Joystick':

            if direction==0:
                self.dialog= Dialog_Calibration(self, 'Please, push the joystick to the right as much as you can')
            elif direction==1:
                self.dialog= Dialog_Calibration(self, 'Please, push the joystick to the left as much as you can')
            elif direction==2:
                self.dialog= Dialog_Calibration(self, 'Please, push the joystick forward as much as you can')
            else:
                self.dialog= Dialog_Calibration(self, 'Please, push the joystick backward as much as you can')

            self.Bridge.CalibrationThread = Thread_JoyCalibClass ("CalibrationThread",self.Bridge, self.Conf, direction)
            self.Bridge.CalibrationThread.start()
            self.timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.end_calibration, self.timer)
            self.timer.Start(self.Conf.CalibrationTmr)
            self.dialog.ShowModal()
        else: 

            dialog= DialogError (self, 'Please, select the joystick as control modality')
            dialog.ShowModal()

    def end_calibration(self,msg):

        self.Bridge.CalibrationThread.terminate()
        self.dialog.Destroy()
        self.timer.Stop()

" Dialog patient setup "
class DialogPatientSetup(BRIDGE_GUI.Dialog_PatientSetup):
    def __init__(self,parent, Conf, Bridge):
        BRIDGE_GUI.Dialog_PatientSetup.__init__(self, parent)

        self.Conf                   = Conf
        self.Bridge                 = Bridge
        self.Filename               = self.Conf.Patient.Filename
        self.J1min_entry.Name       = 'AA'
        self.Jmin_entry_list        = [self.J1min_entry, self.J2min_entry, self.J3min_entry, self.J4min_entry, self.J5min_entry]
        self.Jmax_entry_list        = [self.J1max_entry, self.J2max_entry, self.J3max_entry, self.J4max_entry, self.J5max_entry]
        self.Jdef_entry_list        = [self.J1def_entry, self.J2def_entry, self.J3def_entry, self.J4def_entry, self.J5def_entry]
        self.Jrest_entry_list       = [self.J1rest_entry, self.J2rest_entry, self.J3rest_entry, self.J4rest_entry, self.J5rest_entry]

        self.l_entry_list           = [self.l1_lbl, self.l2_lbl, self.l3_lbl]

        self.inputList              = ["Joystick", "Visual", "Vocal"]

        if self.Conf.Patient.Loaded:

            self.patientName_entry.SetValue(self.Conf.Patient.Name)

            for i, Jmin, Jmax, Jdef, Jrest in zip(range(0,5), self.Jmin_entry_list, self.Jmax_entry_list, self.Jdef_entry_list, self.Jrest_entry_list):
                Jmin.SetValue(str(self.Conf.Patient.Jmin[i]))
                Jmax.SetValue(str(self.Conf.Patient.Jmax[i]))
                Jdef.SetValue(str(self.Conf.Patient.Jdef[i]))
                Jrest.SetValue(str(self.Conf.Patient.Jrest[i]))

            self.l1_lbl.SetValue(str(self.Conf.Patient.l1))
            self.l2_lbl.SetValue(str(self.Conf.Patient.l2))
            self.l3_lbl.SetValue(str(self.Conf.Patient.l3))

            self.ft_lbl.SetValue(str(self.Conf.Patient.FixationTime))

            try:
                self.input_choice.SetSelection(self.inputList.index(self.Conf.Patient.Input))
            except:
                self.input_choice.SetSelection(0)

        else:
            for Jmin, Jmax, Jdef, Jrest in zip(self.Jmin_entry_list, self.Jmax_entry_list, self.Jdef_entry_list, self.Jrest_entry_list):
                Jmin.SetValue('0')
                Jmax.SetValue('0')
                Jdef.SetValue('0')
                Jrest.SetValue('0')

            for l in self.l_entry_list:
                l.SetValue('0')

            self.ft_lbl.SetValue('0')


            self.input_choice.SetSelection(0)

    def define_command(self,event):


        if self.Bridge.Status== READY:
            widget = event.GetEventObject()
            joint_number=int(widget.GetName())
            dialog= Dialog_ROM(self,joint_number,self.Conf,self.Bridge)
            dialog.ShowModal()

            if self.Bridge.SaveJoint:
                for i, Jmin, Jmax, Jdef, Jrest in zip(range(0,5), self.Jmin_entry_list, self.Jmax_entry_list, self.Jdef_entry_list, self.Jrest_entry_list):
                    Jmin.SetValue(str(self.Bridge.Patient.Jmin[i]))
                    Jmax.SetValue(str(self.Bridge.Patient.Jmax[i]))
        elif self.Bridge.Status == RUNNING:

            dialog= DialogError(self, 'Attention: procedure not available. Please, disable control first')
            dialog.ShowModal()
        else:
            dialog= DialogError(self, 'Please, do the initialization first')
            dialog.ShowModal()

    def ok_command(self,event):
        
        for isig, Jmin, Jmax, Jdef, Jrest in zip(range(0,5), self.Jmin_entry_list, self.Jmax_entry_list, self.Jdef_entry_list, self.Jrest_entry_list):
            " Remove accents and get values "
            self.Conf.Patient.Jmin[isig]            = int(unicodedata.normalize('NFKD',Jmin.GetValue()).encode("ascii","ignore"))
            self.Conf.Patient.Jmax[isig]            = int(unicodedata.normalize('NFKD',Jmax.GetValue()).encode("ascii","ignore"))
            self.Conf.Patient.Jdef[isig]            = int(unicodedata.normalize('NFKD',Jdef.GetValue()).encode("ascii","ignore"))
            self.Conf.Patient.Jrest[isig]           = int(unicodedata.normalize('NFKD',Jrest.GetValue()).encode("ascii","ignore"))

        self.Conf.Patient.l1            =  float(unicodedata.normalize('NFKD',self.l1_lbl.GetValue()).encode("ascii","ignore"))
        self.Conf.Patient.l2            =  float(unicodedata.normalize('NFKD',self.l2_lbl.GetValue()).encode("ascii","ignore"))
        self.Conf.Patient.l3            =  float(unicodedata.normalize('NFKD',self.l3_lbl.GetValue()).encode("ascii","ignore"))

        self.Conf.Patient.FixationTime  =  float(unicodedata.normalize('NFKD',self.ft_lbl.GetValue()).encode("ascii","ignore"))

        " Save patient name "
        self.Conf.Patient.Name      = unicodedata.normalize('NFKD',self.patientName_entry.GetValue()).encode("ascii","ignore")

        " Save patient input "
        self.Conf.Patient.Input     = self.inputList[self.input_choice.GetSelection()]

        self.Conf.Patient.Loaded    = True

        self.Bridge.Patient.Filename= self.Filename

        self.Conf.SavePatient(self.Bridge.Patient.Filename, self.Conf.Patient)

        self.EndModal(wx.ID_OK)
        self.Destroy()


    def save_command (self,event):
        path    = os.path.dirname(os.path.realpath(sys.argv[0]))
        dlg     = wx.FileDialog(self, "Choose a File:", wildcard="INI files (*.ini)|*.ini", defaultDir=path, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        
        if dlg.ShowModal() == wx.ID_OK:
            " Get filename "
            self.Filename = dlg.GetPath()

            " Create local patient "
            Patient = PatientClass()

            " Get values from entries "
            for isig, Jmin, Jmax, Jdef, Jrest in zip(range(0,5), self.Jmin_entry_list, self.Jmax_entry_list, self.Jdef_entry_list, self.Jrest_entry_list):
                " Remove accents and get values "
                Patient.Jmin[isig]      = int(unicodedata.normalize('NFKD',Jmin.GetValue()).encode("ascii","ignore"))
                Patient.Jmax[isig]      = int(unicodedata.normalize('NFKD',Jmax.GetValue()).encode("ascii","ignore"))
                Patient.Jdef[isig]      = int(unicodedata.normalize('NFKD',Jdef.GetValue()).encode("ascii","ignore"))
                Patient.Jrest[isig]     = int(unicodedata.normalize('NFKD',Jrest.GetValue()).encode("ascii","ignore"))

            Patient.l1                  =  float(unicodedata.normalize('NFKD',self.l1_lbl.GetValue()).encode("ascii","ignore"))
            Patient.l2                  =  float(unicodedata.normalize('NFKD',self.l2_lbl.GetValue()).encode("ascii","ignore"))
            Patient.l3                  =  float(unicodedata.normalize('NFKD',self.l3_lbl.GetValue()).encode("ascii","ignore"))

            Patient.FixationTime        =  float(unicodedata.normalize('NFKD',self.ft_lbl.GetValue()).encode("ascii","ignore"))

            " get patient name "
            Patient.Name                = unicodedata.normalize('NFKD',self.patientName_entry.GetValue()).encode("ascii","ignore")


            " Save patient input "
            Patient.Input               = self.inputList[self.input_choice.GetSelection()]
            print Patient.Input


            " Save nre patient file"
            self.Bridge.Patient.Filename= self.Filename
            self.Conf.SavePatient (self.Bridge.Patient.Filename, Patient)
            self.Conf.SavePath(self.Filename)


    def cancel_command (self,event):
        self.Destroy()


    def load_command (self,event):

        path = os.path.dirname(os.path.realpath(sys.argv[0]))
        # otherwise ask the user what new file to open
        dlg = wx.FileDialog(self, "Choose a File:", wildcard="INI files (*.ini)|*.ini", defaultDir=path, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if dlg.ShowModal() == wx.ID_OK:
            " Get selected file "
            self.Filename = dlg.GetPath()
            self.Conf.SavePath(self.Filename)

            try:
                Patient = PatientClass()
                Patient = self.Conf.ParsePatientFile(self.Filename)

                self.patientName_entry.SetValue(Patient.Name)

                for i, Jmin, Jmax, Jdef, Jrest in zip(range(0,5), self.Jmin_entry_list, self.Jmax_entry_list, self.Jdef_entry_list, self.Jrest_entry_list):
                    Jmin.SetValue(str(Patient.Jmin[i]))
                    Jmax.SetValue(str(Patient.Jmax[i]))
                    Jdef.SetValue(str(Patient.Jdef[i]))
                    Jrest.SetValue(str(Patient.Jrest[i]))
                
                self.l1_lbl.SetValue(str(Patient.l1))
                self.l2_lbl.SetValue(str(Patient.l2))
                self.l3_lbl.SetValue(str(Patient.l3))

                self.ft_lbl.SetValue(str(Patient.FixationTime))
                self.input_choice.SetSelection(self.inputList.index(Patient.Input))

                self.ft_lbl.SetValue(str(Patient.FixationTime))


            except Exception, e:
                print 'Error ' + str(e)
                self.Filename = None
                pass


    def onText_command (self, event):
        " Check values "
        '''
        print 'la'
        widget = event.GetEventObject()
        print widget.GetName()
        '''
        pass

" ############ "
" Dialog Error "
" ############ "
class DialogError(BRIDGE_GUI.Dialog_Error):
    def __init__(self, parent, error, title=None):
        BRIDGE_GUI.Dialog_Error.__init__(self,parent)
        if title != None:
            self.SetTitle(title)

        self.error_lbl.SetLabel(error)


    def cancel_command(self,event):
        self.Destroy()


" ############ "
" Dialog Joint "
" ############ "
class DialogJoint (BRIDGE_GUI.Dialog_Joint):
    def __init__(self, parent, Num, Joint, Status):
        BRIDGE_GUI.Dialog_Joint.__init__(self,parent)

        self.Joint  = Joint
        self.Status = Status

        self.Joint.Position = self.Joint.GetPositionDeg()
        wx.CallAfter(Publisher.sendMessage, "UpdateJointsInfo", None)

        if self.Joint:
            # self.angle_entry.SetValue(str(self.Joint.Position))
            self.angle_entry.SetValue(str(int(self.Joint.Position)))
        else:
            self.angle_entry.SetValue('0')

        self.joint_lbl.SetLabel('J'+str(Num+1))

    def plus_command (self,event):
        self.angle = int(self.angle_entry.GetValue()) + 1

        self.angle_entry.SetValue(str(self.angle))

    def minus_command (self,event):
        self.angle = int(self.angle_entry.GetValue()) - 1

        self.angle_entry.SetValue(str(self.angle))

    def go_command (self,event):
        if not self.Joint:
            self.error_lbl.SetLabel('Joint not initialized')
        elif self.Status != READY:
            self.error_lbl.SetLabel('System status error')
        else:
            self.Joint.SetPositionMode()
            self.Joint.SetPositionDeg(self.angle)


            while abs(self.Joint.GetPositionDeg() - self.angle) > 0.5:
                print '**** I am going to the requested position, J%d - %d' % (self.Joint.Num, self.Joint.GetPositionDeg())
                time.sleep(1)

            self.Joint.Position = self.Joint.GetPositionDeg()
            wx.CallAfter(Publisher.sendMessage, "UpdateJointsInfo", None)


    def cancel_command (self,event):
        self.Destroy()


" ############## "
" Dialog Donning "
" ############## "
class DialogDonning (BRIDGE_GUI.Dialog_Donning):
    def __init__(self, parent):
        BRIDGE_GUI.Dialog_Donning.__init__(self,parent)

    def ok_command (self,event):
        self.EndModal(wx.ID_OK)
        self.Destroy()

" ################## "
" Dialog Calibration "
" ################## "
class Dialog_ROM(BRIDGE_GUI.Dialog_ROM_def):

    def __init__(self, parent,joint_number,Conf,Bridge):

        BRIDGE_GUI.Dialog_ROM_def.__init__(self,parent)


        self.joint_number= joint_number
        self.Bridge= Bridge
        self.Conf  = Conf
        if self.joint_number<5:
            string= str('         J'+str(self.joint_number+1)+'min')
            #self.joint= self.Bridge.Joints[self.joint_number]
        else:
            string= str('         J'+str(self.joint_number-4)+'max')
            #self.joint= self.Bridge.Joints[self.joint_number-5]

        self.j_label.SetLabel(string)
        #"Leggo la posizione del giunto e la scrivo nel dialog"
        #joint_angle=self.joint.GetPositionDeg()
        #self.joint_label.SetLabel(str(joint_angle))


    def go_command(self,event):


        if self.joint_number<5:
            ret = self.joint.joint_decrease(self.Bridge.StepNumber[self.joint_number])

            if not ret:
                error = ''
                if joint.Timeout:
                    error = ' | Timeout occurred'

                dialog = DialogError(self, "Procedure failed %s" % error)
                dialog.ShowModal()
            else:

                joint_angle= self.joint.GetPositionDeg()

                self.joint_label.SetLabel(str(joint_angle))

            self.joint = None

        else:

            ret = joint.joint_increment()
            if not ret:
                error = ''
                if joint.Timeout:
                    error = ' | Timeout occurred'

                dialog = DialogError(self, "Procedure failed %s" % error)
                dialog.ShowModal()
            else:

                joint_angle = self.joint.GetPositionDeg()
                self.joint_label.SetLabel(str(joint_angle))


            self.joint = None

        self.Bridge.StepNumber[self.joint_number]+=1

    def save_command(self,event):

        self.Bridge.SaveJoint= True

        # if self.joint_number< 5:

        #      self.Conf.Patient.Jmin[self.joint_number]= int(unicodedata.normalize('NFKD',self.joint_label.GetValue()).encode("ascii","ignore"))
        # else:

        #      self.Conf.Patient.Jmax[self.joint_number-5]= int(unicodedata.normalize('NFKD',self.joint_label.GetValue()).encode("ascii","ignore"))


        self.Conf.Patient.ROM_Defined[self.joint_number] = True
        self.Bridge.StepNumber[self.joint_number]= 1
        self.Bridge.Patient= self.Conf.Patient
        self.Destroy()

class Dialog_Calibration(BRIDGE_GUI.Dialog_Calibration):

    def __init__(self, parent, message):
        BRIDGE_GUI.Dialog_Calibration.__init__(self,parent)

        self.Calib_label.SetLabel(message)

