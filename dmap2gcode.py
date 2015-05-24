#!/usr/bin/python
"""
    dmap2gcode G-Code Generator

    Copyright (C) <2015>  <Scorch>
    Source was used from the following works:
              image-to-gcode.py   2005 Chris Radek chris@timeguy.com
              image-to-gcode.py   2006 Jeff Epler
              Author.py(linuxcnc) 2007 Jeff Epler  jepler@unpythonic.net
              
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    To make it a menu item in Ubuntu use the Alacarte Menu Editor and add
    the command python YourPathToThisFile/ThisFilesName.py
    make sure you have made the file executable by right
    clicking and selecting properties then Permissions and Execute

    To use with EMC2 see the instructions at:
    http://wiki.linuxcnc.org/cgi-bin/emcinfo.pl?Simple_EMC_G-Code_Generators

    Version 0.01
    - Initial code

    Version 0.02
    - Updated e-mail address and web page in "Help - About"
    - Added option to disable arcs in the g-code output (useful for GRBL/ShapeOko) 
    - Fixed bug resulting in the selection of columns then rows having no effect
    - Added automatic scaling of all linear dimensions values when changing between units (in/mm)
    - fixed bug when using a configuration file ("dmap2gcode.ngc")

    Version 0.03
    - Fixed crash when filename contains non ASCII character

    Version 0.04
    - Fixed crash when roughing cutter is smaller than final cutter.
    
    Version 0.05
    - Eliminated G91.1 code when arcs are disabled.

    Version 0.06
    - Fixed GUI refresh (get rid of red warning) after a bad value was entered for "Top Tolerance"
    - Fixed compatibility with Python 3
    - Added .tap to extension list

"""
version = '0.06'

import sys
VERSION = sys.version_info[0]

if VERSION == 3:
    from tkinter import *
    from tkinter.filedialog import *
    import tkinter.messagebox
    MAXINT = sys.maxsize
    
else:
    from Tkinter import *
    from tkFileDialog import *
    import tkMessageBox
    MAXINT = sys.maxint

if VERSION < 3 and sys.version_info[1] < 6:
    def next(item):
        return item.next()
    
try:
    import psyco
    psyco.full()
    fmessage("(Psyco Loaded)");
    pass
except:
    pass

from math import *
from time import time
import os
import re
import binascii
import getopt
import operator

PIL = True
if PIL == True:
    try:
        from PIL import Image
        from PIL import ImageTk
        from PIL import ImageOps
        import _imaging
    except:
        PIL = False

NUMPY = True
if NUMPY == True:
    try:
        try:
            import numpy.numarray as numarray
            import numpy.core
            olderr = numpy.core.seterr(divide='ignore')
            plus_inf = (numarray.array((1.,))/0.)[0]
            numpy.core.seterr(**olderr)
        except ImportError:
            import numarray, numarray.ieeespecial
            plus_inf = numarray.ieeespecial.inf
    except:
        NUMPY = False

IN_AXIS   = "AXIS_PROGRESS_BAR" in os.environ

#Setting QUIET to True will stop almost all console messages
QUIET = False
STOP_CALC = 0

################################################################################
class Application(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)
        self.w = 780
        self.h = 490
        frame = Frame(master, width= self.w, height=self.h)
        self.master = master
        self.x = -1
        self.y = -1
        if PIL == False:
            fmessage("Python Imaging Library (PIL) was not found...Bummer")
            fmessage("    PIL enables more image file formats and enables the")
            fmessage("    preview image to scale with the window size.")
        if NUMPY == False:
            fmessage("NumPy was not found...Bummer")
            fmessage("    With NumPy the speed of gcode generation is about eight times faster.")
                
        self.createWidgets()


    def createWidgets(self):
        self.initComplete = 0
        self.master.bind("<Configure>", self.Master_Configure)
        self.master.bind('<Enter>', self.bindConfigure)
        self.master.bind('<Escape>', self.KEY_ESC)
        self.master.bind('<F1>', self.KEY_F1)
        self.master.bind('<F2>', self.KEY_F2)
        self.master.bind('<F3>', self.KEY_F3)
        self.master.bind('<F4>', self.KEY_F4)
        self.master.bind('<F5>', self.KEY_F5) #self.Recalculate_Click)
        self.master.bind('<Control-g>', self.KEY_CTRL_G)

        self.show_axis    = BooleanVar()
        self.invert       = BooleanVar()
        self.normalize    = BooleanVar()
        self.cuttop       = BooleanVar()
        self.cutperim     = BooleanVar()
        self.disable_arcs = BooleanVar()
        self.origin       = StringVar()
        
        self.yscale     = StringVar()
        self.Xscale     = StringVar()
        self.pixsize    = StringVar()
        self.toptol     = StringVar()

        self.tool       = StringVar()
        self.dia        = StringVar()
        self.v_angle    = StringVar()
        self.scanpat    = StringVar()
        self.scandir    = StringVar()
        self.f_feed     = StringVar()
        self.p_feed     = StringVar()
        self.stepover   = StringVar()
        self.z_cut      = StringVar()
        self.z_safe     = StringVar()
        
        self.ROUGH_TOOL     = StringVar()
        self.ROUGH_DIA      = StringVar()
        self.ROUGH_V_ANGLE  = StringVar()
        self.ROUGH_SCANPAT  = StringVar()
        self.ROUGH_SCANDIR  = StringVar()
        self.ROUGH_R_FEED   = StringVar()
        self.ROUGH_P_FEED   = StringVar()
        self.ROUGH_STEPOVER = StringVar()
        self.ROUGH_DEPTH_PP = StringVar()
        self.ROUGH_OFFSET   = StringVar()
        
        self.units      = StringVar()
        self.plungetype = StringVar()
        
        self.lace_bound = StringVar()
        self.cangle     = StringVar()
        self.tolerance  = StringVar()
        self.splitstep  = StringVar()

        self.funits     = StringVar()
        
        self.gpre        = StringVar()
        self.gpost       = StringVar()
        
        self.maxcut             = StringVar()
        self.current_input_file = StringVar()

        ###########################################################################
        #                         INITILIZE VARIABLES                             #
        #    if you want to change a default setting this is the place to do it   #
        ###########################################################################
        self.show_axis.set(1)
        self.invert.set(0)
        self.normalize.set(0)
        self.cuttop.set(1)
        self.cutperim.set(1)
        self.disable_arcs.set(0)

        self.yscale.set("5.0")
        self.Xscale.set("0")
        self.pixsize.set("0")
        self.toptol.set("-0.005")

        self.tool.set("Ball")           # Options are "Ball", "Flat", "Flat"
        self.scanpat.set("Rows")
        self.scandir.set("Alternating") # Options are "Alternating",
                                        #             "Positive"   , "Negative",
                                        #              "Up Mill", "Down Mill"
        self.v_angle.set("45")
        self.f_feed.set("15")
        self.p_feed.set("10")
        self.stepover.set("0.04")
        self.z_cut.set("-0.5")
        self.z_safe.set("0.25")       
        self.dia.set("0.25")
        self.scanpat.set("Rows")
        self.scandir.set("Alternating") # Options are "Alternating", 
                                        #             "Positive"   , "Negative",
                                        #              "Up Mill", "Down Mill"
                                        
        self.ROUGH_TOOL.set("Ball")           # Options are "Ball", "Flat", "Flat"                                
        self.ROUGH_V_ANGLE.set("45")
        self.ROUGH_R_FEED.set("15.0")
        self.ROUGH_P_FEED.set("10.0")
        self.ROUGH_STEPOVER.set("0.04")
        self.ROUGH_DEPTH_PP.set("0.10")
        self.ROUGH_OFFSET.set("0.02")
        self.ROUGH_DIA.set("0.25")
        self.ROUGH_SCANPAT.set("Rows")
        self.ROUGH_SCANDIR.set("Alternating") # Options are "Alternating", 
                                        #             "Positive"   , "Negative",
                                        #              "Up Mill", "Down Mill"        



        self.origin.set("Default")      # Options are "Default",
                                        #             "Top-Left", "Top-Center", "Top-Right",
                                        #             "Mid-Left", "Mid-Center", "Mid-Right",
                                        #             "Bot-Left", "Bot-Center", "Bot-Right"


        self.units.set("in")            # Options are "in" and "mm"
        self.plungetype.set("simple")

        self.lace_bound.set("None")     # Options "Full", "None", "??"
        self.cangle.set("45.0")
        self.tolerance.set("0.001")
        self.splitstep.set("0")        # Options 

        self.NGC_FILE     = (os.path.expanduser("~")+"/None")
        self.IMAGE_FILE   = (os.path.expanduser("~")+"/None")
        
        self.aspect_ratio =  0
        self.SCALE = 1
        
        self.gcode = []
        self.segID = []

        # PAN and ZOOM STUFF
        self.panx = 0
        self.panx = 0
        self.lastx = 0
        self.lasty = 0
        
        # Derived variables
        if self.units.get() == 'in':
            self.funits.set('in/min')
        else:
            self.units.set('mm')
            self.funits.set('mm/min')

        self.ui_TKimage = PhotoImage(format='gif',data=
         'R0lGODdhggDpAIAAAAAAAP///ywAAAAAggDpAAAC/oyPqcvtD6OctNqLs968'
        +'+w+G4kiW5ommCMC27uuqsgjXNjzn1833rQ5s+IbEoJGILBplyaZyWXJKn9DP'
        +'9DqserDcrDbTDfu+FrGZR56c17b0gw2vuRnx+muesOtj+LowPreGceYWtiVG'
        +'1jWiqMVlwriEpeJ4dJUjGWRJcVOhqTMl4RQK+ikKQfkmdWnqYHaqOslKx5ba'
        +'xGT7B9gqG4U7a1eLlMK7sseSm3RCfGDMt7AM4qvQfPcr3Hs9TV39nIztpb3N'
        +'nScd7R0u7kyeHXK+nq5ezG5OxQwv1z3f4S5/P26vjwM/A57ywUI3pl3Ag8HK'
        +'ERy4ASI0ZAEDQNSw0GEE/oYAwe3LWHGjRo2DQHq0iM/ayY4JP9Z7SKUHxZb9'
        +'aEY0KZNlG4MrUb4Eo+9cxYshywS9NlLiz5I9vS1TutToy2SkauZ8ZxPoT2FV'
        +'rXJCePXmVj080YA1KxCnLq9f2e50mdUnMKxhdbZN23TP2bt23+LNO9dtSsH/'
        +'MKqlRRct4XiGxwbu6xcyjkNLH0suLDeuVsBwyvKF2XOzZj+JP2euK7Yy4tKR'
        +'QWsWjdq1Ic+mL8KOfRrVYsxFmUZ1Rbu1bNN/Q+eGRrK376jHfxNl3rgoR9bE'
        +'lS+Hbrs5ce2YKWeX/Iok9x/fvkfv/drKdLjmcdObeB065Fhdb1vvWKqg1PV4'
        +'/sYbV8lff/5Jh4iAAPqTnoEI3tffggkaeBmCEKrh4GQTjlLhMRdukuGGOyzo'
        +'YXzNhJjaiCQWR9qJ7K2monqC3ALAhJAMI1whAdLgXh/yoagYhAx+KN5+Grr4'
        +'IJA3UrhdJztyiMl5SWJYpEgF2vfkLkvONKOQP0bIGJSEUPmjeXtNaWSTDeVI'
        +'HXAi6jfmYFh2VuJswbmZ5otxqrnbkHXaeeeXXOo5oJ/erZWNOOVluI0yiCYK'
        +'46IpruKooJFEqtsXlMJn6aVo2qhplx522mKb8IR6ZjqkemniqUrqpSqYlbbq'
        +'KqawlinrrE7+Z+t7m+Y6aI+8kiDmr7dWKeywNRa7/qKvyPaq7LI8EuusltBG'
        +'y2SU1CJp7bVSZqttqcd2uyq34B747bioTmsuueWmayWu7L657rtzWigvtuLK'
        +'G2y9ecaob7W79vsnvwBv++/AW+p7cL0J43slwPn2+zDCC7MbscITU9wwxBlL'
        +'7O7Aw8Xr8cXpimwuyeOaDG7F7wYZMssOH8kxzCu/qjHNFstZM5kMS4oxiyM/'
        +'ejJZJbOacqrXGnq0JrXC2qTMrernNKlsBuop0/UFXLWqU2NNXq5b75u1il/v'
        +'Se+pY5Pd3YlniwqyglcTvHEaa6vb7IVzw1u321HjjW4jb9PacaZ7e1swFHfb'
        +'GzekS4eLMrB/P1u44otLV3svjYNTHrnlk8dKp+GXr5l3fi7rmvgimydbuemN'
        +'Mx645qlD3vcjpTMb+gyzE/k6jrXT1zrvZXue+6E6Zv5y7C137jHcyS/PfPPO'
        +'Pw999NJPT3311gdRAAA7')
        self.im  = self.ui_TKimage
        self.wim = self.ui_TKimage.width()
        self.him = self.ui_TKimage.height()
        self.aspect_ratio =  float(self.wim-1) / float(self.him-1)

        ##########################################################################
        #                         G-Code Default Preamble                        #
        ##########################################################################
        # G17        ; sets XY plane                                             #
        # G90        ; Fixed cycle, simple cycle, for roughing (Z-axis emphasis) #
        # G64        ; G64 without P option keeps the best speed possible, no    #
        #              matter how far away from the programmed point you end up. #
        # M3 S3000   ; Spindle start at 3000                                     #
        # M7         ; Turn mist coolant on                                      #
        ##########################################################################
        self.gpre.set("G17 G90 G64 M3 S3000 M7")

        ##########################################################################
        #                        G-Code Default Postamble                        #
        ##########################################################################
        # M5 ; Stop Spindle                                                      #
        # M9 ; Turn all coolant off                                              #
        # M2 ; End Program                                                       #
        ##########################################################################
        self.gpost.set("M5 M9 M2")
        
        self.statusMessage = StringVar()
        self.statusMessage.set("Welcome to dmap2gcode")
        ##########################################################################
        ###                     END INITILIZING VARIABLES                      ###
        ##########################################################################

        # make a Status Bar
        self.statusbar = Label(self.master, textvariable=self.statusMessage, \
                                   bd=1, relief=SUNKEN , height=1)
        self.statusbar.pack(anchor=SW, fill=X, side=BOTTOM)
        

        # Buttons
        self.Save_Button = Button(self.master,text="Save G-Code",command=self.menu_File_Save_G_Code_File_Finish)
        self.Roughing_but = Button(self.master,text="Open Roughing Settings",command=self.ROUGH_Settings_Window)

        # Canvas
        lbframe = Frame( self.master )
        self.PreviewCanvas_frame = lbframe
        self.PreviewCanvas = Canvas(lbframe, width=self.w-525, \
                                        height=self.h-200, background="grey")
        self.PreviewCanvas.pack(side=LEFT, fill=BOTH, expand=1)
        self.PreviewCanvas_frame.place(x=230, y=10)

        self.PreviewCanvas.bind("<1>"        , self.mousePanStart)
        self.PreviewCanvas.bind("<B1-Motion>", self.mousePan)
        self.PreviewCanvas.bind("<2>"        , self.mousePanStart)
        self.PreviewCanvas.bind("<B2-Motion>", self.mousePan)
        self.PreviewCanvas.bind("<3>"        , self.mousePanStart)
        self.PreviewCanvas.bind("<B3-Motion>", self.mousePan)

        # Left Column #
        self.Label_font_prop = Label(self.master,text="Image Size:", anchor=W)

        self.Label_Yscale = Label(self.master,text="Image Height", anchor=CENTER)
        self.Label_Yscale_u = Label(self.master,textvariable=self.units, anchor=W)
        self.Entry_Yscale = Entry(self.master,width="15")
        self.Entry_Yscale.configure(textvariable=self.yscale)
        self.Entry_Yscale.bind('<Return>', self.Recalculate_Click)
        self.yscale.trace_variable("w", self.Entry_Yscale_Callback)
        self.NormalColor =  self.Entry_Yscale.cget('bg')

        self.Label_Yscale2 = Label(self.master,text="Image Width", anchor=CENTER)
        self.Label_Yscale2_u = Label(self.master,textvariable=self.units, anchor=W)
        self.Label_Yscale2_val = Label(self.master,textvariable=self.Xscale, anchor=W)

        self.Label_PixSize = Label(self.master,text="Pixel Size", anchor=CENTER)
        self.Label_PixSize_u = Label(self.master,textvariable=self.units, anchor=W)
        self.Label_PixSize_val = Label(self.master,textvariable=self.pixsize, anchor=W)
        
        self.Label_pos_orient = Label(self.master,text="Image Properties:",\
                                          anchor=W)


        self.Label_Origin      = Label(self.master,text="Origin", anchor=CENTER )
        self.Origin_OptionMenu = OptionMenu(root, self.origin,
                                            "Top-Left",
                                            "Top-Center",
                                            "Top-Right",
                                            "Mid-Left",
                                            "Mid-Center",
                                            "Mid-Right",
                                            "Bot-Left",
                                            "Bot-Center",
                                            "Bot-Right",
                                            "Default", command=self.Recalculate_RQD_Click)
        
        #Radio Button
        self.Label_Invert_Color_FALSE = Label(self.master,text="Depth Color")
        self.Radio_Invert_Color_FALSE = Radiobutton(self.master,text="Black", value=False,
                                         width="100", anchor=W)
        self.Radio_Invert_Color_FALSE.configure(variable=self.invert )
        #self.Label_Invert_Color_TRUE = Label(self.master,text=" ")
        self.Radio_Invert_Color_TRUE = Radiobutton(self.master,text="White", value=True,
                                         width="100", anchor=W)
        self.Radio_Invert_Color_TRUE.configure(variable=self.invert )


        self.Label_normalize = Label(self.master,text="Normalize Depth")
        self.Checkbutton_normalize = Checkbutton(self.master,text=" ", anchor=W)
        self.Checkbutton_normalize.configure(variable=self.normalize)

        self.separator1 = Frame(self.master, height=2, bd=1, relief=SUNKEN)
        self.separator2 = Frame(self.master, height=2, bd=1, relief=SUNKEN)
        self.separator3 = Frame(self.master, height=2, bd=1, relief=SUNKEN)
        self.separator4 = Frame(self.master, height=2, bd=1, relief=SUNKEN)

        self.Label_CutTop = Label(self.master,text="Cut Top Surface")
        self.Checkbutton_CutTop = Checkbutton(self.master,text=" ", \
                                              anchor=W, command=self.Set_Input_States)
        self.Checkbutton_CutTop.configure(variable=self.cuttop)

        self.Label_Toptol = Label(self.master,text="Top Tolerance", anchor=CENTER )
        self.Label_Toptol_u = Label(self.master,textvariable=self.units, anchor=W)
        self.Entry_Toptol = Entry(self.master,width="15")
        self.Entry_Toptol.configure(textvariable=self.toptol)
        self.toptol.trace_variable("w", self.Entry_Toptol_Callback)
 
        # End Left Column #

        # Right Column #
        self.Label_tool_opt = Label(self.master,text="Tool Properties:", anchor=W)

        self.Label_ToolDIA = Label(self.master,text="Tool DIA")
        self.Label_ToolDIA_u = Label(self.master,textvariable=self.units, anchor=W)
        self.Entry_ToolDIA = Entry(self.master,width="15")
        self.Entry_ToolDIA.configure(textvariable=self.dia)
        self.Entry_ToolDIA.bind('<Return>', self.Recalculate_Click)
        self.dia.trace_variable("w", self.Entry_ToolDIA_Callback)

        self.Label_Tool      = Label(self.master,text="Tool End", anchor=CENTER )
        self.Tool_OptionMenu = OptionMenu(root, self.tool, "Ball","V","Flat",\
                                               command=self.Set_Input_States_Event)
                
        self.Label_Vangle = Label(self.master,text="V-Bit Angle", anchor=CENTER )
        self.Entry_Vangle = Entry(self.master,width="15")
        self.Entry_Vangle.configure(textvariable=self.v_angle)
        self.Entry_Vangle.bind('<Return>', self.Recalculate_Click)
        self.v_angle.trace_variable("w", self.Entry_Vangle_Callback)

        self.Label_gcode_opt = Label(self.master,text="Gcode Properties:", anchor=W)

        self.Label_Scanpat      = Label(self.master,text="Scan Pattern", anchor=CENTER )
        self.ScanPat_OptionMenu = OptionMenu(root, self.scanpat, "Rows","Columns",\
                                            "R then C", "C then R")

        self.Label_CutPerim = Label(self.master,text="Cut Perimeter")
        self.Checkbutton_CutPerim = Checkbutton(self.master,text=" ", \
                                              anchor=W, command=self.Set_Input_States)
        self.Checkbutton_CutPerim.configure(variable=self.cutperim)

        self.Label_Scandir      = Label(self.master,text="Scan Direction", anchor=CENTER )
        self.ScanDir_OptionMenu = OptionMenu(root, self.scandir, "Alternating", "Positive",
                                            "Negative", "Up Mill", "Down Mill")
        
        self.Label_Feed = Label(self.master,text="Feed Rate")
        self.Label_Feed_u = Label(self.master,textvariable=self.funits, anchor=W)
        self.Entry_Feed = Entry(self.master,width="15")
        self.Entry_Feed.configure(textvariable=self.f_feed)
        self.Entry_Feed.bind('<Return>', self.Recalculate_Click)
        self.f_feed.trace_variable("w", self.Entry_Feed_Callback)

        self.Label_p_feed = Label(self.master,text="Plunge Feed", anchor=CENTER )
        self.Label_p_feed_u = Label(self.master,textvariable=self.funits, anchor=W)
        self.Entry_p_feed = Entry(self.master,width="15")
        self.Entry_p_feed.configure(textvariable=self.p_feed)
        self.Entry_p_feed.bind('<Return>', self.Recalculate_Click)
        self.p_feed.trace_variable("w", self.Entry_p_feed_Callback)

        self.Label_StepOver = Label(self.master,text="Stepover", anchor=CENTER )
        self.Label_StepOver_u = Label(self.master,textvariable=self.units, anchor=W)
        self.Entry_StepOver = Entry(self.master,width="15")
        self.Entry_StepOver.configure(textvariable=self.stepover)
        self.Entry_StepOver.bind('<Return>', self.Recalculate_Click)
        self.stepover.trace_variable("w", self.Entry_StepOver_Callback)

        self.Label_Zsafe = Label(self.master,text="Z Safe")
        self.Label_Zsafe_u = Label(self.master,textvariable=self.units, anchor=W)
        self.Entry_Zsafe = Entry(self.master,width="15")
        self.Entry_Zsafe.configure(textvariable=self.z_safe)
        self.Entry_Zsafe.bind('<Return>', self.Recalculate_Click)
        self.z_safe.trace_variable("w", self.Entry_Zsafe_Callback)

        self.Label_Zcut = Label(self.master,text="Max Cut Depth")
        self.Label_Zcut_u = Label(self.master,textvariable=self.units, anchor=W)
        self.Entry_Zcut = Entry(self.master,width="15")
        self.Entry_Zcut.configure(textvariable=self.z_cut)
        self.Entry_Zcut.bind('<Return>', self.Recalculate_Click)
        self.z_cut.trace_variable("w", self.Entry_Zcut_Callback)      
        # End Right Column #

        #GEN Setting Window Entry initializations
        self.Entry_Sspeed=Entry()
        self.Entry_BoxGap = Entry()
        self.Entry_ContAngle = Entry()
        self.Entry_Tolerance = Entry()

        #ROUGH Setting Window Entry initializations
        self.ROUGH_Entry_ToolDIA=Entry()
        self.ROUGH_Entry_Vangle=Entry()
        self.ROUGH_Entry_Feed=Entry()
        self.ROUGH_Entry_p_feed=Entry()
        self.ROUGH_Entry_StepOver=Entry()
        self.ROUGH_Entry_Roffset=Entry()
        self.ROUGH_Entry_Rdepth=Entry()

        # Make Menu Bar
        self.menuBar = Menu(self.master, relief = "raised", bd=2)

        top_File = Menu(self.menuBar, tearoff=0)
        top_File.add("command", label = "Open G-Code File", \
                         command = self.menu_File_Open_G_Code_File)

        top_File.add("command", label = "Open Image File", \
                             command = self.menu_File_Open_IMAGE_File)

        top_File.add("command", label = "Save G-Code File", \
                         command = self.menu_File_Save_G_Code_File_Finish)
        top_File.add("command", label = "Save Roughing G-Code File", \
                         command = self.menu_File_Save_G_Code_File_Rough)
        if IN_AXIS:
            top_File.add("command", label = "Write To Axis and Exit", \
                             command = self.WriteToAxis)
        else:
            top_File.add("command", label = "Exit", command = self.menu_File_Quit)
        self.menuBar.add("cascade", label="File", menu=top_File)

        top_Edit = Menu(self.menuBar, tearoff=0)
        top_Edit.add("command", label = "Copy G-Code Data to Clipboard", \
                         command = self.CopyClipboard_GCode)
        self.menuBar.add("cascade", label="Edit", menu=top_Edit)

        top_View = Menu(self.menuBar, tearoff=0)
        top_View.add("command", label = "Refresh", command = self.menu_View_Refresh)

        top_View.add_separator()

        top_View.add_checkbutton(label = "Show Origin Axis",  variable=self.show_axis , \
                                     command= self.menu_View_Refresh)

        self.menuBar.add("cascade", label="View", menu=top_View)

        top_Settings = Menu(self.menuBar, tearoff=0)
        top_Settings.add("command", label = "General Settings", \
                             command = self.GEN_Settings_Window)
        top_Settings.add("command", label = "Roughing Settings", \
                             command = self.ROUGH_Settings_Window)

        self.menuBar.add("cascade", label="Settings", menu=top_Settings)

        top_Help = Menu(self.menuBar, tearoff=0)
        top_Help.add("command", label = "About", command = self.menu_Help_About)
        self.menuBar.add("cascade", label="Help", menu=top_Help)

        self.master.config(menu=self.menuBar)

        ##########################################################################
        #                  Config File and command line options                  #
        ##########################################################################
        config_file = "dmap2gcode.ngc"
        home_config1 = os.path.expanduser("~") + "/" + config_file
        config_file2 = ".dmap2gcoderc"
        home_config2 = os.path.expanduser("~") + "/" + config_file2
        if ( os.path.isfile(config_file) ):
            self.Open_G_Code_File(config_file)
        elif ( os.path.isfile(home_config1) ):
            self.Open_G_Code_File(home_config1)
        elif ( os.path.isfile(home_config2) ):
            self.Open_G_Code_File(home_config2)

        opts, args = None, None
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hg:",["help", "gcode_file"])
        except:
            fmessage('Unable interpret command line options')
            sys.exit()
        for option, value in opts:
            if option in ('-h','--help'):
                fmessage(' ')
                fmessage('Usage: python dmap2gcode.py [-g file]')
                fmessage('-g    : dmap2gcode gcode output file to read (also --gcode_file)')
                fmessage('-h    : print this help (also --help)\n')
                sys.exit()
            if option in ('-g','--gcode_file'):
                    self.Open_G_Code_File(value)

        ##########################################################################

