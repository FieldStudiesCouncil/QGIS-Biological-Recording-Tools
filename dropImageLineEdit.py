# -*- coding: utf-8 -*-
"""
/***************************************************************************
dropImageLineEdit
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

import mimetypes
from PyQt5 import QtCore, QtGui, QtWidgets

class DragLineEdit(QtWidgets.QLineEdit):

    imageDropped = QtCore.pyqtSignal(QtGui.QImage)
    
    def __init__(self, parent):  
        QtWidgets.QLineEdit.__init__(self, parent)
        self.setAcceptDrops (True)

    def loadImage(self, data):
        if isinstance(data, QtGui.QImage):
            self.imageDropped.emit(data) 

    def dragEnterEvent (self, event):
        mimedata = event.mimeData()
        if mimedata.hasImage():
            event.acceptProposedAction()
            self.setBackColour(QtGui.QColor(125,255,125,255))
            
    def dragLeaveEvent (self, event):
        self.setBackColour(QtGui.QColor(0,0,0,0))
            
    def setBackColour(self, colour):
        p = self.palette()
        p.setColor(self.backgroundRole(), colour)
        self.setPalette(p)

    def dropEvent(self, event):
        self.setBackColour(QtGui.QColor(0,0,0,0))
        mimedata = event.mimeData()
        if mimedata.hasImage():
            self.loadImage(mimedata.imageData())
