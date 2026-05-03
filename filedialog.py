# -*- coding: utf-8 -*-
"""
/***************************************************************************
FileDialog
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

import os.path
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtNetwork import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt import uic
from qgis.core import *
from qgis.gui import *
from qgis.utils import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), "ui_file.ui"))


class FileDialog(QWidget, FORM_CLASS):
    def __init__(self, iface, strFilePath):
        QWidget.__init__(self)
        self.setupUi(self)
        self.__iface = iface

        # self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        self.pathPlugin = os.path.dirname(__file__)

        self.pbClose.clicked.connect(self.closeWindow)

        # Load file
        if os.path.isfile(strFilePath):
            self.pteEnvironment.setPlainText(open(strFilePath).read())
        else:
            self.pteEnvironment.setPlainText(
                "Didn't find file '" + strFilePath + "'")

    def closeWindow(self):
        self.close()