################################################################################
    def entry_set(self, val2, calc_flag=0, new=0):
        if calc_flag == 0 and new==0:
            try:
                self.statusbar.configure( bg = 'yellow' )
                val2.configure( bg = 'yellow' )
                self.statusMessage.set(" Recalculation required.")
            except:
                pass
        elif calc_flag == 3:
            try:
                val2.configure( bg = 'red' )
                self.statusbar.configure( bg = 'red' )
                self.statusMessage.set(" Value should be a number. ")
            except:
                pass
        elif calc_flag == 2:
            try:
                self.statusbar.configure( bg = 'red' )
                val2.configure( bg = 'red' )
            except:
                pass
        elif (calc_flag == 0 or calc_flag == 1) and new==1 :
            try:
                self.statusbar.configure( bg = 'white' )
                self.statusMessage.set(" ")
                val2.configure( bg = 'white' )
            except:
                pass
        elif (calc_flag == 1) and new==0 :
            try:
                self.statusbar.configure( bg = 'white' )
                self.statusMessage.set(" ")
                val2.configure( bg = 'white' )
            except:
                pass

        elif (calc_flag == 0 or calc_flag == 1) and new==2:
            return 0
        return 1

################################################################################

    ################################################################################
    def WriteGCode(self,rough_flag = 0):
        global Zero
        header = []
        header.append('( Code generated by dmap2gcode-'+version+'.py widget )')
        header.append('( by Scorch - 2014 )')
        header.append('(Settings used in dmap2gcode when this file was created)')
        header.append("(=========================================================)")
        # BOOL
        header.append('(dmap2gcode_set show_axis  %s )' %( int(self.show_axis.get())  ))
        header.append('(dmap2gcode_set invert     %s )' %( int(self.invert.get())     ))
        header.append('(dmap2gcode_set normalize  %s )' %( int(self.normalize.get())  ))
        header.append('(dmap2gcode_set cuttop     %s )' %( int(self.cuttop.get())     ))
        header.append('(dmap2gcode_set cutperim     %s )' %( int(self.cutperim.get())     ))
        header.append('(dmap2gcode_set disable_arcs %s )' %( int(self.disable_arcs.get()) ))


        # STRING.get()
        header.append('(dmap2gcode_set yscale     %s )'  %( self.yscale.get()         ))
        header.append('(dmap2gcode_set toptol     %s )'  %( self.toptol.get()         ))
        header.append('(dmap2gcode_set vangle     %s )'  %( self.v_angle.get()        ))
        header.append('(dmap2gcode_set stepover   %s )'  %( self.stepover.get()       ))
        header.append('(dmap2gcode_set plfeed     %s )'  %( self.p_feed.get()         ))
        header.append('(dmap2gcode_set z_safe      %s )'  %( self.z_safe.get()        ))
        header.append('(dmap2gcode_set z_cut       %s )'  %( self.z_cut.get()         ))
        header.append('(dmap2gcode_set diatool    %s )'  %( self.dia.get()            ))
        header.append('(dmap2gcode_set origin     %s )'  %( self.origin.get()         ))
        header.append('(dmap2gcode_set tool       %s )'  %( self.tool.get()           ))
        header.append('(dmap2gcode_set units      %s )'  %( self.units.get()          ))
        header.append('(dmap2gcode_set plunge     %s )'  %( self.plungetype.get()     ))
        header.append('(dmap2gcode_set feed       %s )'  %( self.f_feed.get()         ))
        header.append('(dmap2gcode_set lace       %s )'  %( self.lace_bound.get()     ))
        header.append('(dmap2gcode_set cangle     %s )'  %( self.cangle.get()         ))        
        header.append('(dmap2gcode_set tolerance  %s )'  %( self.tolerance.get()      )) 
        header.append('(dmap2gcode_set splitstep  %s )'  %( self.splitstep.get()      ))
        header.append('(dmap2gcode_set gpre       \042%s\042 )' %( self.gpre.get()    ))
        header.append('(dmap2gcode_set gpost      \042%s\042 )' %( self.gpost.get()   ))
        header.append('(dmap2gcode_set scanpat    \042%s\042 )' %( self.scanpat.get() ))
        header.append('(dmap2gcode_set scandir    \042%s\042 )' %( self.scandir.get() ))
        header.append('(dmap2gcode_set imagefile  \042%s\042 )' %( self.IMAGE_FILE    ))
        
        header.append('(dmap2gcode_set ROUGH_TOOL     %s )'  %( self.ROUGH_TOOL.get()    ))
        header.append('(dmap2gcode_set ROUGH_DIA      %s )'  %( self.ROUGH_DIA.get()     ))
        header.append('(dmap2gcode_set ROUGH_V_ANGLE  %s )'  %( self.ROUGH_V_ANGLE.get() ))
        header.append('(dmap2gcode_set ROUGH_R_FEED   %s )'  %( self.ROUGH_R_FEED.get()  ))
        header.append('(dmap2gcode_set ROUGH_P_FEED   %s )'  %( self.ROUGH_P_FEED.get()  ))
        header.append('(dmap2gcode_set ROUGH_STEPOVER %s )'  %( self.ROUGH_STEPOVER.get()))
        header.append('(dmap2gcode_set ROUGH_DEPTH_PP %s )'  %( self.ROUGH_DEPTH_PP.get()))
        header.append('(dmap2gcode_set ROUGH_OFFSET   %s )'  %( self.ROUGH_OFFSET.get()  ))
        header.append('(dmap2gcode_set ROUGH_SCANPAT  \042%s\042 )' %( self.ROUGH_SCANPAT.get() ))
        header.append('(dmap2gcode_set ROUGH_SCANDIR  \042%s\042 )' %( self.ROUGH_SCANDIR.get() ))
        
        header.append("(=========================================================)")
        header.append(self.gpre.get())

        postscript = self.gpost.get()
        ######################################
        ######################################
        pil_format = False
        try:
            test = self.im.width()
        except:
            try:
                test = self.im.size
                pil_format = True
            except:
                self.statusMessage.set("No Image Loaded")
                self.statusbar.configure( bg = 'red' )
                return
        
        MAT = Image_Matrix()
        MAT.FromImage(self.im,pil_format)

        image_h       =  float(self.yscale.get())
        pixel_size    =  image_h / ( float(MAT.width) - 1.0 )
        image_w       =  pixel_size * ( float(MAT.height) - 1.0 )
        tolerance     =  float(self.tolerance.get())
        safe_z        =  float(self.z_safe.get())
        splitstep     =  float(self.splitstep.get())
        toptol        =  float(self.toptol.get())
        depth         = -float(self.z_cut.get())
        Cont_Angle    =  float(self.cangle.get())
        cutperim      =  int(self.cutperim.get())
            
        if rough_flag == 0:
            ######################################################
            tool_type     =  self.tool.get()
            
            tool_diameter =  float(self.dia.get())
            rough_depth   =  0.0 
            rough_offset  =  0.0 
            feed_rate     =  float(self.f_feed.get())
            rough_feed    =  float(self.ROUGH_R_FEED.get())
            plunge_feed   =  float(self.p_feed.get())
            step          =  max(1, int(floor( float(self.stepover.get()) / pixel_size)))

            edge_offset   = 0
            ######################################################
            if self.tool.get() == "Flat":
                TOOL = make_tool_shape(endmill, tool_diameter, pixel_size)
            elif self.tool.get() == "V":
                v_angle = float(self.v_angle.get())
                TOOL = make_tool_shape(vee_common(v_angle), tool_diameter, pixel_size)
            else: #"Ball"
                TOOL = make_tool_shape(ball_tool, tool_diameter, pixel_size)
            ######################################################
                
            rows = 0
            columns = 0
            columns_first = 0
            if self.scanpat.get() != "Columns":
                rows = 1
            if self.scanpat.get() != "Rows":
                columns = 1 
            if self.scanpat.get() == "C then R":
                columns_first = 1

            ######################################################
            converter = self.scandir.get()
            lace_bound_val = self.lace_bound.get()
            ### END FINISH CUT STUFF ###
        else:
            ######################################################
            tool_type     =  self.ROUGH_TOOL.get()
            
            rough_depth   =  float(self.ROUGH_DEPTH_PP.get())
            rough_offset  =  float(self.ROUGH_OFFSET.get())
            tool_diameter =  float(self.ROUGH_DIA.get())
            finish_dia    =  float(self.dia.get())
            
            feed_rate     =  float(self.ROUGH_R_FEED.get())
            rough_feed    =  float(self.ROUGH_R_FEED.get())
            plunge_feed   =  float(self.ROUGH_P_FEED.get())
            step          =  max(1, int(floor( float(self.ROUGH_STEPOVER.get()) / pixel_size)))

            edge_offset = max(0, (tool_diameter - finish_dia)/2.0)
            ######################################################
            if self.ROUGH_TOOL.get() == "Flat":
                TOOL = make_tool_shape(endmill, tool_diameter, pixel_size, rough_offset)
            elif self.tool.get() == "V":
                v_angle = float(self.ROUGH_V_ANGLE.get())
                TOOL = make_tool_shape(vee_common(v_angle), tool_diameter, pixel_size, rough_offset)
            else: #"Ball"
                TOOL = make_tool_shape(ball_tool, tool_diameter, pixel_size, rough_offset)
            ######################################################

            rows = 0
            columns = 0
            columns_first = 0
            if self.ROUGH_SCANPAT.get() != "Columns":
                rows = 1
            if self.ROUGH_SCANPAT.get() != "Rows":
                columns = 1 
            if self.ROUGH_SCANPAT.get() == "C then R":
                columns_first = 1

            ######################################################
            converter = self.ROUGH_SCANDIR.get()
            lace_bound_val = self.lace_bound.get()
            
        ### END ROUGHING STUFF ###
            
            
        if converter == "Positive":
            conv_index = 0
            #fmessage("Positive")
            
        elif converter == "Negative":
            conv_index = 1
            #fmessage("Negative")
            
        elif converter == "Alternating":
            conv_index = 2
            #fmessage("Alternating")
            
        elif converter == "Up Mill":
            conv_index = 3
            #fmessage("Up Milling")
            
        elif converter == "Down Mill":
            conv_index = 4
            #fmessage("Down Mill")
        else:
            conv_index = 2
            fmessage("Converter Error: Setting to, Alternating")
        
        ###################################################### 
        if rows: convert_rows = convert_makers[conv_index]()
        else: convert_rows = None
        if columns: convert_cols = convert_makers[conv_index]()
        else: convert_cols = None

        ######################################################
        if lace_bound_val != "None" and rows and columns:
            
            slope = tan( Cont_Angle*pi/180 )
            if columns_first:
                convert_rows = Reduce_Scan_Lace(convert_rows, slope, step+1)
            else:
                convert_cols = Reduce_Scan_Lace(convert_cols, slope, step+1)
            if lace_bound_val == "Full":
                if columns_first:
                    convert_cols = Reduce_Scan_Lace(convert_cols, slope, step+1)
                else:
                    convert_rows = Reduce_Scan_Lace(convert_rows, slope, step+1)




        ######################################################
        ###              START COMMON STUFF                ###
        ######################################################
        if self.units.get() == "in":
            units = 'G20'
        else:
            units = 'G21'

        ######################################################
        if self.cuttop.get() != True:
            if rows == 1:
                convert_rows = Reduce_Scan_Lace_new(convert_rows, toptol, 1)
            if columns == 1:
                convert_cols = Reduce_Scan_Lace_new(convert_cols, toptol, 1)
        ######################################################
        disable_arcs = self.disable_arcs.get()
        ######################################################
        if self.plungetype.get() == "arc" and (not disable_arcs):
            Entry_cut   = ArcEntryCut(plunge_feed, .125)
        else:
            Entry_cut   = SimpleEntryCut(plunge_feed)
        ######################################################
        if self.normalize.get():
            pass
            a = MAT.min()
            b = MAT.max()
            if a != b:
                MAT.minus(a)
                MAT.mult(1./(b-a))
        else:
            MAT.mult(1/255.0)
            
        xoffset = 0
        yoffset = 0            
        ######################################################    
        MAT.mult(depth)
        
        ##########################################
        #         ORIGIN LOCATING STUFF          #
        ##########################################
        minx = 0
        maxx = image_w
        miny = 0
        maxy = image_h
        midx = (minx + maxx)/2
        midy = (miny + maxy)/2

        CASE = str(self.origin.get())
        if     CASE == "Top-Left":
            x_zero = minx
            y_zero = maxy
        elif   CASE == "Top-Center":
            x_zero = midx
            y_zero = maxy
        elif   CASE == "Top-Right":
            x_zero = maxx
            y_zero = maxy
        elif   CASE == "Mid-Left":
            x_zero = minx
            y_zero = midy
        elif   CASE == "Mid-Center":
            x_zero = midx
            y_zero = midy
        elif   CASE == "Mid-Right":
            x_zero = maxx
            y_zero = midy
        elif   CASE == "Bot-Left":
            x_zero = minx
            y_zero = miny
        elif   CASE == "Bot-Center":
            x_zero = midx
            y_zero = miny
        elif   CASE == "Bot-Right":
            x_zero = maxx
            y_zero = miny
        elif   CASE == "Arc-Center":
            x_zero = 0
            y_zero = 0
        else:          #"Default"
            x_zero = 0
            y_zero = 0   

        xoffset = xoffset - x_zero
        yoffset = yoffset - y_zero
        
        ######################################################
        if self.invert.get():
            MAT.mult(-1.0)
        else:
            MAT.minus(depth)
            
        ######################################################
            
        self.gcode = []
        
        MAT.pad_w_zeros(TOOL)
        
        START_TIME=time()
        self.gcode = convert(self,          \
                             MAT,           \
                             units,         \
                             TOOL,          \
                             pixel_size,    \
                             step,          \
                             safe_z,        \
                             tolerance,     \
                             feed_rate,     \
                             convert_rows,  \
                             convert_cols,  \
                             columns_first, \
                             cutperim,      \
                             Entry_cut,     \
                             rough_depth,   \
                             rough_feed,    \
                             xoffset,       \
                             yoffset,       \
                             splitstep,     \
                             header,        \
                             postscript,    \
                             edge_offset,   \
                             disable_arcs)
        ######################################################

    ################################################################################
    def CopyClipboard_GCode(self):
        self.clipboard_clear()
        if (self.Check_All_Variables() > 0):
            return
        self.WriteGCode()
        for line in self.gcode:
            self.clipboard_append(line+'\n')
        self.statusMessage.set("G-Code Sent to Clipboard")

    def CopyClipboard_SVG(self):
        self.clipboard_clear()
        self.WriteSVG()
        for line in self.svgcode:
            self.clipboard_append(line+'\n')

    def WriteToAxis(self):
        if (self.Check_All_Variables() > 0):
            return
        self.WriteGCode()
        for line in self.gcode:
            sys.stdout.write(line+'\n')
        self.Quit_Click(None)

    def Quit_Click(self, event):
        self.statusMessage.set("Exiting!")
        root.destroy()

    def mousePanStart(self,event):
        self.panx = event.x
        self.pany = event.y

    def mousePan(self,event):
        all = self.PreviewCanvas.find_all()
        dx = event.x-self.panx
        dy = event.y-self.pany
        for i in all:
            self.PreviewCanvas.move(i, dx, dy)
        self.lastx = self.lastx + dx
        self.lasty = self.lasty + dy
        self.panx = event.x
        self.pany = event.y

    def Recalculate_Click(self, event):
        pass

    def Settings_ReLoad_Click(self, event):
        win_id=self.grab_current()

    def Close_Current_Window_Click(self):
        win_id=self.grab_current()
        win_id.destroy()

    def Stop_Click(self, event):
        global STOP_CALC
        STOP_CALC=1
        
    # Left Column #
    #############################
    def Entry_Yscale_Check(self):
        try:
            value = float(self.yscale.get())
            if  value <= 0.0:
                self.statusMessage.set(" Height should be greater than 0 ")
                return 2 # Value is invalid number
            else:
                self.Xscale.set("%.3f" %( self.aspect_ratio * float(self.yscale.get())) )
                self.pixsize.set("%.3f" %( float(self.yscale.get()) / (self.him - 1.0) ) )
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Yscale_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Yscale, self.Entry_Yscale_Check(), new=1)        
    #############################
    def Entry_Toptol_Check(self):
        try:
            value = float(self.toptol.get())
            if  value > 0.0:
                self.statusMessage.set(" Tolerance should be less than or equal to 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Toptol_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Toptol, self.Entry_Toptol_Check(), new=1)
    #############################
    # End Left Column #
    #############################
    
    #############################
    # Start Right Column #
    #############################
    def Entry_ToolDIA_Check(self):
        try:
            value = float(self.dia.get())
            if  value <= 0.0:
                self.statusMessage.set(" Diameter should be greater than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_ToolDIA_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_ToolDIA, self.Entry_ToolDIA_Check(), new=1)
    #############################
    def Entry_Vangle_Check(self):
        try:
            value = float(self.v_angle.get())
            if  value <= 0 or value >= 180:
                self.statusMessage.set(" Angle should be between 0 and 180")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Vangle_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Vangle, self.Entry_Vangle_Check(), new=1)
    #############################
    def Entry_Feed_Check(self):
        try:
            value = float(self.f_feed.get())
            if  value <= 0.0:
                self.statusMessage.set(" Feed should be greater than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 1         # Value is a valid number changes do not require recalc
    def Entry_Feed_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Feed,self.Entry_Feed_Check(), new=1)
    #############################
    def Entry_p_feed_Check(self):
        try:
            value = float(self.p_feed.get())
            if  value <= 0.0:
                self.statusMessage.set(" Feed should be greater than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_p_feed_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_p_feed, self.Entry_p_feed_Check(), new=1)
    #############################
    def Entry_StepOver_Check(self):
        try:
            value = float(self.stepover.get())
            if  value <= 0.0:
                self.statusMessage.set(" Stepover should be greater than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_StepOver_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_StepOver, self.Entry_StepOver_Check(), new=1)
    #############################
    def Entry_Zsafe_Check(self):
        try:
            value = float(self.z_safe.get())
            if  value <= 0.0:
                self.statusMessage.set(" Z safe should be greater than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 1         # Value is a valid number changes do not require recalc
    def Entry_Zsafe_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Zsafe,self.Entry_Zsafe_Check(), new=1)
    #############################
    def Entry_Zcut_Check(self):
        try:
            value = float(self.z_cut.get())
            if  value >= 0.0:
                self.statusMessage.set(" Max depth should be less than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 1         # Value is a valid number changes do not require recalc
    def Entry_Zcut_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Zcut,self.Entry_Zcut_Check(), new=1)
    #############################
    # End Right Column #
    #############################

    #############################
    # Start ROUGH Setttings     #
    #############################
    def ROUGH_Entry_ToolDIA_Check(self):
        try:
            value = float(self.ROUGH_DIA.get())
            if  value <= 0.0:
                self.statusMessage.set(" Diameter should be greater than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def ROUGH_Entry_ToolDIA_Callback(self, varName, index, mode):
        self.entry_set(self.ROUGH_Entry_ToolDIA, self.ROUGH_Entry_ToolDIA_Check(), new=1)
    #############################
    def ROUGH_Entry_Vangle_Check(self):
        try:
            value = float(self.ROUGH_V_ANGLE.get())
            if  value <= 0 or value >= 180:
                self.statusMessage.set(" Angle should be between 0 and 180")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def ROUGH_Entry_Vangle_Callback(self, varName, index, mode):
        self.entry_set(self.ROUGH_Entry_Vangle, self.ROUGH_Entry_Vangle_Check(), new=1)
    #############################
    def ROUGH_Entry_Feed_Check(self):
        try:
            value = float(self.ROUGH_R_FEED.get())
            if  value <= 0.0:
                self.statusMessage.set(" Feed should be greater than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 1         # Value is a valid number changes do not require recalc
    def ROUGH_Entry_Feed_Callback(self, varName, index, mode):
        self.entry_set(self.ROUGH_Entry_Feed,self.ROUGH_Entry_Feed_Check(), new=1)
    #############################
    def ROUGH_Entry_p_feed_Check(self):
        try:
            value = float(self.ROUGH_P_FEED.get())
            if  value <= 0.0:
                self.statusMessage.set(" Feed should be greater than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def ROUGH_Entry_p_feed_Callback(self, varName, index, mode):
        self.entry_set(self.ROUGH_Entry_p_feed, self.ROUGH_Entry_p_feed_Check(), new=1)
    #############################
    def ROUGH_Entry_StepOver_Check(self):
        try:
            value = float(self.ROUGH_STEPOVER.get())
            if  value <= 0.0:
                self.statusMessage.set(" Stepover should be greater than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def ROUGH_Entry_StepOver_Callback(self, varName, index, mode):
        self.entry_set(self.ROUGH_Entry_StepOver, self.ROUGH_Entry_StepOver_Check(), new=1)
    #############################
    def ROUGH_Entry_Roffset_Check(self):
        try:
            value = float(self.ROUGH_OFFSET.get())
            if  value < 0.0:
                self.statusMessage.set(" Roughing offset should be greater than or equal to 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def ROUGH_Entry_Roffset_Callback(self, varName, index, mode):
        self.entry_set(self.ROUGH_Entry_Roffset, self.ROUGH_Entry_Roffset_Check(), new=1)
    #############################
    def ROUGH_Entry_Rdepth_Check(self):
        try:
            value = float(self.ROUGH_DEPTH_PP.get())
            if  value < 0.0:
                self.statusMessage.set(" Roughing depth per pass should be greater than or equal to 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def ROUGH_Entry_Rdepth_Callback(self, varName, index, mode):
        self.entry_set(self.ROUGH_Entry_Rdepth, self.ROUGH_Entry_Rdepth_Check(), new=1)
    #############################
    # End ROUGH setttings       #
    #############################

    #############################
    def Entry_Tolerance_Check(self):
        try:
            value = float(self.tolerance.get())
            if  value <= 0.0:
                self.statusMessage.set(" Tolerance should be greater than 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Tolerance_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Tolerance,self.Entry_Tolerance_Check(), new=1)
    #############################
    def Entry_ContAngle_Check(self):
        try:
            value = float(self.cangle.get())
            if  value <= 0.0 or value >= 90:
                self.statusMessage.set(" Contact angle should be between 0 and 90 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_ContAngle_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_ContAngle,self.Entry_ContAngle_Check(), new=1)
    #############################

    ##########################################################################
    ##########################################################################
    def Check_All_Variables(self):
        MAIN_error_cnt= \
        self.entry_set(self.Entry_Yscale, self.Entry_Yscale_Check()    ,2) +\
        self.entry_set(self.Entry_Toptol, self.Entry_Toptol_Check()    ,2) +\
        self.entry_set(self.Entry_ToolDIA, self.Entry_ToolDIA_Check()  ,2) +\
        self.entry_set(self.Entry_Vangle, self.Entry_Vangle_Check()    ,2) +\
        self.entry_set(self.Entry_Feed,self.Entry_Feed_Check()         ,2) +\
        self.entry_set(self.Entry_p_feed, self.Entry_p_feed_Check()  ,2)   +\
        self.entry_set(self.Entry_StepOver, self.Entry_StepOver_Check(),2) +\
        self.entry_set(self.Entry_Zsafe,self.Entry_Zsafe_Check()       ,2) +\
        self.entry_set(self.Entry_Zcut,self.Entry_Zcut_Check()         ,2)

        GEN_error_cnt= \
        self.entry_set(self.Entry_Tolerance,self.Entry_Tolerance_Check(),2) +\
        self.entry_set(self.Entry_ContAngle,self.Entry_ContAngle_Check(),2)
        
        ROUGH_error_cnt= \
        self.entry_set(self.ROUGH_Entry_ToolDIA, self.ROUGH_Entry_ToolDIA_Check()  ,2) +\
        self.entry_set(self.ROUGH_Entry_Vangle, self.ROUGH_Entry_Vangle_Check()    ,2) +\
        self.entry_set(self.ROUGH_Entry_Feed,self.ROUGH_Entry_Feed_Check()         ,2) +\
        self.entry_set(self.ROUGH_Entry_p_feed, self.ROUGH_Entry_p_feed_Check()  ,2)   +\
        self.entry_set(self.ROUGH_Entry_StepOver, self.ROUGH_Entry_StepOver_Check(),2) +\
        self.entry_set(self.ROUGH_Entry_Roffset, self.ROUGH_Entry_Roffset_Check()  ,2) +\
        self.entry_set(self.ROUGH_Entry_Rdepth, self.ROUGH_Entry_Rdepth_Check()    ,2)


        ERROR_cnt = MAIN_error_cnt + GEN_error_cnt + ROUGH_error_cnt

        if (ERROR_cnt > 0):
            self.statusbar.configure( bg = 'red' )
        if (GEN_error_cnt > 0):
            self.statusMessage.set(\
                " Entry Error Detected: Check Entry Values in General Settings Window ")
        if (MAIN_error_cnt > 0):
            self.statusMessage.set(\
                " Entry Error Detected: Check Entry Values in Main Window ")
        if (ROUGH_error_cnt > 0):
            self.statusMessage.set(\
                " Entry Error Detected: Check Entry Values in Roughing Settigns Window ")

        return ERROR_cnt

    def Entry_units_var_Callback(self):
        if (self.units.get() == 'in') and (self.funits.get()=='mm/min'):
            self.Scale_Linear_Inputs(1/25.4)
            self.funits.set('in/min')
        elif (self.units.get() == 'mm') and (self.funits.get()=='in/min'):
            self.Scale_Linear_Inputs(25.4)
            self.funits.set('mm/min')

    def Scale_Linear_Inputs(self, factor=1.0):
        try:
            self.yscale.set(        '%.3g' %(float(self.yscale.get()        )*factor) )
            self.toptol.set(        '%.3g' %(float(self.toptol.get()        )*factor) )
            self.dia.set(           '%.3g' %(float(self.dia.get()           )*factor) )
            self.f_feed.set(        '%.3g' %(float(self.f_feed.get()        )*factor) )
            self.p_feed.set(        '%.3g' %(float(self.p_feed.get()        )*factor) )
            self.stepover.set(      '%.3g' %(float(self.stepover.get()      )*factor) )
            self.z_cut.set(         '%.3g' %(float(self.z_cut.get()         )*factor) )
            self.z_safe.set(        '%.3g' %(float(self.z_safe.get()        )*factor) )
            self.ROUGH_R_FEED.set(  '%.3g' %(float(self.ROUGH_R_FEED.get()  )*factor) )
            self.ROUGH_P_FEED.set(  '%.3g' %(float(self.ROUGH_P_FEED.get()  )*factor) )
            self.ROUGH_STEPOVER.set('%.3g' %(float(self.ROUGH_STEPOVER.get())*factor) )
            self.ROUGH_DEPTH_PP.set('%.3g' %(float(self.ROUGH_DEPTH_PP.get())*factor) )
            self.ROUGH_OFFSET.set(  '%.3g' %(float(self.ROUGH_OFFSET.get()  )*factor) )
            self.ROUGH_DIA.set(     '%.3g' %(float(self.ROUGH_DIA.get()     )*factor) )
            self.tolerance.set(     '%.3g' %(float(self.tolerance.get()     )*factor) )
        except:
            pass

    def menu_File_Open_G_Code_File(self):
        init_dir = os.path.dirname(self.NGC_FILE)
        if ( not os.path.isdir(init_dir) ):
            init_dir = os.path.expanduser("~")
        fileselect = askopenfilename(filetypes=[("Gcode Files","*.ngc"),\
                                                ("TAP File","*.tap"),\
                                                ("All Files","*")],\
                                                 initialdir=init_dir)

        if fileselect != '' and fileselect != ():
            self.Open_G_Code_File(fileselect)

    def menu_File_Open_IMAGE_File(self):
        init_dir = os.path.dirname(self.IMAGE_FILE)
        if ( not os.path.isdir(init_dir) ):
            init_dir = os.path.expanduser("~")

        if PIL:
            fileselect = askopenfilename(filetypes=[("Image Files", ("*.pgm","*.jpg","*.png","*.gif")),
                                                    ("All Files","*")],\
                                                     initialdir=init_dir)
        else:
            fileselect = askopenfilename(filetypes=[("Image Files", ("*.pgm","*.gif")),\
                                                    ("All Files","*.*")],\
                                                    initialdir=init_dir)

        if fileselect != '' and fileselect != ():
            self.Read_image_file(fileselect)
            self.Plot_Data()

    def Open_G_Code_File(self,filename):
        try:
            fin = open(filename,'r')
        except:
            fmessage("Unable to open file: %s" %(filename))
            return
        
        text_codes=[]
        ident = "dmap2gcode_set"
        for line in fin:
            if ident in line:
                # BOOL
                if   "show_axis"  in line:
                    self.show_axis.set(line[line.find("show_axis"):].split()[1])
                elif "invert"  in line:
                    self.invert.set(line[line.find("invert"):].split()[1])
                elif "normalize"  in line:
                    self.normalize.set(line[line.find("normalize"):].split()[1])
                elif "cuttop"  in line:
                    self.cuttop.set(line[line.find("cuttop"):].split()[1])
                elif "cutperim"  in line:
                    self.cuttop.set(line[line.find("cutperim"):].split()[1])
                elif "disable_arcs"  in line:
                    self.cuttop.set(line[line.find("disable_arcs"):].split()[1])

                # STRING.set()
                elif "yscale"     in line:
                    self.yscale.set(line[line.find("yscale"):].split()[1])
                elif "toptol"    in line:
                    self.toptol.set(line[line.find("toptol"):].split()[1])
                elif "vangle"    in line:
                    self.v_angle.set(line[line.find("vangle"):].split()[1])
                elif "stepover"    in line:
                    self.stepover.set(line[line.find("stepover"):].split()[1])
                elif "plfeed"    in line:
                    self.p_feed.set(line[line.find("plfeed"):].split()[1])
                elif "z_safe"    in line:
                    self.z_safe.set(line[line.find("z_safe"):].split()[1])
                elif "z_cut"    in line:
                    self.z_cut.set(line[line.find("z_cut"):].split()[1])
                elif "diatool"    in line:
                    self.dia.set(line[line.find("diatool"):].split()[1])
                elif "origin"    in line:
                    self.origin.set(line[line.find("origin"):].split()[1])
                elif "tool"    in line:
                    self.tool.set(line[line.find("tool"):].split()[1])
                elif "units"    in line:
                    self.units.set(line[line.find("units"):].split()[1])
                elif "plunge"    in line:
                    self.plungetype.set(line[line.find("plunge"):].split()[1])
                elif "feed"    in line:
                     self.f_feed.set(line[line.find("feed"):].split()[1])
                elif "lace"    in line:
                     self.lace_bound.set(line[line.find("lace"):].split()[1])
                elif "cangle"    in line:
                     self.cangle.set(line[line.find("cangle"):].split()[1])    
                elif "tolerance"    in line:
                     self.tolerance.set(line[line.find("tolerance"):].split()[1])
                elif "splitstep"    in line:
                     self.splitstep.set(line[line.find("splitstep"):].split()[1])

                elif "scanpat"    in line:
                     self.scanpat.set(line[line.find("scanpat"):].split("\042")[1])
                elif "scandir"    in line:
                     self.scandir.set(line[line.find("scandir"):].split("\042")[1])
                elif "gpre"    in line:
                     self.gpre.set(line[line.find("gpre"):].split("\042")[1])
                elif "gpost"    in line:
                     self.gpost.set(line[line.find("gpost"):].split("\042")[1])
                elif "imagefile"    in line:
                       self.IMAGE_FILE=(line[line.find("imagefile"):].split("\042")[1])
                       
                elif "ROUGH_TOOL"    in line:
                     self.ROUGH_TOOL.set(line[line.find("ROUGH_TOOL"):].split()[1])
                elif "ROUGH_DIA"    in line:
                     self.ROUGH_DIA.set(line[line.find("ROUGH_DIA"):].split()[1])
                elif "ROUGH_V_ANGLE"    in line:
                     self.ROUGH_V_ANGLE.set(line[line.find("ROUGH_V_ANGLE"):].split()[1])
                elif "ROUGH_R_FEED"    in line:
                     self.ROUGH_R_FEED.set(line[line.find("ROUGH_R_FEED"):].split()[1])
                elif "ROUGH_P_FEED"    in line:
                     self.ROUGH_P_FEED.set(line[line.find("ROUGH_P_FEED"):].split()[1])
                elif "ROUGH_STEPOVER"    in line:
                     self.ROUGH_STEPOVER.set(line[line.find("ROUGH_STEPOVER"):].split()[1])
                elif "ROUGH_DEPTH_PP"    in line:
                     self.ROUGH_DEPTH_PP.set(line[line.find("ROUGH_DEPTH_PP"):].split()[1])
                elif "ROUGH_OFFSET"    in line:
                     self.ROUGH_OFFSET.set(line[line.find("ROUGH_OFFSET"):].split()[1])                     
                elif "ROUGH_SCANPAT"    in line:
                     self.ROUGH_SCANPAT.set(line[line.find("ROUGH_SCANPAT"):].split("\042")[1])
                elif "ROUGH_SCANDIR"    in line:
                     self.ROUGH_SCANDIR.set(line[line.find("ROUGH_SCANDIR"):].split("\042")[1])
                     
        fin.close()
            
        fileName, fileExtension = os.path.splitext(self.IMAGE_FILE)
        init_file=os.path.basename(fileName)
        if init_file != "None":
            if ( os.path.isfile(self.IMAGE_FILE) ):
                self.Read_image_file(self.IMAGE_FILE)
            else:
                self.statusMessage.set("Image file not found: %s " %(self.IMAGE_FILE))

        if self.units.get() == 'in':
            self.funits.set('in/min')
        else:
            self.units.set('mm')
            self.funits.set('mm/min')

        temp_name, fileExtension = os.path.splitext(filename)
        file_base=os.path.basename(temp_name)
            
        if self.initComplete == 1:
            self.menu_Mode_Change()
            self.NGC_FILE = filename
        
    ###############################################

    def Read_image_file(self,fileselect):
        im = []
        if not ( os.path.isfile(fileselect) ):
            self.statusMessage.set("Image file not found: %s" %(fileselect))
            self.statusbar.configure( bg = 'red' )            
        else:
            self.statusMessage.set("Image file: %s " %(fileselect))
            self.statusbar.configure( bg = 'white' ) 
            try:
                if PIL:
                    PIL_im = Image.open(fileselect)
                    self.wim, self.him = PIL_im.size
                    # Convert image to grayscale
                    PIL_im = PIL_im.convert("L") 
                else:
                    im = PhotoImage(file=fileselect)
                    self.wim = im.width()
                    self.him = im.height()

                self.aspect_ratio =  float(self.wim-1) / float(self.him-1)
                self.Xscale.set("%.3f" %( self.aspect_ratio * float(self.yscale.get())) ) 
                self.pixsize.set("%.3f" %( float(self.yscale.get()) / (self.him - 1.0) ) )
                                
                ######################################
                ######################################
                if PIL:
                    self.im = PIL_im
                    self.SCALE = 1
                    self.ui_TKimage = ImageTk.PhotoImage(self.im.resize((50,50), Image.ANTIALIAS))
                else:
                    self.ui_TKimage = im
                    self.im = self.ui_TKimage
                    self.SCALE = 1
                    
                self.IMAGE_FILE = fileselect
                    
            except:
                self.statusMessage.set("Unable to Open Image file: %s" %(self.IMAGE_FILE))
                self.statusbar.configure( bg = 'red' )    
                
            
    ##########################################################################
    ##########################################################################
    def menu_File_Save_G_Code_File_Finish(self):
        self.menu_File_Save_G_Code_File(rough_flag = 0)

    def menu_File_Save_G_Code_File_Rough(self):
        win_id=self.grab_current()
        self.menu_File_Save_G_Code_File(rough_flag = 1)
        try:
            win_id.withdraw()
            win_id.deiconify()
            win_id.grab_set()
        except:
            pass

    def menu_File_Save_G_Code_File(self,rough_flag = 0):
        global STOP_CALC
        STOP_CALC = 0
        if (self.Check_All_Variables() > 0):
            return
        
        init_dir = os.path.dirname(self.NGC_FILE)
        if ( not os.path.isdir(init_dir) ):
            init_dir = os.path.expanduser("~")

        fileName, fileExtension = os.path.splitext(self.NGC_FILE)
        init_file=os.path.basename(fileName)
        
        fileName, fileExtension = os.path.splitext(self.IMAGE_FILE)
        init_file=os.path.basename(fileName)


        init_file = init_file.replace('_rough', '')
        if rough_flag == 1:
            init_file = init_file + "_rough"
        filename = asksaveasfilename(defaultextension='.ngc', \
                                     filetypes=[("G-Code Files","*.ngc"),("TAP File","*.tap"),("All Files","*")],\
                                     initialdir=init_dir,\
                                     initialfile= init_file )
        
        if filename != '' and filename != ():
            self.NGC_FILE = filename

            try:
                fout = open(filename,'w')
            except:
                self.statusMessage.set("Unable to open file for writing: %s" %(filename))
                self.statusbar.configure( bg = 'red' )
                return

            vcalc_status = Toplevel(width=525, height=50)
            # Use grab_set to prevent user input in the main window during calculations
            vcalc_status.grab_set()

            self.statusbar2 = Label(vcalc_status, textvariable=self.statusMessage, bd=1, relief=FLAT , height=1)
            self.statusbar2.place(x=130+12+12, y=12, width=350, height=30)
            self.statusMessage.set("Preparing Image Data")
            self.statusbar.configure( bg = 'yellow' )

            STOP_CALC = 0
            self.stop_button = Button(vcalc_status,text="Stop Calculation")
            self.stop_button.place(x=12, y=12, width=130, height=30)
            self.stop_button.bind("<ButtonRelease-1>", self.Stop_Click)
            
            vcalc_status.resizable(0,0)
            vcalc_status.title('Saving File')
            vcalc_status.iconname("dmap2gcode")
            
            try: #Attempt to create temporary icon bitmap file
                f = open("dmap2gcode_icon",'w')
                f.write("#define dmap2gcode_icon_width 16\n")
                f.write("#define dmap2gcode_icon_height 16\n")
                f.write("static unsigned char dmap2gcode_icon_bits[] = {\n")
                f.write("   0x3f, 0xfc, 0x1f, 0xf8, 0xcf, 0xf3, 0x6f, 0xe4, 0x6f, 0xed, 0xcf, 0xe5,\n")
                f.write("   0x1f, 0xf4, 0xfb, 0xf3, 0x73, 0x98, 0x47, 0xce, 0x0f, 0xe0, 0x3f, 0xf8,\n")
                f.write("   0x7f, 0xfe, 0x3f, 0xfc, 0x9f, 0xf9, 0xcf, 0xf3 };\n")
                f.close()
                vcalc_status.iconbitmap("@dmap2gcode_icon")
                os.remove("dmap2gcode_icon") 
            except:
                fmessage("Unable to create temporary icon file.")

            vcalc_status.update_idletasks()
            self.WriteGCode(rough_flag = rough_flag)
            for line in self.gcode:
                try:
                    fout.write(line+'\n')
                except:
                    fmessage("skipping g-code line:" + line + "; may be due to non ASCII character.");
                    pass
            fout.close
            if STOP_CALC == 0:
                self.statusMessage.set("File Saved: %s" %(filename))
                self.statusbar.configure( bg = 'white' )
            else:
                self.statusMessage.set("File Save Terminated")
                self.statusbar.configure( bg = 'yellow' )
            vcalc_status.grab_release()
            try:
                vcalc_status.destroy()
            except:
                pass
    ##########################################################################
    ##########################################################################
            
    def menu_File_Quit(self):
        if message_ask_ok_cancel("Exit", "Exiting...."):
            self.Quit_Click(None)

    def menu_View_Refresh_Callback(self, varName, index, mode):
        self.menu_View_Refresh()

    def menu_View_Refresh(self):
        dummy_event = Event()
        dummy_event.widget=self.master
        self.Master_Configure(dummy_event,1)
        self.Plot_Data()

    def menu_Mode_Change_Callback(self, varName, index, mode):
        self.menu_View_Refresh()

    def menu_Mode_Change(self):
        dummy_event = Event()
        dummy_event.widget=self.master
        self.Master_Configure(dummy_event,1)

    def menu_View_Recalculate(self):
        pass

    def menu_Help_About(self):
        about = "dmap2gcode by Scorch.\n"
        about = about + "\163\143\157\162\143\150\100\163\143\157\162"
        about = about + "\143\150\167\157\162\153\163\056\143\157\155\n"
        about = about + "http://www.scorchworks.com/"
        message_box("About dmap2gcode",about)

    def KEY_ESC(self, event):
        pass #A stop calculation command may go here

    def KEY_F1(self, event):
        self.menu_Help_About()

    def KEY_F2(self, event):
        self.GEN_Settings_Window()

    def KEY_F3(self, event):
        self.ROUGH_Settings_Window()

    def KEY_F4(self, event):
        pass

    def KEY_F5(self, event):
        self.menu_View_Refresh()

    def KEY_CTRL_G(self, event):
        self.CopyClipboard_GCode()

    def bindConfigure(self, event):
        if not self.initComplete:
            self.initComplete = 1
            self.menu_Mode_Change()

    def Master_Configure(self, event, update=0):
        if event.widget != self.master:
            return
        x = int(self.master.winfo_x())
        y = int(self.master.winfo_y())
        w = int(self.master.winfo_width())
        h = int(self.master.winfo_height())
        if (self.x, self.y) == (-1,-1):
            self.x, self.y = x,y
        if abs(self.w-w)>10 or abs(self.h-h)>10 or update==1:
            ###################################################
            #  Form changed Size (resized) adjust as required #
            ###################################################
            self.w=w
            self.h=h

            if 0 == 0:                
                # Left Column #
                w_label=90
                w_entry=60
                w_units=35

                x_label_L=10
                x_entry_L=x_label_L+w_label+10
                x_units_L=x_entry_L+w_entry+5

                Yloc=6
                self.Label_font_prop.place(x=x_label_L, y=Yloc, width=w_label*2, height=21)
                Yloc=Yloc+24
                self.Label_Yscale.place(x=x_label_L, y=Yloc, width=w_label, height=21)
                self.Label_Yscale_u.place(x=x_units_L, y=Yloc, width=w_units, height=21)
                self.Entry_Yscale.place(x=x_entry_L, y=Yloc, width=w_entry, height=23)

                Yloc=Yloc+24
                self.Label_Yscale2.place(x=x_label_L, y=Yloc, width=w_label, height=21)
                self.Label_Yscale2_u.place(x=x_units_L, y=Yloc, width=w_units, height=21)
                self.Label_Yscale2_val.place(x=x_entry_L, y=Yloc, width=w_entry, height=21)
                
                Yloc=Yloc+24
                self.Label_PixSize.place(x=x_label_L, y=Yloc, width=w_label, height=21)
                self.Label_PixSize_u.place(x=x_units_L, y=Yloc, width=w_units, height=21)
                self.Label_PixSize_val.place(x=x_entry_L, y=Yloc, width=w_entry, height=21)

                Yloc=Yloc+24+12
                self.separator1.place(x=x_label_L, y=Yloc,width=w_label+75+40, height=2)
                Yloc=Yloc+6
                self.Label_pos_orient.place(x=x_label_L, y=Yloc, width=w_label*2, height=21)

                Yloc=Yloc+24
                self.Label_Invert_Color_FALSE.place(x=x_label_L, y=Yloc, width=w_label, height=21)
                self.Radio_Invert_Color_FALSE.place(x=x_entry_L+20, y=Yloc, width=75, height=23)
                
                Yloc=Yloc+24
                #self.Label_Invert_Color_TRUE.place(x=x_label_L, y=Yloc, width=w_label, height=21)
                self.Radio_Invert_Color_TRUE.place(x=x_entry_L+20, y=Yloc, width=75, height=23)



                Yloc=Yloc+24
                self.Label_normalize.place(x=x_label_L, y=Yloc, width=w_label+20, height=21)
                self.Checkbutton_normalize.place(x=x_entry_L+20, y=Yloc, width=w_entry+20, height=23)

                Yloc=Yloc+24
                self.Label_Origin.place(x=x_label_L, y=Yloc, width=w_label, height=21)
                self.Origin_OptionMenu.place(x=x_entry_L, y=Yloc, width=w_entry+40, height=23)

                Yloc=Yloc+24+12
                self.separator2.place(x=x_label_L, y=Yloc,width=w_label+75+40, height=2)

                Yloc=Yloc+6
                self.Label_CutTop.place(x=x_label_L, y=Yloc, width=w_label+20, height=21)
                self.Checkbutton_CutTop.place(x=x_entry_L+20, y=Yloc, width=w_entry+20, height=23)
                
                Yloc=Yloc+24
                self.Label_Toptol.place(x=x_label_L, y=Yloc, width=w_label, height=21)
                self.Label_Toptol_u.place(x=x_units_L, y=Yloc, width=w_units, height=21)
                self.Entry_Toptol.place(x=x_entry_L, y=Yloc, width=w_entry, height=23)
                # End Left Column #

                # Start Right Column
                w_label=90
                w_entry=60
                w_units=35

                x_label_R=self.w - 220
                x_entry_R=x_label_R+w_label+10
                x_units_R=x_entry_R+w_entry+5

                Yloc=6
                self.Label_tool_opt.place(x=x_label_R, y=Yloc, width=w_label*2, height=21)

                Yloc=Yloc+24
                self.Label_ToolDIA.place(x=x_label_R,   y=Yloc, width=w_label, height=21)
                self.Label_ToolDIA_u.place(x=x_units_R, y=Yloc, width=w_units, height=21)
                self.Entry_ToolDIA.place(x=x_entry_R,   y=Yloc, width=w_entry, height=23)

                Yloc=Yloc+24
                self.Label_Tool.place(x=x_label_R, y=Yloc, width=w_label, height=21)
                self.Tool_OptionMenu.place(x=x_entry_R, y=Yloc, width=w_entry+40, height=23)

                Yloc=Yloc+24
                self.Label_Vangle.place(x=x_label_R, y=Yloc, width=w_label, height=21)
                self.Entry_Vangle.place(x=x_entry_R, y=Yloc, width=w_entry, height=23)
                
                Yloc=Yloc+24+12
                self.separator3.place(x=x_label_R, y=Yloc,width=w_label+75+40, height=2)

                Yloc=Yloc+6
                self.Label_gcode_opt.place(x=x_label_R, y=Yloc, width=w_label*2, height=21)

                Yloc=Yloc+24
                self.Label_Scanpat.place(x=x_label_R, y=Yloc, width=w_label, height=21)
                self.ScanPat_OptionMenu.place(x=x_entry_R, y=Yloc, width=w_entry+40, height=23)

                Yloc=Yloc+24
                self.Label_CutPerim.place(x=x_label_R, y=Yloc, width=w_label, height=21)
                self.Checkbutton_CutPerim.place(x=x_entry_R, y=Yloc, width=w_entry+40, height=23)
                
                Yloc=Yloc+24
                self.Label_Scandir.place(x=x_label_R, y=Yloc, width=w_label, height=21)
                self.ScanDir_OptionMenu.place(x=x_entry_R, y=Yloc, width=w_entry+40, height=23)
                
                Yloc=Yloc+24
                self.Entry_Feed.place(  x=x_entry_R, y=Yloc, width=w_entry, height=23)
                self.Label_Feed.place(  x=x_label_R, y=Yloc, width=w_label, height=21)
                self.Label_Feed_u.place(x=x_units_R, y=Yloc, width=w_units+15, height=21)

                Yloc=Yloc+24
                self.Label_p_feed.place(x=x_label_R,  y=Yloc, width=w_label,   height=21)
                self.Entry_p_feed.place(x=x_entry_R,  y=Yloc, width=w_entry,   height=23)
                self.Label_p_feed_u.place(x=x_units_R,y=Yloc, width=w_units+15,height=21)

                Yloc=Yloc+24
                self.Label_StepOver.place(x=x_label_R, y=Yloc, width=w_label, height=21)
                self.Label_StepOver_u.place(x=x_units_R, y=Yloc, width=w_units, height=21)
                self.Entry_StepOver.place(x=x_entry_R, y=Yloc, width=w_entry, height=23)

                Yloc=Yloc+24
                self.Entry_Zsafe.place(  x=x_entry_R, y=Yloc, width=w_entry, height=23)
                self.Label_Zsafe.place(  x=x_label_R, y=Yloc, width=w_label, height=21)
                self.Label_Zsafe_u.place(x=x_units_R, y=Yloc, width=w_units, height=21)


                Yloc=Yloc+24
                self.Label_Zcut.place(  x=x_label_R, y=Yloc, width=w_label, height=21)
                self.Label_Zcut_u.place(x=x_units_R, y=Yloc, width=w_units, height=21)
                self.Entry_Zcut.place(  x=x_entry_R, y=Yloc, width=w_entry, height=23)

                Yloc=Yloc+24+12
                self.separator4.place(x=x_label_R, y=Yloc,width=w_label+75+40, height=2)

                # Buttons etc.
                Yloc=Yloc+12
                self.Roughing_but.place(x=x_label_R, y=Yloc, width=90+75+40, height=30)
        
                # Buttons etc.
                Ybut=self.h-60
                self.Save_Button.place(x=12, y=Ybut, width=95, height=30)

                self.PreviewCanvas.configure( width = self.w-455, height = self.h-50 )
                self.PreviewCanvas_frame.place(x=220, y=10)

                self.Set_Input_States()
            self.Plot_Data()
            
    def Recalculate_RQD_Click(self, event):
        self.menu_View_Refresh()

    def Set_Input_States(self):
        if self.tool.get() != "V":
            self.Label_Vangle.configure(state="disabled")
            self.Entry_Vangle.configure(state="disabled")
        else:
            self.Label_Vangle.configure(state="normal")
            self.Entry_Vangle.configure(state="normal")

        if self.cuttop.get():
            self.Entry_Toptol.configure(state="disabled")
            self.Label_Toptol.configure(state="disabled")
            self.Label_Toptol_u.configure(state="disabled")
        else:
            self.Entry_Toptol.configure(state="normal")
            self.Label_Toptol.configure(state="normal")
            self.Label_Toptol_u.configure(state="normal")
            
    def Set_Input_States_Event(self,event):
        self.Set_Input_States()

    def Set_Input_States_GEN(self):
        if self.lace_bound.get() == "None":
            self.Label_ContAngle.configure(state="disabled")
            self.Entry_ContAngle.configure(state="disabled")
        else:
            self.Label_ContAngle.configure(state="normal")
            self.Entry_ContAngle.configure(state="normal")

        if ( self.scanpat.get().find("R") == -1) or \
           ( self.scanpat.get().find("C") == -1):
            self.Label_LaceBound.configure(state="disabled")
            self.LaceBound_OptionMenu.configure(state="disabled")
            self.Label_ContAngle.configure(state="disabled")
            self.Entry_ContAngle.configure(state="disabled")
        else:
            self.Label_LaceBound.configure(state="normal")
            self.LaceBound_OptionMenu.configure(state="normal")
            
    def Set_Input_States_GEN_Event(self,event):
        self.Set_Input_States_GEN()

    def Set_Input_States_ROUGH(self):
        if self.ROUGH_TOOL.get() != "V":
            self.ROUGH_Label_Vangle.configure(state="disabled")
            self.ROUGH_Entry_Vangle.configure(state="disabled")
        else:
            self.ROUGH_Label_Vangle.configure(state="normal")
            self.ROUGH_Entry_Vangle.configure(state="normal")
            
    def Set_Input_States_Event_ROUGH(self,event):
        self.Set_Input_States_ROUGH()
        
        
    ##########################################
    #        CANVAS PLOTTING STUFF           #
    ##########################################
    def Plot_Data(self):
        self.PreviewCanvas.delete(ALL)
        
        if (self.Check_All_Variables() > 0):
            return
        
        cszw = int(self.PreviewCanvas.cget("width"))
        cszh = int(self.PreviewCanvas.cget("height"))
        wc = float(cszw/2)
        hc = float(cszh/2)

        try:
            test = self.im.size
            self.SCALE = min( float(cszw-20)/float(self.wim), float(cszh-20)/float(self.him))
            if self.SCALE < 1:
                nw=int(self.SCALE*self.wim)
                nh=int(self.SCALE*self.him)
            else:
                nw = self.wim
                nh = self.him
                self.SCALE = 1
            self.ui_TKimage = ImageTk.PhotoImage(self.im.resize((nw,nh), Image.ANTIALIAS))
        except:
            self.SCALE = 1            

        self.canvas_image = self.PreviewCanvas.create_image(wc, \
                            hc, anchor=CENTER, image=self.ui_TKimage)

        midx = 0
        midy = 0
        minx = int(self.wim/2)
        miny = int(self.him/2)
        maxx = -minx
        maxy = -miny
        
        ##########################################
        #         ORIGIN LOCATING STUFF          #
        ##########################################
        CASE = str(self.origin.get())
        if     CASE == "Top-Left":
            x_zero = minx
            y_zero = maxy
        elif   CASE == "Top-Center":
            x_zero = midx
            y_zero = maxy
        elif   CASE == "Top-Right":
            x_zero = maxx
            y_zero = maxy
        elif   CASE == "Mid-Left":
            x_zero = minx
            y_zero = midy
        elif   CASE == "Mid-Center":
            x_zero = midx
            y_zero = midy
        elif   CASE == "Mid-Right":
            x_zero = maxx
            y_zero = midy
        elif   CASE == "Bot-Left":
            x_zero = minx
            y_zero = miny
        elif   CASE == "Bot-Center":
            x_zero = midx
            y_zero = miny
        elif   CASE == "Bot-Right":
            x_zero = maxx
            y_zero = miny
        else:          #"Default"
            x_zero = minx
            y_zero = miny    
        
        axis_length = int(self.wim/4)

        PlotScale =  self.SCALE
        axis_x1 =  cszw/2 + (-x_zero             ) * PlotScale
        axis_x2 =  cszw/2 + ( axis_length-x_zero ) * PlotScale
        axis_y1 =  cszh/2 - (-y_zero             ) * PlotScale
        axis_y2 =  cszh/2 - ( axis_length-y_zero ) * PlotScale
        
        for seg in self.segID:
            self.PreviewCanvas.delete(seg)
        self.segID = []
        if self.show_axis.get() == True:
            # Plot coordinate system origin
            self.segID.append( self.PreviewCanvas.create_line(axis_x1,axis_y1,\
                                                                  axis_x2,axis_y1,\
                                                                  fill = 'red'  , width = 2))
            self.segID.append( self.PreviewCanvas.create_line(axis_x1,axis_y1,\
                                                                  axis_x1,axis_y2,\
                                                                  fill = 'green', width = 2))

    ################################################################################
    #                         General Settings Window                              #
    ################################################################################
    def GEN_Settings_Window(self):
        gen_settings = Toplevel(width=560, height=360)
        gen_settings.grab_set() # Use grab_set to prevent user input in the main window during calculations
        gen_settings.resizable(0,0)
        gen_settings.title('Settings')
        gen_settings.iconname("Settings")

        try: #Attempt to create temporary icon bitmap file
            f = open("dmap2gcode_icon",'w')
            f.write("#define dmap2gcode_icon_width 16\n")
            f.write("#define dmap2gcode_icon_height 16\n")
            f.write("static unsigned char dmap2gcode_icon_bits[] = {\n")
            f.write("   0x3f, 0xfc, 0x1f, 0xf8, 0xcf, 0xf3, 0x6f, 0xe4, 0x6f, 0xed, 0xcf, 0xe5,\n")
            f.write("   0x1f, 0xf4, 0xfb, 0xf3, 0x73, 0x98, 0x47, 0xce, 0x0f, 0xe0, 0x3f, 0xf8,\n")
            f.write("   0x7f, 0xfe, 0x3f, 0xfc, 0x9f, 0xf9, 0xcf, 0xf3 };\n")
            f.close()
            gen_settings.iconbitmap("@dmap2gcode_icon")
            os.remove("dmap2gcode_icon")
        except:
            pass

        D_Yloc  = 6
        D_dY = 24
        xd_label_L = 12

        w_label=110
        w_entry=60
        w_units=35
        xd_entry_L=xd_label_L+w_label+10
        xd_units_L=xd_entry_L+w_entry+5

        #Radio Button
        D_Yloc=D_Yloc+D_dY
        self.Label_Units = Label(gen_settings,text="Units")
        self.Label_Units.place(x=xd_label_L, y=D_Yloc, width=113, height=21)
        self.Radio_Units_IN = Radiobutton(gen_settings,text="inch", value="in",
                                         width="100", anchor=W)
        self.Radio_Units_IN.place(x=w_label+22, y=D_Yloc, width=75, height=23)
        self.Radio_Units_IN.configure(variable=self.units, command=self.Entry_units_var_Callback )
        self.Radio_Units_MM = Radiobutton(gen_settings,text="mm", value="mm",
                                         width="100", anchor=W)
        self.Radio_Units_MM.place(x=w_label+110, y=D_Yloc, width=75, height=23)
        self.Radio_Units_MM.configure(variable=self.units, command=self.Entry_units_var_Callback )

        D_Yloc=D_Yloc+D_dY
        self.Label_Tolerance = Label(gen_settings,text="tolerance")
        self.Label_Tolerance.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Label_Tolerance_u = Label(gen_settings,textvariable=self.units, anchor=W)
        self.Label_Tolerance_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.Entry_Tolerance = Entry(gen_settings,width="15")
        self.Entry_Tolerance.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_Tolerance.configure(textvariable=self.tolerance)
        self.tolerance.trace_variable("w", self.Entry_Tolerance_Callback)
        self.entry_set(self.Entry_Tolerance,self.Entry_Tolerance_Check(),2)

        D_Yloc=D_Yloc+D_dY
        self.Label_Gpre = Label(gen_settings,text="G Code Header")
        self.Label_Gpre.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Entry_Gpre = Entry(gen_settings,width="15")
        self.Entry_Gpre.place(x=xd_entry_L, y=D_Yloc, width=300, height=23)
        self.Entry_Gpre.configure(textvariable=self.gpre)

        D_Yloc=D_Yloc+D_dY
        self.Label_Gpost = Label(gen_settings,text="G Code Postscript")
        self.Label_Gpost.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Entry_Gpost = Entry(gen_settings)
        self.Entry_Gpost.place(x=xd_entry_L, y=D_Yloc, width=300, height=23)
        self.Entry_Gpost.configure(textvariable=self.gpost)
        
        D_Yloc=D_Yloc+D_dY
        self.Label_LaceBound = Label(gen_settings,text="Lace Bounding")
        self.Label_LaceBound.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.LaceBound_OptionMenu = OptionMenu(gen_settings, self.lace_bound, "None","Secondary","Full",\
                                               command=self.Set_Input_States_GEN_Event)
        self.LaceBound_OptionMenu.place(x=xd_entry_L, y=D_Yloc, width=w_entry+40, height=23)

        D_Yloc=D_Yloc+D_dY
        self.Label_ContAngle = Label(gen_settings,text="LB Contact Angle")
        self.Label_ContAngle.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Label_ContAngle_u = Label(gen_settings,text="deg", anchor=W)
        self.Label_ContAngle_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.Entry_ContAngle = Entry(gen_settings,width="15")
        self.Entry_ContAngle.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_ContAngle.configure(textvariable=self.cangle)
        self.cangle.trace_variable("w", self.Entry_ContAngle_Callback)
        self.entry_set(self.Entry_ContAngle,self.Entry_ContAngle_Check(),2)

        #Radio Button
        D_Yloc=D_Yloc+D_dY
        self.Label_SplitStep = Label(gen_settings,text="Offset Stepover")
        self.Label_SplitStep.place(x=xd_label_L, y=D_Yloc, width=113, height=21)


        self.Radio_SplitStep_N = Radiobutton(gen_settings,text="None", value="0",
                                         width="100", anchor=W)
        self.Radio_SplitStep_N.place(x=w_label+22, y=D_Yloc, width=75, height=23)
        self.Radio_SplitStep_N.configure(variable=self.splitstep )

        self.Radio_SplitStep_H = Radiobutton(gen_settings,text="1/2 Step", value="0.5",
                                         width="100", anchor=W)
        self.Radio_SplitStep_H.place(x=w_label+110, y=D_Yloc, width=75, height=23)
        self.Radio_SplitStep_H.configure(variable=self.splitstep )

        self.Radio_SplitStep_Q = Radiobutton(gen_settings,text="1/4 Step", value="0.25",
                                         width="100", anchor=W)
        self.Radio_SplitStep_Q.place(x=w_label+198, y=D_Yloc, width=75, height=23)
        self.Radio_SplitStep_Q.configure(variable=self.splitstep )



        #Radio Button
        D_Yloc=D_Yloc+D_dY
        self.Label_PlungeType = Label(gen_settings,text="Plunge Type")
        self.Label_PlungeType.place(x=xd_label_L, y=D_Yloc, width=113, height=21)
        self.Radio_PlungeType_S = Radiobutton(gen_settings,text="Vertical", value="simple",
                                         width="100", anchor=W)
        self.Radio_PlungeType_S.place(x=w_label+22, y=D_Yloc, width=75, height=23)
        self.Radio_PlungeType_S.configure(variable=self.plungetype )
        self.Radio_PlungeType_A = Radiobutton(gen_settings,text="Arc", value="arc",
                                         width="100", anchor=W)
        self.Radio_PlungeType_A.place(x=w_label+110, y=D_Yloc, width=75, height=23)
        self.Radio_PlungeType_A.configure(variable=self.plungetype )

        D_Yloc=D_Yloc+D_dY
        self.Label_Disable_Arcs = Label(gen_settings,text="Disable G-Code Arcs")
        self.Label_Disable_Arcs.place(x=xd_label_L, y=D_Yloc, width=113, height=21)
        self.Checkbutton_Disable_Arcs = Checkbutton(gen_settings,text=" ", \
                                              anchor=W, command=self.Set_Input_States)
        self.Checkbutton_Disable_Arcs.place(x=w_label+22, y=D_Yloc, width=75, height=23)
        
        self.Label_Disable_Arcs.place(x=xd_label_L, y=D_Yloc, width=113, height=21)
        self.Checkbutton_Disable_Arcs.configure(variable=self.disable_arcs)
        
        ## Buttons ##
        gen_settings.update_idletasks()
        Ybut=int(gen_settings.winfo_height())-30
        Xbut=int(gen_settings.winfo_width()/2)

        self.GEN_Close = Button(gen_settings,text="Close",command=self.Close_Current_Window_Click)
        self.GEN_Close.place(x=Xbut, y=Ybut, width=130, height=30, anchor="center")

        self.Set_Input_States_GEN()

    ################################################################################
    #                        Roughing Settings Window                              #
    ################################################################################
    def ROUGH_Settings_Window(self):
        rough_settings = Toplevel(width=350, height=460)
        rough_settings.grab_set() # Use grab_set to prevent user input in the main window during calculations
        rough_settings.resizable(0,0)
        rough_settings.title('Roughing Settings')
        rough_settings.iconname("Roughing")

        try: #Attempt to create temporary icon bitmap file
            f = open("dmap2gcode_icon",'w')
            f.write("#define dmap2gcode_icon_width 16\n")
            f.write("#define dmap2gcode_icon_height 16\n")
            f.write("static unsigned char dmap2gcode_icon_bits[] = {\n")
            f.write("   0x3f, 0xfc, 0x1f, 0xf8, 0xcf, 0xf3, 0x6f, 0xe4, 0x6f, 0xed, 0xcf, 0xe5,\n")
            f.write("   0x1f, 0xf4, 0xfb, 0xf3, 0x73, 0x98, 0x47, 0xce, 0x0f, 0xe0, 0x3f, 0xf8,\n")
            f.write("   0x7f, 0xfe, 0x3f, 0xfc, 0x9f, 0xf9, 0xcf, 0xf3 };\n")
            f.close()
            rough_settings.iconbitmap("@dmap2gcode_icon")
            os.remove("dmap2gcode_icon")
        except:
            pass

        self.ROUGH_separator1 = Frame(rough_settings, height=2, bd=1, relief=SUNKEN)
        self.ROUGH_separator2 = Frame(rough_settings, height=2, bd=1, relief=SUNKEN)
        self.ROUGH_separator3 = Frame(rough_settings, height=2, bd=1, relief=SUNKEN)
        self.ROUGH_separator4 = Frame(rough_settings, height=2, bd=1, relief=SUNKEN)

        D_Yloc  = 6
        D_dY = 24
        xd_label_L = 12

        w_label=170
        w_entry=60
        w_units=35
        xd_entry_L=xd_label_L+w_label+10
        xd_units_L=xd_entry_L+w_entry+5
        
        ######################
        # Roughing setttings #
        ######################
        # Start Right Column
        D_Yloc=6
        self.ROUGH_Label_tool_opt = Label(rough_settings,text="Roughing Tool Properties:", anchor=W)
        
        self.ROUGH_Label_Tool      = Label(rough_settings,text="Roughing Tool End", anchor=CENTER )
        self.ROUGH_Tool_OptionMenu       = OptionMenu(rough_settings, self.ROUGH_TOOL, "Ball","V","Flat",\
                                               command=self.Set_Input_States_Event_ROUGH)
        self.ROUGH_Label_tool_opt.place(x=xd_label_L, y=D_Yloc, width=w_label*2, height=21)

        D_Yloc=D_Yloc+24
        self.ROUGH_Label_ToolDIA = Label(rough_settings,text="Roughing Tool DIA")
        self.ROUGH_Label_ToolDIA_u = Label(rough_settings,textvariable=self.units, anchor=W)
        self.ROUGH_Entry_ToolDIA = Entry(rough_settings,width="15")
        
        self.ROUGH_Entry_ToolDIA.configure(textvariable=self.ROUGH_DIA)
        self.ROUGH_Entry_ToolDIA.bind('<Return>', self.Recalculate_Click)
        self.ROUGH_DIA.trace_variable("w", self.ROUGH_Entry_ToolDIA_Callback)
        self.ROUGH_Label_ToolDIA.place(x=xd_label_L,   y=D_Yloc, width=w_label, height=21)
        self.ROUGH_Label_ToolDIA_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.ROUGH_Entry_ToolDIA.place(x=xd_entry_L,   y=D_Yloc, width=w_entry, height=23)

        D_Yloc=D_Yloc+24
        self.ROUGH_Label_Tool.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.ROUGH_Tool_OptionMenu.place(x=xd_entry_L, y=D_Yloc, width=w_entry+40, height=23)

        D_Yloc=D_Yloc+24
        self.ROUGH_Label_Vangle = Label(rough_settings,text="Roughing V-Bit Angle", anchor=CENTER )
        self.ROUGH_Entry_Vangle = Entry(rough_settings,width="15")
        self.ROUGH_Entry_Vangle.configure(textvariable=self.ROUGH_V_ANGLE)
        self.ROUGH_Entry_Vangle.bind('<Return>', self.Recalculate_Click)
        self.ROUGH_V_ANGLE.trace_variable("w", self.ROUGH_Entry_Vangle_Callback)
        self.ROUGH_Label_Vangle.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.ROUGH_Entry_Vangle.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        
        D_Yloc=D_Yloc+24+12
        self.ROUGH_separator3.place(x=xd_label_L, y=D_Yloc,width=w_label+75+40, height=2)

        D_Yloc=D_Yloc+6        
        self.ROUGH_Label_gcode_opt = Label(rough_settings,text="Roughing Gcode Properties:", anchor=W)
        self.ROUGH_Label_gcode_opt.place(x=xd_label_L, y=D_Yloc, width=w_label*2, height=21)

        D_Yloc=D_Yloc+24
        self.ROUGH_Label_Scanpat      = Label(rough_settings,text="Roughing Scan Pattern", anchor=CENTER )
        self.ROUGH_ScanPat_OptionMenu = OptionMenu(rough_settings, self.ROUGH_SCANPAT, "Rows","Columns",\
                                           "R then C", "C then R")
        self.ROUGH_Label_Scanpat.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.ROUGH_ScanPat_OptionMenu.place(x=xd_entry_L, y=D_Yloc, width=w_entry+40, height=23)

        D_Yloc=D_Yloc+24
        self.ROUGH_Label_Scandir      = Label(rough_settings,text="Roughing Scan Direction", anchor=CENTER )
        self.ROUGH_ScanDir_OptionMenu = OptionMenu(rough_settings, self.ROUGH_SCANDIR, "Alternating", "Positive",
                                            "Negative", "Up Mill", "Down Mill")
        self.ROUGH_Label_Scandir.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.ROUGH_ScanDir_OptionMenu.place(x=xd_entry_L, y=D_Yloc, width=w_entry+40, height=23)

        D_Yloc=D_Yloc+24
        self.ROUGH_Label_Feed = Label(rough_settings,text="Roughing Feed Rate")
        self.ROUGH_Label_Feed_u = Label(rough_settings,textvariable=self.funits, anchor=W)
        self.ROUGH_Entry_Feed = Entry(rough_settings,width="15")
        self.ROUGH_Entry_Feed.configure(textvariable=self.ROUGH_R_FEED)
        self.ROUGH_Entry_Feed.bind('<Return>', self.Recalculate_Click)
        self.ROUGH_R_FEED.trace_variable("w", self.ROUGH_Entry_Feed_Callback)
        self.ROUGH_Entry_Feed.place(  x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.ROUGH_Label_Feed.place(  x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.ROUGH_Label_Feed_u.place(x=xd_units_L, y=D_Yloc, width=w_units+15, height=21)

        D_Yloc=D_Yloc+24
        self.ROUGH_Label_p_feed = Label(rough_settings,text="Roughing Plunge Feed", anchor=CENTER )
        self.ROUGH_Label_p_feed_u = Label(rough_settings,textvariable=self.funits, anchor=W)
        self.ROUGH_Entry_p_feed = Entry(rough_settings,width="15")
        self.ROUGH_Entry_p_feed.configure(textvariable=self.ROUGH_P_FEED)
        self.ROUGH_Entry_p_feed.bind('<Return>', self.Recalculate_Click)
        self.ROUGH_P_FEED.trace_variable("w", self.Entry_p_feed_Callback)
        self.ROUGH_Label_p_feed.place(x=xd_label_L,  y=D_Yloc, width=w_label,   height=21)
        self.ROUGH_Entry_p_feed.place(x=xd_entry_L,  y=D_Yloc, width=w_entry,   height=23)
        self.ROUGH_Label_p_feed_u.place(x=xd_units_L,y=D_Yloc, width=w_units+15,height=21)

        D_Yloc=D_Yloc+24
        self.ROUGH_Label_StepOver = Label(rough_settings,text="Roughing Stepover", anchor=CENTER )
        self.ROUGH_Label_StepOver_u = Label(rough_settings,textvariable=self.units, anchor=W)
        self.ROUGH_Entry_StepOver = Entry(rough_settings,width="15")
        self.ROUGH_Entry_StepOver.configure(textvariable=self.ROUGH_STEPOVER)
        self.ROUGH_Entry_StepOver.bind('<Return>', self.Recalculate_Click)
        self.ROUGH_STEPOVER.trace_variable("w", self.ROUGH_Entry_StepOver_Callback)
        self.ROUGH_Label_StepOver.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.ROUGH_Label_StepOver_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.ROUGH_Entry_StepOver.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)

        D_Yloc=D_Yloc+24+12
        self.ROUGH_separator4.place(x=xd_label_L, y=D_Yloc,width=w_label+75+40, height=2)

        D_Yloc=D_Yloc+6
        self.ROUGH_Label_roughing_props = Label(rough_settings,text="Roughing Properties:",anchor=W)        
        self.ROUGH_Label_roughing_props.place(x=xd_label_L, y=D_Yloc, width=w_label*2, height=21)

        D_Yloc=D_Yloc+24
        self.ROUGH_Label_Roffset = Label(rough_settings,text="Roughing Offset", anchor=CENTER )
        self.ROUGH_Label_Roffset_u = Label(rough_settings,textvariable=self.units, anchor=W)
        self.ROUGH_Entry_Roffset = Entry(rough_settings,width="15")
        self.ROUGH_Entry_Roffset.configure(textvariable=self.ROUGH_OFFSET)
        self.ROUGH_Entry_Roffset.bind('<Return>', self.Recalculate_Click)
        self.ROUGH_OFFSET.trace_variable("w", self.ROUGH_Entry_Roffset_Callback)
        self.ROUGH_Label_Roffset.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.ROUGH_Label_Roffset_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.ROUGH_Entry_Roffset.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        
        D_Yloc=D_Yloc+24
        self.ROUGH_Label_Rdepth = Label(rough_settings,text="Roughing Depth/Pass", anchor=CENTER )
        self.ROUGH_Label_Rdepth_u = Label(rough_settings,textvariable=self.units, anchor=W)
        self.ROUGH_Entry_Rdepth = Entry(rough_settings,width="15")
        self.ROUGH_Entry_Rdepth.configure(textvariable=self.ROUGH_DEPTH_PP)
        self.ROUGH_Entry_Rdepth.bind('<Return>', self.Recalculate_Click)
        self.ROUGH_DEPTH_PP.trace_variable("w", self.ROUGH_Entry_Rdepth_Callback)
        self.ROUGH_Label_Rdepth.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.ROUGH_Label_Rdepth_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.ROUGH_Entry_Rdepth.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        
        ##########################
        # End Roughing Setttings #
        ##########################

        ## Buttons ##
        rough_settings.update_idletasks()
        Ybut=int(rough_settings.winfo_height())-30
        Xbut=int(rough_settings.winfo_width()/2)

        self.ROUGH_Save = Button(rough_settings,text="Save\nRoughing G-Code",\
                                 command=self.menu_File_Save_G_Code_File_Rough)
        self.ROUGH_Save.place(x=Xbut, y=Ybut, width=130, height=40, anchor="e")
        
        self.ROUGH_Close = Button(rough_settings,text="Close",\
                                  command=self.Close_Current_Window_Click)
        self.ROUGH_Close.place(x=Xbut, y=Ybut, width=130, height=40, anchor="w")
        
        self.Set_Input_States_ROUGH()
        
################################################################################
#             Author.py                                                        #
#             A component of emc2                                              #
################################################################################

# Compute the 3D distance from the line segment l1..l2 to the point p.
# (Those are lower case L1 and L2)
def dist_lseg(l1, l2, p):
    x0, y0, z0 = l1
    xa, ya, za = l2
    xi, yi, zi = p

    dx = xa-x0
    dy = ya-y0
    dz = za-z0
    d2 = dx*dx + dy*dy + dz*dz

    if d2 == 0: return 0

    t = (dx * (xi-x0) + dy * (yi-y0) + dz * (zi-z0)) / d2
    if t < 0: t = 0
    if t > 1: t = 1
    dist2 = (xi - x0 - t*dx)**2 + (yi - y0 - t*dy)**2 + (zi - z0 - t*dz)**2

    return dist2 ** .5

def rad1(x1,y1,x2,y2,x3,y3):
    x12 = x1-x2
    y12 = y1-y2
    x23 = x2-x3
    y23 = y2-y3
    x31 = x3-x1
    y31 = y3-y1

    den = abs(x12 * y23 - x23 * y12)
    if abs(den) < 1e-5: return MAXINT
    return hypot(float(x12), float(y12)) * hypot(float(x23), float(y23)) * hypot(float(x31), float(y31)) / 2 / den

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __str__(self): return "<%f,%f>" % (self.x, self.y)
    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)
    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)
    def __mul__(self, other):
        return Point(self.x * other, self.y * other)
    __rmul__ = __mul__
    def cross(self, other):
        return self.x * other.y - self.y * other.x
    def dot(self, other):
        return self.x * other.x + self.y * other.y
    def mag(self):
        return hypot(self.x, self.y)
    def mag2(self):
        return self.x**2 + self.y**2

def cent1(x1,y1,x2,y2,x3,y3):
    P1 = Point(x1,y1)
    P2 = Point(x2,y2)
    P3 = Point(x3,y3)

    den = abs((P1-P2).cross(P2-P3))
    if abs(den) < 1e-5: return MAXINT, MAXINT

    alpha = (P2-P3).mag2() * (P1-P2).dot(P1-P3) / 2 / den / den
    beta  = (P1-P3).mag2() * (P2-P1).dot(P2-P3) / 2 / den / den
    gamma = (P1-P2).mag2() * (P3-P1).dot(P3-P2) / 2 / den / den

    Pc = alpha * P1 + beta * P2 + gamma * P3
    return Pc.x, Pc.y

def arc_center(plane, p1, p2, p3):
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    x3, y3, z3 = p3

    if plane == 17: return cent1(x1,y1,x2,y2,x3,y3)
    if plane == 18: return cent1(x1,z1,x2,z2,x3,z3)
    if plane == 19: return cent1(y1,z1,y2,z2,y3,z3)

def arc_rad(plane, P1, P2, P3):
    if plane is None: return MAXINT

    x1, y1, z1 = P1
    x2, y2, z2 = P2
    x3, y3, z3 = P3

    if plane == 17: return rad1(x1,y1,x2,y2,x3,y3)
    if plane == 18: return rad1(x1,z1,x2,z2,x3,z3)
    if plane == 19: return rad1(y1,z1,y2,z2,y3,z3)
    return None, 0

def get_pts(plane, x,y,z):
    if plane == 17: return x,y
    if plane == 18: return x,z
    if plane == 19: return y,z

def one_quadrant(plane, c, p1, p2, p3):
    xc, yc = c
    x1, y1 = get_pts(plane, p1[0],p1[1],p1[2])
    x2, y2 = get_pts(plane, p2[0],p2[1],p2[2])
    x3, y3 = get_pts(plane, p3[0],p3[1],p3[2])

    def sign(x):
        if abs(x) < 1e-5: return 0
        if x < 0: return -1
        return 1

    signs = set((
        (sign(x1-xc),sign(y1-yc)),
        (sign(x2-xc),sign(y2-yc)),
        (sign(x3-xc),sign(y3-yc))
    ))

    if len(signs) == 1: return True

    if (1,1) in signs:
        signs.discard((1,0))
        signs.discard((0,1))
    if (1,-1) in signs:
        signs.discard((1,0))
        signs.discard((0,-1))
    if (-1,1) in signs:
        signs.discard((-1,0))
        signs.discard((0,1))
    if (-1,-1) in signs:
        signs.discard((-1,0))
        signs.discard((0,-1))

    if len(signs) == 1: return True

def arc_dir(plane, c, p1, p2, p3):
    xc, yc = c
    x1, y1 = get_pts(plane, p1[0],p1[1],p1[2])
    x2, y2 = get_pts(plane, p2[0],p2[1],p2[2])
    x3, y3 = get_pts(plane, p3[0],p3[1],p3[2])

    theta_start = atan2(y1-yc, x1-xc)
    theta_mid = atan2(y2-yc, x2-xc)
    theta_end = atan2(y3-yc, x3-xc)

    if theta_mid < theta_start:
        theta_mid = theta_mid + 2 * pi
    while theta_end < theta_mid:
        theta_end = theta_end + 2 * pi

    return theta_end < 2 * pi

def arc_fmt(plane, c1, c2, p1):
    x, y, z = p1
    if plane == 17: return "I%.4f J%.4f" % (c1-x, c2-y)
    if plane == 18: return "I%.4f K%.4f" % (c1-x, c2-z)
    if plane == 19: return "J%.4f K%.4f" % (c1-y, c2-z)

# Perform Douglas-Peucker simplification on the path 'st' with the specified
# tolerance.  The '_first' argument is for internal use only.
#
# The Douglas-Peucker simplification algorithm finds a subset of the input points
# whose path is never more than 'tolerance' away from the original input path.
#
# If 'plane' is specified as 17, 18, or 19, it may find helical arcs in the given
# plane in addition to lines.  Note that if there is movement in the plane
# perpendicular to the arc, it will be distorted, so 'plane' should usually
# be specified only when there is only movement on 2 axes
def douglas(st, tolerance=.001, plane=None, _first=True):
    if len(st) == 1:
        yield "G1", st[0], None
        return

    l1 = st[0]
    l2 = st[-1]

    worst_dist = 0
    worst = 0
    min_rad = MAXINT
    max_arc = -1

    ps = st[0]
    pe = st[-1]

    for i, p in enumerate(st):
        if p is l1 or p is l2: continue
        dist = dist_lseg(l1, l2, p)
        if dist > worst_dist:
            worst = i
            worst_dist = dist
            rad = arc_rad(plane, ps, p, pe)
            if rad < min_rad:
                max_arc = i
                min_rad = rad

    worst_arc_dist = 0
    if min_rad != MAXINT:
        c1, c2 = arc_center(plane, ps, st[max_arc], pe)
        lx, ly, lz = st[0]
        if one_quadrant(plane, (c1, c2), ps, st[max_arc], pe):
            for i, (x,y,z) in enumerate(st):
                if plane == 17: dist = abs(hypot(c1-x, c2-y) - min_rad)
                elif plane == 18: dist = abs(hypot(c1-x, c2-z) - min_rad)
                elif plane == 19: dist = abs(hypot(c1-y, c2-z) - min_rad)
                else: dist = MAXINT
                if dist > worst_arc_dist: worst_arc_dist = dist

                mx = (x+lx)/2
                my = (y+ly)/2
                mz = (z+lz)/2
                if plane == 17: dist = abs(hypot(c1-mx, c2-my) - min_rad)
                elif plane == 18: dist = abs(hypot(c1-mx, c2-mz) - min_rad)
                elif plane == 19: dist = abs(hypot(c1-my, c2-mz) - min_rad)
                else: dist = MAXINT
                lx, ly, lz = x, y, z
        else:
            worst_arc_dist = MAXINT
    else:
        worst_arc_dist = MAXINT

    if worst_arc_dist < tolerance and worst_arc_dist < worst_dist:
        ccw = arc_dir(plane, (c1, c2), ps, st[max_arc], pe)
        if plane == 18: ccw = not ccw
        yield "G1", ps, None
        if ccw:
            yield "G3", st[-1], arc_fmt(plane, c1, c2, ps)
        else:
            yield "G2", st[-1], arc_fmt(plane, c1, c2, ps)
    elif worst_dist > tolerance:
        if _first: yield "G1", st[0], None
        for i in douglas(st[:worst+1], tolerance, plane, False):
            yield i
        yield "G1", st[worst], None
        for i in douglas(st[worst:], tolerance, plane, False):
            yield i
        if _first: yield "G1", st[-1], None
    else:
        if _first: yield "G1", st[0], None
        if _first: yield "G1", st[-1], None

# For creating rs274ngc files
class Gcode:
    def __init__(self, homeheight = 1.5, safetyheight = 0.04,
                 tolerance=0.001, units="G20", header="", postscript="",
                 target=lambda s: sys.stdout.write(s + "\n"),
                 disable_arcs = False):
        self.lastx = self.lasty = self.lastz = self.lasta = None
        self.lastgcode = self.lastfeed = None
        self.homeheight = homeheight
        self.safetyheight = self.lastz = safetyheight
        self.tolerance = tolerance
        self.units = units
        self.cuts = []
        self.write = target
        self.time = 0
        self.plane = None
        self.header = header
        self.postscript = postscript
        self.disable_arcs = disable_arcs

    def set_plane(self, p):
        if (not self.disable_arcs):
            assert p in (17,18,19)
            if p != self.plane:
                self.plane = p
                self.write("G%d" % p)
        
    # This function moves to the safety height, sets many modal codes to default
    # values, turns the spindle on at 3000RPM
    def begin(self):
        if self.header=="":
            self.write("G17 G90 M3 S3000 G40 G94")
        else:
            for line in self.header:
                self.write(line)
        self.write(self.units)
        if not self.disable_arcs:
            self.write("G91.1")

        #self.safety()
        #self.rapid(z=self.safetyheight)
        self.write("G0 Z%.4f" % (self.safetyheight))
        #["G17 G40","G80 G90 G94 G91.1"]
        
    # If any 'cut' moves are stored up, send them to the simplification algorithm
    # and actually output them.
    #
    # This function is usually used internally (e.g., when changing from a cut
    # to a rapid) but can be called manually as well.  For instance, when
    # a contouring program reaches the end of a row, it may be desirable to enforce
    # that the last 'cut' coordinate is actually in the output file, and it may
    # give better performance because this means that the simplification algorithm
    # will examine fewer points per run.
    def flush(self):
        if not self.cuts: return
        for move, (x, y, z), cent in douglas(self.cuts, self.tolerance, self.plane):
            if cent:
                self.write("%s X%.4f Y%.4f Z%.4f %s" % (move, x, y, z, cent))
                self.lastgcode = None
                self.lastx = x
                self.lasty = y
                self.lastz = z
            else:
                self.move_common(x, y, z, gcode="G1")
        self.cuts = []

    def end(self):
        #"""End the program"""
        self.flush()
        self.safety()
        if self.postscript=="":
            self.write("M2")
        else:
            self.write(self.postscript)

    #    """\
    #Set exact path mode.  Note that unless self.tolerance is set to zero,
    #the simplification algorithm may still skip over specified points."""
    def exactpath(self):
        self.write("G61")

    # Set continuous mode.
    def continuous(self, tolerance=0.0):
    
        if tolerance > 0.0:
            self.write("G64 P%.4f" % tolerance)
        else:
            self.write("G64")

    def rapid(self, x=None, y=None, z=None, a=None):
        #"Perform a rapid move to the specified coordinates"
        self.flush()
        self.move_common(x, y, z, a, "G0")

    def move_common(self, x=None, y=None, z=None, a=None, gcode="G0"):
        #"An internal function used for G0 and G1 moves"
        gcodestring = xstring = ystring = zstring = astring = ""
        if x == None: x = self.lastx
        if y == None: y = self.lasty
        if z == None: z = self.lastz
        if a == None: a = self.lasta
        if x != self.lastx:
                xstring = " X%.4f" % (x)
                self.lastx = x
        if y != self.lasty:
                ystring = " Y%.4f" % (y)
                self.lasty = y
        if z != self.lastz:
                zstring = " Z%.4f" % (z)
                self.lastz = z
        if a != self.lasta:
                astring = " A%.4f" % (a)
                self.lasta = a
        if xstring == ystring == zstring == astring == "":
            return
        if gcode != self.lastgcode:
                gcodestring = gcode
                self.lastgcode = gcode
        cmd = "".join([gcodestring, xstring, ystring, zstring, astring])
        if cmd:
            self.write(cmd)

    def set_feed(self, feed):
        #"Set the feed rate to the given value"
        self.flush()
        self.write("F%.4f" % feed)

    def cut(self, x=None, y=None, z=None):
        #"Perform a cutting move at the specified feed rate to the specified coordinates"
        if self.cuts:
            lastx, lasty, lastz = self.cuts[-1]
        else:
            lastx, lasty, lastz = self.lastx, self.lasty, self.lastz
        if x is None: x = lastx
        if y is None: y = lasty
        if z is None: z = lastz
        self.cuts.append([x,y,z])

    def home(self):
        #"Go to the 'home' height at rapid speed"
        self.flush()
        self.rapid(z=self.homeheight)

    def safety(self):
        #"Go to the 'safety' height at rapid speed"
        self.flush()
        self.rapid(z=self.safetyheight)


################################################################################
#             image-to-gcode                                                   #
#                                                                              #
################################################################################

epsilon = 1e-5

def ball_tool(r,rad):
    s = -sqrt(rad**2-r**2)
    return s

def endmill(r,dia, rough_offset=0.0):
    return 0

def vee_common(angle, rough_offset=0.0):
    slope = tan(pi/2.0 - (angle / 2.0) * pi / 180.0)
    def f(r, dia):
        return r * slope
    return f

def make_tool_shape(f, wdia, resp, rough_offset=0.0):
    # resp is pixel size
    res = 1. / resp
    wrad = wdia/2.0 + rough_offset
    rad = int(ceil((wrad-resp/2.0)*res))
    if rad < 1: rad = 1
    dia = 2*rad+1
    
    hdia = rad
    l = []
    for x in range(dia):
        for y in range(dia):
            r = hypot(x-hdia, y-hdia) * resp
            if r < wrad:
                z = f(r, wrad)
                l.append(z)
    #######################
    TOOL = Image_Matrix(dia,dia)
    l = []
    temp = []
    for x in range(dia):
        temp.append([])
        for y in range(dia):
            r = hypot(x-hdia, y-hdia) * resp
            if r < wrad:
                z = f(r, wrad)
                l.append(z)
                temp[x].append(float(z))
            else:
                temp[x].append(1e100000)
    TOOL.From_List(temp)
    TOOL.minus(TOOL.min()+rough_offset)
    return TOOL

def amax(seq):
    res = 0
    for i in seq:
        if abs(i) > abs(res): res = i
    return res

def group_by_sign(seq, slop=sin(pi/18), key=lambda x:x):
    sign = None
    subseq = []
    for i in seq:
        ki = key(i)
        if sign is None:
            subseq.append(i)
            if ki != 0:
                sign = ki / abs(ki)
        else:
            subseq.append(i)
            if sign * ki < -slop:
                sign = ki / abs(ki)
                yield subseq
                subseq = [i]
    if subseq: yield subseq

class Convert_Scan_Alternating:
    def __init__(self):
        self.st = 0

    def __call__(self, primary, items):
        st = self.st = self.st + 1
        if st % 2: items.reverse()
        if st == 1: yield True, items
        else: yield False, items

    def reset(self):
        self.st = 0

class Convert_Scan_Increasing:
    def __call__(self, primary, items):
        yield True, items

    def reset(self):
        pass

class Convert_Scan_Decreasing:
    def __call__(self, primary, items):
        items.reverse()
        yield True, items

    def reset(self):
        pass

class Convert_Scan_Upmill:
    def __init__(self, slop = sin(pi / 18)):
        self.slop = slop

    def __call__(self, primary, items):
        for span in group_by_sign(items, self.slop, operator.itemgetter(2)):
            if amax([it[2] for it in span]) < 0:
                span.reverse()
            yield True, span

    def reset(self):
        pass

class Convert_Scan_Downmill:
    def __init__(self, slop = sin(pi / 18)):
        self.slop = slop

    def __call__(self, primary, items):
        for span in group_by_sign(items, self.slop, operator.itemgetter(2)):
            if amax([it[2] for it in span]) > 0:
                span.reverse()
            yield True, span

    def reset(self):
        pass

class Reduce_Scan_Lace:
    def __init__(self, converter, slope, keep):
        self.converter = converter
        self.slope = slope
        self.keep = keep

    def __call__(self, primary, items):
        slope = self.slope
        keep = self.keep
        if primary:
            idx = 3
            test = operator.le
        else:
            idx = 2
            test = operator.ge

        def bos(j):
            return j - j % keep

        def eos(j):
            if j % keep == 0: return j
            return j + keep - j%keep

        for i, (flag, span) in enumerate(self.converter(primary, items)):
            subspan = []
            a = None
            for i, si in enumerate(span):
                ki = si[idx]
                if a is None:
                    if test(abs(ki), slope):
                        a = b = i
                else:
                    if test(abs(ki), slope):
                        b = i
                    else:
                        if i - b < keep: continue
                        yield True, span[bos(a):eos(b+1)]
                        a = None
            if a is not None:
                yield True, span[a:]

    def reset(self):
        self.converter.reset()

#############
class Reduce_Scan_Lace_new:
    def __init__(self, converter, depth, keep):
        self.converter = converter
        self.depth = depth
        self.keep = keep

    def __call__(self, primary, items):
        keep = self.keep
        max_z_cut = self.depth  # set a max z value to cut
        
        def bos(j):
            return j - j % keep

        def eos(j):
            if j % keep == 0: return j
            return j + keep - j%keep

        for i, (flag, span) in enumerate(self.converter(primary, items)):
            subspan = []
            a = None
            for i, si in enumerate(span):
                ki = si[1]         # This is (x,y,z)
                z_value   = ki[2]  # Get the z value from ki
                if a is None:
                    if z_value < max_z_cut:
                        a = b = i
                else:
                    if z_value < max_z_cut:
                        b = i
                    else:
                        if i - b < keep: continue
                        yield True, span[bos(a):eos(b+1)]
                        a = None
            if a is not None:
                yield True, span[a:]

    def reset(self):
        self.converter.reset()
#############
        
unitcodes = ['G20', 'G21']
convert_makers = [ Convert_Scan_Increasing, Convert_Scan_Decreasing, Convert_Scan_Alternating, Convert_Scan_Upmill, Convert_Scan_Downmill ]

def progress(a, b, START_TIME, GUI=[]):
    if IN_AXIS:
        print >> sys.stderr, "FILTER_PROGRESS=%d" % int(a*100./b)
        sys.stderr.flush()
    else:
        CUR_PCT = (a*100./b)
        if CUR_PCT > 100.0:
            CUR_PCT = 100.0
        MIN_REMAIN =( time()-START_TIME )/60 * (100-CUR_PCT)/CUR_PCT
        MIN_TOTAL = 100.0/CUR_PCT * ( time()-START_TIME )/60
        message = '%.1f %% ( %.1f Minutes Remaining | %.1f Minutes Total )' %( CUR_PCT, MIN_REMAIN, MIN_TOTAL )
        try:   
            GUI.statusMessage.set(message)
        except:
            fmessage(message)

class Converter:
    def __init__(self, BIG, \
            image, units, tool_shape, pixelsize, pixelstep, safetyheight, tolerance,\
                 feed, convert_rows, convert_cols, cols_first_flag, border, entry_cut,\
                 roughing_delta, roughing_feed, xoffset, yoffset, splitstep, header, \
                 postscript, edge_offset, disable_arcs):

        self.BIG = BIG
        self.image = image
        self.units = units
        self.tool_shape = tool_shape
        self.pixelsize = pixelsize
        self.safetyheight = safetyheight
        self.tolerance = tolerance
        self.base_feed = feed
        self.convert_rows = convert_rows
        self.convert_cols = convert_cols
        self.cols_first_flag = cols_first_flag
        self.entry_cut = entry_cut
        self.roughing_delta = roughing_delta
        self.roughing_feed = roughing_feed
        self.header = header
        self.postscript = postscript
        self.border = border
        self.edge_offset = edge_offset
        self.disable_arcs = disable_arcs

        self.xoffset = xoffset
        self.yoffset = yoffset

        # Split step stuff
        splitpixels = 0
        if splitstep > epsilon:
            pixelstep   = int(floor(pixelstep * splitstep * 2))
            splitpixels = int(floor(pixelstep * splitstep    ))
        self.pixelstep   = pixelstep
        self.splitpixels = splitpixels

        self.cache = {}

        w, h = self.w, self.h = image.shape
        self.h1 = h
        self.w1 = w

        ### Percent complete stuff ###
        self.START_TIME=time()
        row_cnt=0
        cnt_border = 0
        if self.convert_rows != None:
            row_cnt = ceil( self.w1 / pixelstep) + 2
        col_cnt = 0
        if self.convert_cols != None:
            col_cnt = ceil( self.h1 / pixelstep) + 2
        if self.roughing_delta != 0:
            cnt_mult = ceil(self.image.min() / -self.roughing_delta) + 1
        else:
            cnt_mult = 1
        if self.convert_cols != None or self.convert_rows != None:
            cnt_border = 2
        self.cnt_total = (row_cnt + col_cnt + cnt_border )* cnt_mult
        self.cnt = 0.0

    def one_pass(self):
        g = self.g
        g.set_feed(self.feed)

        if self.convert_cols and self.cols_first_flag:
            self.g.set_plane(19)
            self.mill_cols(self.convert_cols, True)
            if self.convert_rows: g.safety()

        if self.convert_rows:
            self.g.set_plane(18)
            self.mill_rows(self.convert_rows, not self.cols_first_flag)

        if self.convert_cols and not self.cols_first_flag:
            self.g.set_plane(19)
            if self.convert_rows: g.safety()
            self.mill_cols(self.convert_cols, not self.convert_rows)

        g.safety()

        ## mill border ##
        if self.convert_cols:
            self.convert_cols.reset()
        if self.convert_rows:
            self.convert_rows.reset()

        step_save = self.pixelstep
        self.pixelstep = max(self.w1, self.h1) + 1
        if self.border == 1 and not self.convert_rows:
            if self.convert_cols:
                self.g.set_plane(18)
                self.mill_rows(self.convert_cols, True)
                g.safety()
                
        if self.border == 1 and not self.convert_cols:
            if self.convert_rows:
                self.g.set_plane(19)
                self.mill_cols(self.convert_rows, True)
                g.safety()
        self.pixelstep = step_save 

        if self.convert_cols:
            self.convert_cols.reset()
        if self.convert_rows:
            self.convert_rows.reset()
            
        g.safety()

    def convert(self):
        output_gcode = []
        self.g = g = Gcode(safetyheight=self.safetyheight,
                           tolerance=self.tolerance,
                           units=self.units,
                           header=self.header,
                           postscript=self.postscript, 
                           target=lambda s: output_gcode.append(s),
                           disable_arcs = self.disable_arcs)
        g.begin()
        g.continuous(self.tolerance)
        g.safety()
        
        if self.roughing_delta:
            ##########################################
            self.feed = self.roughing_feed
            r = -self.roughing_delta
            m = self.image.min()
            while r > m:
                self.rd = r
                self.one_pass()
                r = r - self.roughing_delta
            if r < m + epsilon:
                self.rd = m
                self.one_pass()
            ##########################################
        else:
            self.feed = self.base_feed
            self.rd = self.image.min()
            self.one_pass()
            ##########################################
        g.end()
        return output_gcode

    def get_z(self, x, y):
        try:
            return min(0, max(self.rd, self.cache[x,y]))
        except KeyError:
            self.cache[x,y] = d = self.image.height_calc(x,y,self.tool_shape)
            return min(0.0, max(self.rd, d))

    def get_dz_dy(self, x, y):
        y1 = max(0, y-1)
        y2 = min(self.image.shape[0]-1, y+1)
        dy = self.pixelsize * (y2-y1)
        return (self.get_z(x, y2) - self.get_z(x, y1)) / dy

    def get_dz_dx(self, x, y):
        x1 = max(0, x-1)
        x2 = min(self.image.shape[1]-1, x+1)
        dx = self.pixelsize * (x2-x1)
        return (self.get_z(x2, y) - self.get_z(x1, y)) / dx

    def frange(self,start, stop, step):
        out = []
        i = start
        while i < stop:
            out.append(i)
            i += step
        return out
            
    def mill_rows(self, convert_scan, primary):
        global STOP_CALC
        w1 = self.w1
        h1 = self.h1
        pixelsize = self.pixelsize
        pixelstep = self.pixelstep
        pixel_offset = int(ceil(self.edge_offset / pixelsize))
        jrange = self.frange(self.splitpixels+pixel_offset, w1-pixel_offset, pixelstep)
        if jrange[0] != pixel_offset: jrange.insert(0,pixel_offset)
        if w1-1-pixel_offset not in jrange: jrange.append(w1-1-pixel_offset)
        
        irange = range(pixel_offset,h1-pixel_offset)

        for j in jrange:
            self.cnt = self.cnt+1
            progress(self.cnt, self.cnt_total, self.START_TIME, self.BIG )
            y = (w1-j-1) * pixelsize + self.yoffset
            scan = []
            for i in irange:
                self.BIG.update()
                if STOP_CALC: return
                x = i * pixelsize + self.xoffset
                milldata = (i, (x, y, self.get_z(i, j)),
                            self.get_dz_dx(i, j), self.get_dz_dy(i, j))
                scan.append(milldata)
            for flag, points in convert_scan(primary, scan):
                if flag:
                    self.entry_cut(self, points[0][0], j, points)
                for p in points:
                    self.g.cut(*p[1])
            self.g.flush()



    def mill_cols(self, convert_scan, primary):
        global STOP_CALC
        w1 = self.w1
        h1 = self.h1
        pixelsize = self.pixelsize
        pixelstep = self.pixelstep
        pixel_offset = int(ceil(self.edge_offset / pixelsize))
        jrange = self.frange(self.splitpixels+pixel_offset, h1-pixel_offset, pixelstep)
        if jrange[0] != pixel_offset: jrange.insert(0,pixel_offset)
        if h1-1-pixel_offset not in jrange: jrange.append(h1-1-pixel_offset)

        irange = range(pixel_offset,w1-pixel_offset)
        
        if h1-1-pixel_offset not in jrange: jrange.append(h1-1-pixel_offset)
        jrange.reverse()

        for j in jrange:
            self.cnt = self.cnt+1
            progress(self.cnt, self.cnt_total, self.START_TIME, self.BIG )
            x = j * pixelsize + self.xoffset
            scan = []
            for i in irange:
                self.BIG.update()
                if STOP_CALC: return
                y = (w1-i-1) * pixelsize + self.yoffset
                milldata = (i, (x, y, self.get_z(j, i)),
                            self.get_dz_dy(j, i), self.get_dz_dx(j, i))
                scan.append(milldata)
            for flag, points in convert_scan(primary, scan):
                if flag:
                    self.entry_cut(self, j, points[0][0], points)
                for p in points:
                    self.g.cut(*p[1])
            self.g.flush()

def convert(*args, **kw):
    return Converter(*args, **kw).convert()

class SimpleEntryCut:
    def __init__(self, feed):
        self.feed = feed

    def __call__(self, conv, i0, j0, points):
        p = points[0][1]
        if self.feed:
            conv.g.set_feed(self.feed)
        conv.g.safety()
        conv.g.rapid(p[0], p[1])
        if self.feed:
            conv.g.set_feed(conv.feed)

# Calculate the portion of the arc to do so that none is above the
# safety height (that's just silly)
def circ(r,b):
    z = r**2 - (r-b)**2
    if z < 0: z = 0
    return z**.5

class ArcEntryCut:
    def __init__(self, feed, max_radius):
        self.feed = feed
        self.max_radius = max_radius

    def __call__(self, conv, i0, j0, points):
        if len(points) < 2:
            p = points[0][1]
            if self.feed:
                conv.g.set_feed(self.feed)
            conv.g.safety()
            conv.g.rapid(p[0], p[1])
            if self.feed:
                conv.g.set_feed(conv.feed)
            return

        p1 = points[0][1]
        p2 = points[1][1]
        z0 = p1[2]

        lim = int(ceil(self.max_radius / conv.pixelsize))
        r = range(1, lim)

        if self.feed:
            conv.g.set_feed(self.feed)
        conv.g.safety()

        x, y, z = p1

        pixelsize = conv.pixelsize

        cx = cmp(p1[0], p2[0])
        cy = cmp(p1[1], p2[1])

        radius = self.max_radius

        if cx != 0:
            h1 = conv.h1
            for di in r:
                dx = di * pixelsize
                i = i0 + cx * di
                if i < 0 or i >= h1: break
                z1 = conv.get_z(i, j0)
                dz = (z1 - z0)
                if dz <= 0: continue
                if dz > dx:
                    conv.g.write("(case 1)")
                    radius = dx
                    break
                rad1 = (dx * dx / dz + dz) / 2
                if rad1 < radius:
                    radius = rad1
                if dx > radius:
                    break

            z1 = min(p1[2] + radius, conv.safetyheight)

            x1 = p1[0] + cx * circ(radius, z1 - p1[2])
            conv.g.rapid(x1, p1[1])
            conv.g.cut(z=z1)

            I = - cx * circ(radius, z1 - p1[2])
            K = (p1[2] + radius) - z1
            
            conv.g.flush(); conv.g.lastgcode = None
            if cx > 0:
                #conv.g.write("G3 X%f Z%f R%f" % (p1[0], p1[2], radius)) #G3
                conv.g.write("G3 X%f Z%f I%f K%f" % (p1[0], p1[2], I, K))
            else:
                #conv.g.write("G2 X%f Z%f R%f" % (p1[0], p1[2], radius)) #G2
                conv.g.write("G2 X%f Z%f I%f K%f" % (p1[0], p1[2], I, K))
                
            conv.g.lastx = p1[0]
            conv.g.lasty = p1[1]
            conv.g.lastz = p1[2]
        else:
            w1 = conv.w1
            for dj in r:
                dy = dj * pixelsize
                j = j0 - cy * dj
                if j < 0 or j >= w1: break
                z1 = conv.get_z(i0, j)
                dz = (z1 - z0)
                if dz <= 0: continue
                if dz > dy:
                    radius = dy
                    break
                rad1 = (dy * dy / dz + dz) / 2
                if rad1 < radius: radius = rad1
                if dy > radius: break

            z1 = min(p1[2] + radius, conv.safetyheight)
            y1 = p1[1] + cy * circ(radius, z1 - p1[2])
            conv.g.rapid(p1[0], y1)
            conv.g.cut(z=z1)
            
            J =  -cy * circ(radius, z1 - p1[2])
            K = (p1[2] + radius) - z1
            
            conv.g.flush(); conv.g.lastgcode = None
            if cy > 0:
                #conv.g.write("G2 Y%f Z%f R%f" % (p1[1], p1[2], radius)) #G2
                conv.g.write("G2 Y%f Z%f J%f K%f" % (p1[1], p1[2], J, K))
            else:
                #conv.g.write("G3 Y%f Z%f R%f" % (p1[1], p1[2], radius)) #G3
                conv.g.write("G3 Y%f Z%f J%f K%f" % (p1[1], p1[2], J, K))
            conv.g.lastx = p1[0]
            conv.g.lasty = p1[1]
            conv.g.lastz = p1[2]
        if self.feed:
            conv.g.set_feed(conv.feed)

class Image_Matrix_List: #Nested list (no Numpy)
    def __init__(self, width=0, height=0):
        self.width  = width
        self.height = height
        self.matrix = []
        self.shape  = [width, height]

    def __call__(self,i,j):
        return self.matrix[i][j]

    def Assign(self,i,j,val):
        self.matrix[i][j] = float(val)
        
    def From_List(self,input_list):
        s = len(input_list)
        self.width  = s
        self.height = s
        
        for x in range(s):
            self.api()
            for y in range(s):
                self.apj(x,float(input_list[x][y]))


    def FromImage(self, im, pil_format):
        global STOP_CALC
        self.matrix = []

        if pil_format:      
            him,wim = im.size
            for i in range(0,wim):
                self.api()
                for j in range(0,him):
                    pix = im.getpixel((j,i))
                    self.apj(i,pix)
                
        else:
            him = im.width()
            wim = im.height()
            for i in range(0,wim):
                self.api()
                for j in range(0,him):
                    try:    pix = im.get(j,i).split()
                    except: pix = im.get(j,i)
                    self.apj(i,pix[0])

        self.width  = wim
        self.height = him
        self.shape  = [wim, him]
        self.t_offset = 0
        


    def pad_w_zeros(self,tool):
        ts = tool.width
        for i in range(len(self.matrix),self.width+ts):
            self.api()
            
        for i in range(0,len(self.matrix)):
            for j in range(len(self.matrix[i]),self.height+ts):
                self.apj(i,-1e1000000)

    def height_calc(self,x,y,tool):
        ts = tool.width
        d = -1e1000000
        ilow  = (int)(x-(ts-1)/2)
        ihigh = (int)(x+(ts-1)/2+1)
        jlow  = (int)(y-(ts-1)/2)
        jhigh = (int)(y+(ts-1)/2+1)
            
        icnt = 0
        for i in range( ilow , ihigh):
            jcnt = 0
            for j in range( jlow , jhigh):
                d = max( d, self(j,i) - tool(jcnt,icnt))
                jcnt = jcnt+1 
            icnt = icnt+1
        return d

    def min(self):
        minval = 1e1000000
        for i in range(0,self.width):
            for j in range(0,self.height):
                minval = min(minval,self.matrix[i][j])
        return minval

    def max(self):
        maxval = -1e1000000
        for i in range(0,self.width):
            for j in range(0,self.height):
                maxval = max(maxval,self.matrix[i][j])
        return maxval
        
    def api(self):
        self.matrix.append([])

    def apj(self,i,val):
        fval = float(val)
        self.matrix[i].append(fval)

    def mult(self,val):
        fval = float(val)
        icnt=0
        for i in self.matrix:
            jcnt = 0
            for j in i:
                self.matrix[icnt][jcnt] = fval * j
                jcnt = jcnt + 1
            icnt=icnt+1
            
    def minus(self,val):
        fval = float(val)
        icnt=0
        for i in self.matrix:
            jcnt = 0
            for j in i:
                self.matrix[icnt][jcnt] = j - fval
                jcnt = jcnt + 1
            icnt=icnt+1

class Image_Matrix_Numpy:
    def __init__(self, width=2, height=2):
        self.width  = width
        self.height = height
        self.matrix = numarray.zeros((width, height), 'Float32')
        self.shape  = [width, height]
        self.t_offset = 0

    def __call__(self,i,j):
        return self.matrix[i+self.t_offset,j+self.t_offset]

    def Assign(self,i,j,val):
        fval=float(val)
        self.matrix[i+self.t_offset,j+self.t_offset]=fval

    def From_List(self,input_list):
        s = len(input_list)
        self.width  = s
        self.height = s

        self.matrix = numarray.zeros((s, s), 'Float32')
        for x in range(s):
            for y in range(s):
                self.matrix[x,y]=float(input_list[x][y])       

    def FromImage(self, im, pil_format):
        global STOP_CALC
        self.matrix = []

        if pil_format:
            him,wim = im.size
            self.matrix = numarray.zeros((wim, him), 'Float32')
            for i in range(0,wim):
                for j in range(0,him):
                    pix = im.getpixel((j,i))
                    self.matrix[i,j] = float(pix)
        else:
            him = im.width()
            wim = im.height()
            self.matrix = numarray.zeros((wim, him), 'Float32')
            for i in range(0,wim):
                for j in range(0,him):
                    try:    pix = im.get(j,i).split()
                    except: pix = im.get(j,i)
                    self.matrix[i,j] = float(pix[0])
                    
        self.width  = wim
        self.height = him
        self.shape  = [wim, him]
        self.t_offset = 0

    def pad_w_zeros(self,tool):
        ts = tool.width
        self.t_offset = (ts-1)/2 
        to = self.t_offset
        
        w, h = self.shape
        w1 = w + ts-1
        h1 = h + ts-1
        temp = numarray.zeros((w1, h1), 'Float32')
        for j in range(0, w1):
            for i in range(0, h1):
                temp[j,i] = -1e1000000
        temp[to:to+w, to:to+h] = self.matrix
        self.matrix = temp

    def height_calc(self,x,y,tool):
        to = self.t_offset
        ts = tool.width
        d= -1e100000
        m1 = self.matrix[y:y+ts, x:x+ts]
        d = (m1 - tool.matrix).max()
        return d

    def min(self):
        return self.matrix[self.t_offset:self.t_offset+self.width,
                              self.t_offset:self.t_offset+self.height].min()
    def max(self):
        return self.matrix[self.t_offset:self.t_offset+self.width,
                              self.t_offset:self.t_offset+self.height].max()
    def mult(self,val):
        self.matrix = self.matrix * float(val)
            
    def minus(self,val):
        self.matrix = self.matrix - float(val)
        
################################################################################
#             Function for outputting messages to different locations          #
#            depending on what options are enabled                             #
################################################################################
def fmessage(text,newline=True):
    global IN_AXIS, QUIET
    if (not IN_AXIS and not QUIET):
        if newline==True:
            try:
                sys.stdout.write(text)
                sys.stdout.write("\n")
            except:
                pass
        else:
            try:
                sys.stdout.write(text)
            except:
                pass

def message_box(title,message):
    if VERSION == 3:
        tkinter.messagebox.showinfo(title,message)
    else:
        tkMessageBox.showinfo(title,message)
        pass

def message_ask_ok_cancel(title, mess):
    if VERSION == 3:
        result=tkinter.messagebox.askokcancel(title, mess)
    else:
        result=tkMessageBox.askokcancel(title, mess)
    return result

################################################################################
#                          Startup Application                                 #
################################################################################
if NUMPY == True:
    Image_Matrix = Image_Matrix_Numpy
else:
    Image_Matrix = Image_Matrix_List
    
root = Tk()
app = Application(root)
app.master.title("dmap2gcode V"+version)
app.master.iconname("dmap2gcode")
app.master.minsize(780,540)


try: #Attempt to create temporary icon bitmap file
    f = open("dmap2gcode_icon",'w')
    f.write("#define dmap2gcode_icon_width 16\n")
    f.write("#define dmap2gcode_icon_height 16\n")
    f.write("static unsigned char dmap2gcode_icon_bits[] = {\n")
    f.write("   0x3f, 0xfc, 0x1f, 0xf8, 0xcf, 0xf3, 0x6f, 0xe4, 0x6f, 0xed, 0xcf, 0xe5,\n")
    f.write("   0x1f, 0xf4, 0xfb, 0xf3, 0x73, 0x98, 0x47, 0xce, 0x0f, 0xe0, 0x3f, 0xf8,\n")
    f.write("   0x7f, 0xfe, 0x3f, 0xfc, 0x9f, 0xf9, 0xcf, 0xf3 };\n")
    f.close()
    app.master.iconbitmap("@dmap2gcode_icon")
    os.remove("dmap2gcode_icon")
except:
    fmessage("Unable to create temporary icon file.")

root.mainloop()
