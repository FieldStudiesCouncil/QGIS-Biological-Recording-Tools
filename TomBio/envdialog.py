# -*- coding: utf-8 -*-
"""
/***************************************************************************
EnvDialog
                                 A QGIS plugin
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

from ui_env import Ui_Env
import os.path
import csv
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from envmanager import *

class EnvDialog(QWidget, Ui_Env):
    def __init__(self, iface):
        QWidget.__init__(self)
        Ui_Env.__init__(self)
        self.setupUi(self)
        self.__canvas = iface.mapCanvas()
        self.__iface = iface

        #self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        self.pathPlugin = os.path.dirname( __file__ ) 
        
        # Load the environment stuff
        self.env = envManager()
        self.pteEnvironment.setPlainText(self.env.getTextEnv())
        
        self.bbButtons.accepted.connect(self.okayClicked)
        self.bbButtons.rejected.connect(self.cancelClicked)
        
    def okayClicked(self):
        
        self.env.setTextEnv(self.pteEnvironment.toPlainText())
        self.env.saveEnvironment()
        self.close()
        
    def cancelClicked(self):
        self.pteEnvironment.setPlainText(self.env.getTextEnv())
        self.close()
        
    def hideEvent(self, event):
        #QWidget.hideEvent(event)
        self.visChanged(False)
        
    def visChanged(self, vis):
        if vis == False:
            self.cancelClicked()

            
    