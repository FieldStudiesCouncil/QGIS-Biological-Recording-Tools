# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TomBio
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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import resources_rc
from osgrdialog import OsgrDialog
from nbndialog import NBNDialog
from mapmashupdialog import MapmashupDialog
from biorecdialog import BiorecDialog
from envdialog import EnvDialog
import os.path

class custDockWidget(QDockWidget):

    closed = pyqtSignal()
    
    def __init__(self, title, parent):
        super(custDockWidget, self).__init__(title, parent)
        
    # The QDockWidget class is subclassed so that we can detect when the widget
    # is closed by the user.
    
    def closeEvent(self, event):
        super(custDockWidget, self).closeEvent(event)
        self.closed.emit()

class TomBio:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n', 'tombio_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
                
    def initGui(self):

        # Toolbar
        self.toolbar = self.iface.addToolBar("TomBioToolbar")
        
        # OSGR tool
        self.actionOsgr = QAction(QIcon(":/plugins/TomBio/images/osgrPoly.png"), u"OSGR tools", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&TomBio productivity tools", self.actionOsgr)
        self.actionOsgr.triggered.connect(self.showOsgrDialog)
        self.toolbar.addAction(self.actionOsgr)
        self.dwOsgr = None
        
        # Display biological records tools
        self.actionBiorec = QAction(QIcon(":/plugins/TomBio/images/maptaxa.png"), u"Biological record tools", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&TomBio productivity tools", self.actionBiorec)
        self.actionBiorec.triggered.connect(self.showBiorecDialog)
        self.toolbar.addAction(self.actionBiorec)
        self.dwBiorec = None
        
        # NBN tools
        self.actionNbn = QAction(QIcon(":/plugins/TomBio/images/nbn.png"), u"NBN tools", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&TomBio productivity tools", self.actionNbn)
        self.actionNbn.triggered.connect(self.showNbnDialog)
        self.toolbar.addAction(self.actionNbn)
        self.dwNbn = None
        
        # Map mashup tools 
        self.actionMapMash = QAction(QIcon(":/plugins/TomBio/images/mashup.png"), u"Map mashup", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&TomBio productivity tools", self.actionMapMash)
        self.actionMapMash.triggered.connect(self.showMapmashupDialog)
        self.toolbar.addAction(self.actionMapMash)
        self.dwMapmashup = None
        
        # Environment dialog
        self.actionEnv = QAction(u"Environment options", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&TomBio productivity tools", self.actionEnv)
        self.actionEnv.triggered.connect(self.showEnvDialog)
        self.guiEnv = None
        
         # Help dialog
        self.actionHelp = QAction(u"Help", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&TomBio productivity tools", self.actionHelp)
        self.actionHelp.triggered.connect(self.showHelp)
        #self.guiEnv = None
        
    def showHelp(self):
        #showPluginHelp()
        QDesktopServices().openUrl(QUrl("http://tombio.myspecies.info/QGISTools"))
        
    def showOsgrDialog(self):
        if self.dwOsgr is None:
            self.dwOsgr = custDockWidget("FSC Tom.bio - OSGR tools", self.iface.mainWindow())
            self.guiOsgr = OsgrDialog(self.iface, self.dwOsgr)
            self.dwOsgr.setWidget(self.guiOsgr)
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dwOsgr)
            self.dwOsgr.closed.connect(self.closeOsgrDialog)
        else:
            self.dwOsgr.setVisible(True)
            
    def closeOsgrDialog(self):
        self.guiOsgr.clearMapGraphics()
        self.guiOsgr.cbGRShowSquare.setChecked(False)
        
    def showNbnDialog(self):
        if self.dwNbn is None:
            self.dwNbn = custDockWidget("FSC Tom.bio - NBN tools", self.iface.mainWindow())
            self.guiNbn = NBNDialog(self.iface, self.dwNbn)
            self.dwNbn.setWidget(self.guiNbn)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dwNbn)
            self.guiNbn.displayNBNCSVFile.connect(self.displayNBNCSVFile)
        else:
            self.dwNbn.setVisible(True)
            
    def displayNBNCSVFile(self, strCSV):
        self.dwNbn.setVisible(False)
        self.showBiorecDialog()
        #self.iface.messageBar().pushMessage("Info", "CSV: " + strCSV, level=QgsMessageBar.INFO)
        self.guiBiorec.setCSV(strCSV)
            
    def showMapmashupDialog(self):
        if self.dwMapmashup is None:
            self.dwMapmashup = custDockWidget("FSC Tom.bio - Map mashup", self.iface.mainWindow())
            self.guiMapmashup = MapmashupDialog(self.iface, self.dwMapmashup)
            self.dwMapmashup.setWidget(self.guiMapmashup)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dwMapmashup)
        else:
            self.dwMapmashup.setVisible(True)
            
    def showBiorecDialog(self):
        if self.dwBiorec is None:
            self.dwBiorec = custDockWidget("FSC Tom.bio - Biological record display", self.iface.mainWindow())
            self.guiBiorec = BiorecDialog(self.iface, self.dwBiorec)
            self.dwBiorec.setWidget(self.guiBiorec)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dwBiorec)
        else:
            self.dwBiorec.setVisible(True)
            
    def showEnvDialog(self):
        if self.guiEnv is None:
            self.guiEnv = EnvDialog(self.iface)
      
        self.guiEnv.setVisible(True)
            
    def unload(self):
        # Remove the plugin menu item
        self.iface.removePluginMenu(u"&TomBio productivity tools", self.actionOsgr)
        self.iface.removePluginMenu(u"&TomBio productivity tools", self.actionBiorec)
        self.iface.removePluginMenu(u"&TomBio productivity tools", self.actionNbn)
        self.iface.removePluginMenu(u"&TomBio productivity tools", self.actionMapMash)
        self.iface.removePluginMenu(u"&TomBio productivity tools", self.actionEnv)
        self.iface.removePluginMenu(u"&TomBio productivity tools", self.actionHelp)
        
        #Remove the toolbar
        del self.toolbar
