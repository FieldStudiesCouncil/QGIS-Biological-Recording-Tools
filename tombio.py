# -*- coding: utf-8 -*-
"""
/***************************************************************************
                                 A QGIS plugin
 FSC QGIS Plugin for biological recorders
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
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from . import osgrdialog
from . import nbndialog
from . import mapmashupdialog
from . import biorecdialog
from . import envdialog
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
        locale = QSettings().value('locale/userLocale')[0:2]
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
        icon_path = os.path.join(os.path.dirname(__file__),'images/osgrPoly.png')
        self.actionOsgr = QAction(QIcon(icon_path), u"OSGR Tool", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&FSC Tools", self.actionOsgr)
        self.actionOsgr.triggered.connect(self.showOsgrDialog)
        self.toolbar.addAction(self.actionOsgr)
        self.dwOsgr = None
        
        # Display Biological Records Tool
        icon_path = os.path.join(os.path.dirname(__file__),'images/maptaxa.png')
        self.actionBiorec = QAction(QIcon(icon_path), u"Biological Records Tool", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&FSC Tools", self.actionBiorec)
        self.actionBiorec.triggered.connect(self.showBiorecDialog)
        self.toolbar.addAction(self.actionBiorec)
        self.dwBiorec = None
        
        # NBN Tool
        icon_path = os.path.join(os.path.dirname(__file__),'images/nbn.png')
        self.actionNbn = QAction(QIcon(icon_path), u"NBN Atlas Tool", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&FSC Tools", self.actionNbn)
        self.actionNbn.triggered.connect(self.showNbnDialog)
        self.toolbar.addAction(self.actionNbn)
        self.dwNbn = None
        
        # Map Mashup Tool
        icon_path = os.path.join(os.path.dirname(__file__),'images/mashup.png')
        self.actionMapMash = QAction(QIcon(icon_path), u"Map Mashup Tool", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&FSC Tools", self.actionMapMash)
        self.actionMapMash.triggered.connect(self.showMapmashupDialog)
        self.toolbar.addAction(self.actionMapMash)
        self.dwMapmashup = None
        
        # Help dialog
        icon_path = os.path.join(os.path.dirname(__file__),'images/info.png')
        self.actionHelp = QAction(QIcon(icon_path), u"Help and Info on FSC QGIS plugin", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&FSC Tools", self.actionHelp)
        self.actionHelp.triggered.connect(self.showHelp)
        self.toolbar.addAction(self.actionHelp)
        
        # Environment Options
        self.actionEnv = QAction(u"Environment Options", self.iface.mainWindow())
        self.iface.addPluginToMenu(u"&FSC Tools", self.actionEnv)
        self.actionEnv.triggered.connect(self.showEnvDialog)
        self.guiEnv = None

    def showHelp(self):
        #showPluginHelp()
        QDesktopServices().openUrl(QUrl("http://www.tombio.uk/qgisplugin"))
        
    def showOsgrDialog(self):
        if self.dwOsgr is None:
            self.dwOsgr = custDockWidget("FSC - OSGR Tool", self.iface.mainWindow())
            self.guiOsgr = osgrdialog.OsgrDialog(self.iface, self.dwOsgr)
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
            self.dwNbn = custDockWidget("FSC - NBN Atlas Tool", self.iface.mainWindow())
            self.guiNbn = nbndialog.NBNDialog(self.iface, self.dwNbn)
            self.dwNbn.setWidget(self.guiNbn)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dwNbn)
            self.guiNbn.displayNBNCSVFile.connect(self.displayNBNCSVFile)
        else:
            self.dwNbn.setVisible(True)
            
    def displayNBNCSVFile(self, strCSV):
        self.dwNbn.setVisible(False)
        self.showBiorecDialog()
        #self.iface.messageBar().pushMessage("Info", "CSV: " + strCSV, level=Qgis.Info)
        self.guiBiorec.setCSV(strCSV)
            
    def showMapmashupDialog(self):
        if self.dwMapmashup is None:
            self.dwMapmashup = custDockWidget("FSC - Map Mashup Tool", self.iface.mainWindow())
            self.guiMapmashup = mapmashupdialog.MapmashupDialog(self.iface, self.dwMapmashup)
            self.dwMapmashup.setWidget(self.guiMapmashup)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dwMapmashup)
        else:
            self.dwMapmashup.setVisible(True)
            
    def showBiorecDialog(self):
        if self.dwBiorec is None:
            self.dwBiorec = custDockWidget("FSC - Biological Records Tool", self.iface.mainWindow())
            self.guiBiorec = biorecdialog.BiorecDialog(self.iface, self.dwBiorec)
            self.dwBiorec.setWidget(self.guiBiorec)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dwBiorec)
        else:
            self.dwBiorec.setVisible(True)
            
            #self.dwBiorec.setVisible(False)
            #self.dwBiorec = custDockWidget("FSC - Biological Records Tool", self.iface.mainWindow())
            #self.guiBiorec = BiorecDialog(self.iface, self.dwBiorec)
            #self.dwBiorec.setWidget(self.guiBiorec)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dwBiorec)
            
    def showEnvDialog(self):
        if self.guiEnv is None:
            self.guiEnv = envdialog.EnvDialog(self.iface)
      
        self.guiEnv.setVisible(True)
            
    def unload(self):
        # Remove the plugin menu item
        self.iface.removePluginMenu(u"&FSC Tools", self.actionOsgr)
        self.iface.removePluginMenu(u"&FSC Tools", self.actionBiorec)
        self.iface.removePluginMenu(u"&FSC Tools", self.actionNbn)
        self.iface.removePluginMenu(u"&FSC Tools", self.actionMapMash)
        self.iface.removePluginMenu(u"&FSC Tools", self.actionEnv)
        self.iface.removePluginMenu(u"&FSC Tools", self.actionHelp)
        
        #Remove the toolbar
        del self.toolbar
