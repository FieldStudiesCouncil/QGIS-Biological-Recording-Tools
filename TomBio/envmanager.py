# -*- coding: utf-8 -*-
"""
/***************************************************************************
 envmanager
        A class for managing environment stuff
 FSC Tomorrow's Biodiversity productivity tools for biological recorders
                              -------------------
        begin                : 2014-02-17
        copyright            : (C) 2014 by Rich Burkmar, Field Studies Council
        email                : richardb@field-studies-council.org
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os
from shutil import *

class envManager():
    
    def __init__(self):
        
        self.iniFile = os.path.join(os.path.dirname( __file__ ), "iniBioRec.txt")
        self.iniFileDefault = os.path.join(os.path.dirname( __file__ ), "iniBioRecDefault.txt")
        if not os.path.exists(self.iniFile):
            if os.path.exists(self.iniFileDefault):
                copyfile(self.iniFileDefault, self.iniFile) 
            
        self.loadEnvironment()
        
    def loadEnvironment(self):
        
        #self.pteEnvironment.appendPlainText(fileEnv)
        if os.path.isfile(self.iniFile):
            self.textEnv = open(self.iniFile).read()
        else:
            self.textEnv = "Environment File '" + self.iniFile + "'not found."
            self.textEnv = "#Environment File"
            
    def saveEnvironment(self):
        f = open(self.iniFile, 'w')
        f.write(self.textEnv)
        f.close()
        
    def getTextEnv(self):
        return self.textEnv
        
    def getTextExample(self):
        if os.path.isfile(self.iniFileDefault):
            return open(self.iniFileDefault).read()
    
    def setTextEnv(self, textEnv):
        self.textEnv = textEnv
    
    def getEnvValue(self, envLabel):
        # Returns the first matching value
        search = envLabel + ": "
        lines = self.textEnv.split('\n' )
        for line in lines:
            if line.startswith(search):
                return line[len(search):]
        return ""
    
    def getEnvValues(self, envLabel):
        # Returns a list of all matching values
        ret = []
        search = envLabel + ": "
        lines = self.textEnv.split('\n' )
        for line in lines:
            if line.startswith(search):
                ret.append(line[len(search):])
        return ret
    
    def isValueAssignedToLabel(self, envLabel, envValue):
        # Returns True if the value is assigned to the label
        pass