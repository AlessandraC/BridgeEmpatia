# -*- coding: utf-8 -*-
import ConfigParser
import math
import numpy
import os, sys


IDLE                = 0
INIT_SYSTEM         = 1
DONNING             = 2
REST_POSITION       = 3
READY               = 4
RUNNING             = 5
ERROR               = 6
SPEED_CTRL          = 7
POS_CTRL            = 8


class BridgeClass:
    def __init__(self):
        self.JointsNum              = 4
        self.Joints                 = [None] * self.JointsNum
        self.JointInitThreads       = [None] * self.JointsNum
        self.JointUpdateThreads     = [None] * self.JointsNum
        self.ControlThread          = None
        self.InputThread            = None
        self.Control                = ControlClass()
        self.Patient                = PatientClass()
        self.Joystick               = JoystickClass()
        self.Status                 = IDLE
        self.SaveJoint              = False
        self.StepNumber             = [1]*10

class ControlClass:
    def __init__(self):

        self.Status                 = IDLE
        self.InputList              = ["Joystick", "Visual", "Vocal"]
        self.Input                  = ""
        self.Listen = 0
        self.FIRST_RUN = False

        # TODO: Tuning Parameters "
        self.ThreadPeriod           = 0.5
        self.Time                   = 0.5
        self.MaxDegDispl            = 5
        " Massimo spostamento 3D [m]"
        self.S                      = 0.02

        " Tolleranza sull'errore cartesiano nella cinematica inversa "
        self.Tollerance             = 5e-4
        self.Eps                    = 0.5
        " Peso per smorzare la velocita' di giunto vicino alle singolarita'/limiti WS - NB massimo valore 1 "
        self.Wq0s                   = 0.5

        " IK parameters "
        self.Dol                    = 5     # gradi di distanza da ROM
        self.Du                     = 1   # step to increase/decrease joint limit ramps
        self.Alpha                  = 1
        self.Alpha0                 = 1
        self.IterMax                = 2000
        self.Threshold              = 3     # deg di tolleranza

        # " Flag per limitare velocità "
        # self.BoundedJv              = [False, False, False, False, False]

        " ############# "
        " VOCAL CONTROL "
        " ############# "
        self.VocalMaxSteps          = 10

        ' Set in BridgeInputThread '
        self.VocalSteps             = self.VocalMaxSteps
        self.VocalStepsCnt          = 0

class BridgeCoordClass:
    def __init__(self):

        " User input [-1;+1]"
        self.p0                         = [0]*4

        " End effector coordinates (in space) - current "
        self.EndEff_current             = numpy.array([0.0, 0.0, 0.0, 0.0])

        " End effector coordinates (in space) - desired "
        self.EndEff_des                 = numpy.array([0.0, 0.0, 0.0, 0.0])

        " Usato per plot 3D, ma calcolato nel thread di controllo "
        self.Elbow                      = numpy.array([0.0, 0.0, 0.0])

        " Posizione attuale dei giunti "
        self.Jpos                       = [0]*5

        " Posizione desiderata dei giunti "
        self.Jdes                       = [0]*5

        " Velocita' desiderata dei giunti "
        self.Jv                         = [0]*5

        #self.SavedPos                   = [0]*5
        #self.SavePos                    = [False, False, False, False, False]
        #self.GoToSavedPos               = [False, False, False, False, False]
        #self.GoToSavedPosMainTrigger    = False
        #self.SavePosMainTrigger         = False

class JoystickClass:
    def __init__(self):
        " 0: Normale - 1: Advanced "
        self.Mode               = 0
        self.SavePosition       = 0
        self.GotoSavedPosition  = 0
        self.Alarm              = 0
        #TODO: INIT JOYSTICK
        self.Gain               = 1.5
        self.AxisOffset         = [-0.273468017578 , -0.257843017578]


class SerialClass:
    def __init__(self):
        self.COM            = [None] * 5
        self.Connected      = [False] * 5

        " Flag generale connessione porte seriali "
        self.AllConnected   = False

        " Errore dovuto a un numero non sufficiente di porte seriali o configurazione mancante/sbagliata "
        self.Error          = True


