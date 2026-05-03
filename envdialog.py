# -*- coding: utf-8 -*-
"""
/***************************************************************************
EnvDialog
                                 A QGIS plugin
 FSC QGIS plugin for biological recorders
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

from . import envmanager
import os.path
import csv
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtNetwork import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt import uic
from qgis import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), "ui_env.ui"))


class EnvDialog(QWidget, FORM_CLASS):
    def __init__(self, iface):
        QWidget.__init__(self)
        self.setupUi(self)
        self.__canvas = iface.mapCanvas()
        self.iface = iface

        # self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        self.pathPlugin = os.path.dirname(__file__)

        # Load the environment stuff
        self.env = envmanager.envManager()
        self.pteEnvironment.setPlainText(self.env.getTextEnv())
        self.leExternalEnvFile.setText(self.env.getExternalFilePath())
        self.leExternalEnvFile.setEnabled(False)

        self.exampleText = self.env.getTextExample()
        self.pteExample.setPlainText(self.exampleText)
        self.pbSaveToNewEnvFile.clicked.connect(self.saveToNewEnvFile)
        self.pbExternalEnvFile.clicked.connect(self.browseEnvFile)

        self.bbButtons.accepted.connect(self.okayClicked)
        self.bbButtons.rejected.connect(self.cancelClicked)

        self.pteExample.textChanged.connect(self.editingExample)

    def browseEnvFile(self):

        dlg = QFileDialog
        fileName = dlg.getOpenFileName(
            self, "Open environment file", "", "Text Files (*.txt)")[0]
        if fileName:
            self.leExternalEnvFile.setText(fileName)
            self.env.setExternalEnvFile(fileName, True)
            self.pteEnvironment.setPlainText(self.env.getTextEnv())

    def saveToNewEnvFile(self):

        dlg = QFileDialog
        fileName = dlg.getSaveFileName(
            self,
            "Specify location for environment file",
            "",
            "Text Files (*.txt)")[0]
        if fileName:
            self.leExternalEnvFile.setText(fileName)
            self.env.setExternalEnvFile(fileName, False)

    def editingExample(self):

        self.iface.messageBar().pushMessage(
            "Warning",
            "You are editing the example environment file - changes will not be saved",
            level=Qgis.Warning,
            duration=1)
        self.pteExample.blockSignals(True)
        self.pteExample.setPlainText(self.exampleText)
        self.pteExample.blockSignals(False)

    def okayClicked(self):

        self.env.setTextEnv(self.pteEnvironment.toPlainText())
        self.env.saveEnvironment()
        self.close()

    def cancelClicked(self):
        self.pteEnvironment.setPlainText(self.env.getTextEnv())
        self.close()

    def hideEvent(self, event):
        # QWidget.hideEvent(event)
        self.visChanged(False)

    def visChanged(self, vis):
        if not vis:
            self.cancelClicked()