class PyGameConfClass:
    def __init__(self):

        self.size   = self.width, self.height = 320, 240
        self.color  = 0, 0, 0
        self.period = 0.05


class PatientClass:
    def __init__(self):
        self.Name           = ''
        self.Jmin           = [0]*5
        self.Jmax           = [0]*5
        self.Jrest          = [0]*5
        self.Jdef           = [0]*5
        self.l1             = None      # [m]
        self.l2             = None      # [m]
        self.l3             = None      # [m]
        self.FixationTime   = None      # [samples]
        self.RJoint3        = 0.07     # [m]
        self.Loaded         = False
        self.Filename       = ''
        self.Input          = ''
        self.axis_max       = [0]*4
        self.ROM_Defined    = [False]*10



class ExoClass:
    def __init__(self):
        self.Jmin           = [0]*5
        self.Jmax           = [0]*5
        self.Jratio         = [0]*5
        self.Joffset        = [0]*5
        self.Loaded         = False
        self.Filename       = ''


class BridgeConfClass:
    def __init__(self):
        self.version                = '1.0'
        self.exo_file               = 'Conf.ini'
        self.PyGameConf             = PyGameConfClass()
        self.Serial                 = SerialClass()
        self.Patient                = PatientClass()
        self.Exo                    = ExoClass()

        " Input values timer in milliseconds "
        self.InputValuesRefreshTmr  = 200

        " Calibration Timer in milliseconds"
        self.CalibrationTmr         = 5000


        self.FirstStart             = True

        
        # Parameters
        self.w_plot_joy             = 0
        self.h_plot_joy             = 0

        self.ReadConfFile()
        self.ReadPatientFile(self.Patient.Filename)

        '''
        print self.Exo.Jmin
        print self.Exo.Jmax
        print self.Exo.Jratio
        print self.Exo.Joffset
        '''

    def ReadConfFile (self):
        try:
            Config = ConfigParser.ConfigParser()
            Config.read(self.exo_file)
            section = Config.sections()

            self.Patient.Filename      = Config.get(section[0],"FileName")
            self.Serial.COM[0]         = Config.get(section[0],"COM_J1")
            self.Serial.COM[1]         = Config.get(section[0],"COM_J2")
            self.Serial.COM[2]         = Config.get(section[0],"COM_J3")
            self.Serial.COM[3]         = Config.get(section[0],"COM_J4")
            self.Serial.COM[4]         = Config.get(section[0],"COM_J5")

            self.Exo.Jmin[0]            = int(Config.get(section[0],"J1_min"))
            self.Exo.Jmin[1]            = int(Config.get(section[0],"J2_min"))
            self.Exo.Jmin[2]            = int(Config.get(section[0],"J3_min"))
            self.Exo.Jmin[3]            = int(Config.get(section[0],"J4_min"))
            self.Exo.Jmin[4]            = int(Config.get(section[0],"J5_min"))

            self.Exo.Jmax[0]            = int(Config.get(section[0],"J1_max"))
            self.Exo.Jmax[1]            = int(Config.get(section[0],"J2_max"))
            self.Exo.Jmax[2]            = int(Config.get(section[0],"J3_max"))
            self.Exo.Jmax[3]            = int(Config.get(section[0],"J4_max"))
            self.Exo.Jmax[4]            = int(Config.get(section[0],"J5_max"))

            self.Exo.Jratio[0]          = float(Config.get(section[0],"J1_ratio"))
            self.Exo.Jratio[1]          = float(Config.get(section[0],"J2_ratio"))
            self.Exo.Jratio[2]          = float(Config.get(section[0],"J3_ratio"))
            self.Exo.Jratio[3]          = float(Config.get(section[0],"J4_ratio"))
            self.Exo.Jratio[4]          = float(Config.get(section[0],"J5_ratio"))

            self.Exo.Joffset[0]         = int(Config.get(section[0],"J1_offset"))
            self.Exo.Joffset[1]         = int(Config.get(section[0],"J2_offset"))
            self.Exo.Joffset[2]         = int(Config.get(section[0],"J3_offset"))
            self.Exo.Joffset[3]         = int(Config.get(section[0],"J4_offset"))
            self.Exo.Joffset[4]         = int(Config.get(section[0],"J5_offset"))

        except Exception, e:
            print '# Error: ReadConfFile failed | ' + str(e)
            # Read conf failed -> create a new configuration file

    def ReadPatientFile(self, filename):
        try:
            Config = ConfigParser.ConfigParser()
            Config.read(filename)
            section = Config.sections()

            self.Patient.Name               = Config.get(section[0],"Name")
            self.Patient.Input              = Config.get(section[0],"Input")
            self.Patient.Jmin[0]            = int(Config.get(section[0],"J1_min"))
            self.Patient.Jmin[1]            = int(Config.get(section[0],"J2_min"))
            self.Patient.Jmin[2]            = int(Config.get(section[0],"J3_min"))
            self.Patient.Jmin[3]            = int(Config.get(section[0],"J4_min"))
            self.Patient.Jmin[4]            = int(Config.get(section[0],"J5_min"))

            self.Patient.Jmax[0]            = int(Config.get(section[0],"J1_max"))
            self.Patient.Jmax[1]            = int(Config.get(section[0],"J2_max"))
            self.Patient.Jmax[2]            = int(Config.get(section[0],"J3_max"))
            self.Patient.Jmax[3]            = int(Config.get(section[0],"J4_max"))
            self.Patient.Jmax[4]            = int(Config.get(section[0],"J5_max"))

            self.Patient.Jdef[0]            = int(Config.get(section[0],"J1_default"))
            self.Patient.Jdef[1]            = int(Config.get(section[0],"J2_default"))
            self.Patient.Jdef[2]            = int(Config.get(section[0],"J3_default"))
            self.Patient.Jdef[3]            = int(Config.get(section[0],"J4_default"))
            self.Patient.Jdef[4]            = int(Config.get(section[0],"J5_default"))

            self.Patient.Jrest[0]           = int(Config.get(section[0],"J1_rest"))
            self.Patient.Jrest[1]           = int(Config.get(section[0],"J2_rest"))
            self.Patient.Jrest[2]           = int(Config.get(section[0],"J3_rest"))
            self.Patient.Jrest[3]           = int(Config.get(section[0],"J4_rest"))
            self.Patient.Jrest[4]           = int(Config.get(section[0],"J5_rest"))

            self.Patient.l1                 = float(Config.get(section[0],"l1"))
            self.Patient.l2                 = float(Config.get(section[0],"l2"))
            self.Patient.l3                 = float(Config.get(section[0],"l3"))

            self.Patient.FixationTime       = float(Config.get(section[0],"fixation_time"))

            self.Patient.ROM_Defined[0]     = Config.get(section[0],"J1min Defined")
            self.Patient.ROM_Defined[1]     = Config.get(section[0],"J2min Defined")
            self.Patient.ROM_Defined[2]     = Config.get(section[0],"J3min Defined")
            self.Patient.ROM_Defined[3]     = Config.get(section[0],"J4min Defined")
            self.Patient.ROM_Defined[4]     = Config.get(section[0],"J5min Defined")
            self.Patient.ROM_Defined[5]     = Config.get(section[0],"J1max Defined")
            self.Patient.ROM_Defined[6]     = Config.get(section[0],"J2max Defined")
            self.Patient.ROM_Defined[7]     = Config.get(section[0],"J3max Defined")
            self.Patient.ROM_Defined[8]     = Config.get(section[0],"J4max Defined")
            self.Patient.ROM_Defined[9]     = Config.get(section[0],"J5max Defined")

            self.Patient.axis_max[0]        = float(Config.get(section[0],"Joy_destra"))
            self.Patient.axis_max[1]        = float(Config.get(section[0],"Joy_sinistra"))
            self.Patient.axis_max[2]        = float(Config.get(section[0],"Joy_avanti"))
            self.Patient.axis_max[3]        = float(Config.get(section[0],"Joy_indietro"))




            #self.Patient.Filename           = filename
            self.Patient.Loaded             = True

            return True

        except Exception, e:
            print '# Error: ReadPatientFile failed | ' + str(e)
            # Read conf failed -> create a new configuration file
            return False

    def SavePath(self, filename):

        Config = ConfigParser.ConfigParser()
        Config.optionxform = str
        Config.read(self.exo_file)
        section = Config.sections()
        Config.set(section[0], 'FileName', filename)
        cfgfile = open(self.exo_file,'w')
        Config.write(cfgfile)
        cfgfile.close()

    def ParsePatientFile (self, filename):

        try:

            Patient     = PatientClass()
            Config      = ConfigParser.ConfigParser()
            Config.read(filename)
            section     = Config.sections()

            Patient.Name               = Config.get(section[0],"Name")
            Patient.Input              = Config.get(section[0],"Input")
            Patient.Jmin[0]            = int(Config.get(section[0],"J1_min"))
            Patient.Jmin[1]            = int(Config.get(section[0],"J2_min"))
            Patient.Jmin[2]            = int(Config.get(section[0],"J3_min"))
            Patient.Jmin[3]            = int(Config.get(section[0],"J4_min"))
            Patient.Jmin[4]            = int(Config.get(section[0],"J5_min"))

            Patient.Jmax[0]            = int(Config.get(section[0],"J1_max"))
            Patient.Jmax[1]            = int(Config.get(section[0],"J2_max"))
            Patient.Jmax[2]            = int(Config.get(section[0],"J3_max"))
            Patient.Jmax[3]            = int(Config.get(section[0],"J4_max"))
            Patient.Jmax[4]            = int(Config.get(section[0],"J5_max"))

            Patient.Jdef[0]            = int(Config.get(section[0],"J1_default"))
            Patient.Jdef[1]            = int(Config.get(section[0],"J2_default"))
            Patient.Jdef[2]            = int(Config.get(section[0],"J3_default"))
            Patient.Jdef[3]            = int(Config.get(section[0],"J4_default"))
            Patient.Jdef[4]            = int(Config.get(section[0],"J5_default"))

            Patient.Jrest[0]           = int(Config.get(section[0],"J1_rest"))
            Patient.Jrest[1]           = int(Config.get(section[0],"J2_rest"))
            Patient.Jrest[2]           = int(Config.get(section[0],"J3_rest"))
            Patient.Jrest[3]           = int(Config.get(section[0],"J4_rest"))
            Patient.Jrest[4]           = int(Config.get(section[0],"J5_rest"))

            Patient.l1                 = float(Config.get(section[0],"l1"))
            Patient.l2                 = float(Config.get(section[0],"l2"))
            Patient.l3                 = float(Config.get(section[0],"l3"))

            Patient.FixationTime       = float(Config.get(section[0],"fixation_time"))
            Patient.ROM_Defined[0]     = Config.get(section[0],"J1min Defined")
            Patient.ROM_Defined[1]     = Config.get(section[0],"J2min Defined")
            Patient.ROM_Defined[2]     = Config.get(section[0],"J3min Defined")
            Patient.ROM_Defined[3]     = Config.get(section[0],"J4min Defined")
            Patient.ROM_Defined[4]     = Config.get(section[0],"J5min Defined")
            Patient.ROM_Defined[5]     = Config.get(section[0],"J1max Defined")
            Patient.ROM_Defined[6]     = Config.get(section[0],"J2max Defined")
            Patient.ROM_Defined[7]     = Config.get(section[0],"J3max Defined")
            Patient.ROM_Defined[8]     = Config.get(section[0],"J4max Defined")
            Patient.ROM_Defined[9]     = Config.get(section[0],"J5max Defined")
            Patient.axis_max[0]        = float(Config.get(section[0],"Joy_destra"))
            Patient.axis_max[1]        = float(Config.get(section[0],"Joy_sinistra"))
            Patient.axis_max[2]        = float(Config.get(section[0],"Joy_avanti"))
            Patient.axis_max[3]        = float(Config.get(section[0],"Joy_indietro"))


            return Patient

        except Exception, e:
            print '# Error: ReadPatientFile failed | ' + str(e)
            # Read conf failed -> create a new configuration file
            return False


    def ParseExoFile (self, filename):
        try:
            Exo         = ExoClass()
            Config      = ConfigParser.ConfigParser()
            Config.read(filename)
            section     = Config.sections()

            Exo.Jmin[0]            = int(Config.get(section[0],"J1_min"))
            Exo.Jmin[1]            = int(Config.get(section[0],"J2_min"))
            Exo.Jmin[2]            = int(Config.get(section[0],"J3_min"))
            Exo.Jmin[3]            = int(Config.get(section[0],"J4_min"))
            Exo.Jmin[4]            = int(Config.get(section[0],"J5_min"))

            Exo.Jmax[0]            = int(Config.get(section[0],"J1_max"))
            Exo.Jmax[1]            = int(Config.get(section[0],"J2_max"))
            Exo.Jmax[2]            = int(Config.get(section[0],"J3_max"))
            Exo.Jmax[3]            = int(Config.get(section[0],"J4_max"))
            Exo.Jmax[4]            = int(Config.get(section[0],"J5_max"))

            Exo.Jratio[0]          = float(Config.get(section[0],"J1_ratio"))
            Exo.Jratio[1]          = float(Config.get(section[0],"J2_ratio"))
            Exo.Jratio[2]          = float(Config.get(section[0],"J3_ratio"))
            Exo.Jratio[3]          = float(Config.get(section[0],"J4_ratio"))
            Exo.Jratio[4]          = float(Config.get(section[0],"J5_ratio"))

            Exo.Joffset[0]         = int(Config.get(section[0],"J1_offset"))
            Exo.Joffset[1]         = int(Config.get(section[0],"J2_offset"))
            Exo.Joffset[2]         = int(Config.get(section[0],"J3_offset"))
            Exo.Joffset[3]         = int(Config.get(section[0],"J4_offset"))
            Exo.Joffset[4]         = int(Config.get(section[0],"J5_offset"))

            return Exo

        except Exception, e:
            print '# Error: ReadExoFile failed | ' + str(e)
            # Read conf failed -> create a new configuration file
            return False


    def WriteConfFile (self):

        print 'WriteConfFile called.'

        try:
            Config = ConfigParser.ConfigParser()
            Config.optionxform = str
            section = 'BRIDGE'
            Config.add_section(section)

            Config.set(section, 'FileName', self.Patient.Filename)
            Config.set(section, 'COM_J1', self.Serial.COM[0])
            Config.set(section, 'COM_J2', self.Serial.COM[1])
            Config.set(section, 'COM_J3', self.Serial.COM[2])
            Config.set(section, 'COM_J4', self.Serial.COM[3])
            Config.set(section, 'COM_J5', self.Serial.COM[4])

            Config.set(section, 'J1_min', self.Exo.Jmin[0])
            Config.set(section, 'J2_min', self.Exo.Jmin[1])
            Config.set(section, 'J3_min', self.Exo.Jmin[2])
            Config.set(section, 'J4_min', self.Exo.Jmin[3])
            Config.set(section, 'J5_min', self.Exo.Jmin[4])

            Config.set(section, 'J1_max', self.Exo.Jmax[0])
            Config.set(section, 'J2_max', self.Exo.Jmax[1])
            Config.set(section, 'J3_max', self.Exo.Jmax[2])
            Config.set(section, 'J4_max', self.Exo.Jmax[3])
            Config.set(section, 'J5_max', self.Exo.Jmax[4])

            Config.set(section, 'J1_ratio', self.Exo.Jratio[0])
            Config.set(section, 'J2_ratio', self.Exo.Jratio[1])
            Config.set(section, 'J3_ratio', self.Exo.Jratio[2])
            Config.set(section, 'J4_ratio', self.Exo.Jratio[3])
            Config.set(section, 'J5_ratio', self.Exo.Jratio[4])

            Config.set(section, 'J1_offset', self.Exo.Joffset[0])
            Config.set(section, 'J2_offset', self.Exo.Joffset[1])
            Config.set(section, 'J3_offset', self.Exo.Joffset[2])
            Config.set(section, 'J4_offset', self.Exo.Joffset[3])
            Config.set(section, 'J5_offset', self.Exo.Joffset[4])

            cfgfile = open(self.exo_file,'w')
            Config.write(cfgfile)
            cfgfile.close()
            return True
        except Exception, e:
            print '# Error: couldn\'t save exoskeleton configuration | ' + str(e)
            return False



    def SavePatient (self, Filename, Patient):

        print 'SavePatient called.'

        try:
            Config = ConfigParser.ConfigParser()
            Config.optionxform = str
            section = 'BRIDGE-PATIENT'
            Config.add_section(section)

            Config.set(section, 'Name', Patient.Name)
            Config.set(section, 'Input', Patient.Input)

            Config.set(section, 'J1_min', Patient.Jmin[0])
            Config.set(section, 'J2_min', Patient.Jmin[1])
            Config.set(section, 'J3_min', Patient.Jmin[2])
            Config.set(section, 'J4_min', Patient.Jmin[3])
            Config.set(section, 'J5_min', Patient.Jmin[4])

            Config.set(section, 'J1_max', Patient.Jmax[0])
            Config.set(section, 'J2_max', Patient.Jmax[1])
            Config.set(section, 'J3_max', Patient.Jmax[2])
            Config.set(section, 'J4_max', Patient.Jmax[3])
            Config.set(section, 'J5_max', Patient.Jmax[4])

            Config.set(section, 'J1_default', Patient.Jdef[0])
            Config.set(section, 'J2_default', Patient.Jdef[1])
            Config.set(section, 'J3_default', Patient.Jdef[2])
            Config.set(section, 'J4_default', Patient.Jdef[3])
            Config.set(section, 'J5_default', Patient.Jdef[4])

            Config.set(section, 'J1_rest', Patient.Jrest[0])
            Config.set(section, 'J2_rest', Patient.Jrest[1])
            Config.set(section, 'J3_rest', Patient.Jrest[2])
            Config.set(section, 'J4_rest', Patient.Jrest[3])
            Config.set(section, 'J5_rest', Patient.Jrest[4])

            Config.set(section, 'l1', Patient.l1)
            Config.set(section, 'l2', Patient.l2)
            Config.set(section, 'l3', Patient.l3)

            Config.set(section, 'fixation_time', Patient.FixationTime)
            Config.set(section, 'J1min Defined', Patient.ROM_Defined[0])
            Config.set(section, 'J2min Defined', Patient.ROM_Defined[1])
            Config.set(section, 'J3min Defined', Patient.ROM_Defined[2])
            Config.set(section, 'J4min Defined', Patient.ROM_Defined[3])
            Config.set(section, 'J5min Defined', Patient.ROM_Defined[4])
            Config.set(section, 'J1max Defined', Patient.ROM_Defined[5])
            Config.set(section, 'J2max Defined', Patient.ROM_Defined[6])
            Config.set(section, 'J3max Defined', Patient.ROM_Defined[7])
            Config.set(section, 'J4max Defined', Patient.ROM_Defined[8])
            Config.set(section, 'J5max Defined', Patient.ROM_Defined[9])
            Config.set(section, 'Joy_destra', Patient.axis_max[0])
            Config.set(section, 'Joy_sinistra', Patient.axis_max[0])
            Config.set(section, 'Joy_avanti', Patient.axis_max[0])
            Config.set(section, 'Joy_indietro', Patient.axis_max[0])

            cfgfile = open(Filename,'w')
            Config.write(cfgfile)
            cfgfile.close()

            return True
        except Exception, e:
            print '# Error: couldn\'t save patient configuration | ' + str(e)
            return False


