# -*- coding: utf-8 -*-
"""
/***************************************************************************
 drag_box_tool
        A class for dragging a box on the map
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
from qgis.core import *
from qgis.gui import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class RectangleMapTool(QgsMapToolEmitPoint):

  boxDragged = pyqtSignal() 

  def __init__(self, canvas, iface):
      self.canvas = canvas
      self.iface = iface
      QgsMapToolEmitPoint.__init__(self, self.canvas)
      self.rubberBand = QgsRubberBand(self.canvas, False)
      self.rubberBand.setColor(Qt.black)
      self.rubberBand.setWidth(1)
      self.reset()

  def reset(self):
      self.startPoint = self.endPoint = None
      self.isEmittingPoint = False
      self.rubberBand.reset(False)

  def canvasPressEvent(self, e):
      self.startPoint = self.toMapCoordinates(e.pos())
      self.endPoint = self.startPoint
      self.isEmittingPoint = True
      self.showRect(self.startPoint, self.endPoint)

  def canvasReleaseEvent(self, e):
      self.isEmittingPoint = False
      r = self.rectangle()
      if r is not None:
        #strMessage = str(r.xMinimum()) + ":" +  str(r.yMinimum()) + ":" + str(r.xMaximum()) + ":" + str(r.yMaximum())
        #self.iface.messageBar().pushMessage("Output", strMessage, level=Qgis.Info)
        self.xMinimum = r.xMinimum()
        self.xMaximum = r.xMaximum()
        self.yMinimum = r.yMinimum()
        self.yMaximum = r.yMaximum()
        self.rubberBand.reset(False)
        self.boxDragged.emit()
        
  def canvasMoveEvent(self, e):
      if not self.isEmittingPoint:
        return

      self.endPoint = self.toMapCoordinates( e.pos() )
      self.showRect(self.startPoint, self.endPoint)

  def showRect(self, startPoint, endPoint):
      self.rubberBand.reset(False)
      if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
        return

      point1 = QgsPoint(startPoint.x(), startPoint.y())
      point2 = QgsPoint(startPoint.x(), endPoint.y())
      point3 = QgsPoint(endPoint.x(), endPoint.y())
      point4 = QgsPoint(endPoint.x(), startPoint.y())

      #self.rubberBand.addPoint( point1, False )
      #self.rubberBand.addPoint( point2, False )
      #self.rubberBand.addPoint( point3, False )
      #self.rubberBand.addPoint( point4, True )    # true to update canvas#
      #self.rubberBand.show()
      
      points = [point1, point2, point3, point4, point1]
      self.rubberBand.setToGeometry(QgsGeometry.fromPolyline(points), None)
      
  def rectangle(self):
      if self.startPoint is None or self.endPoint is None:
        return None
      elif self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == \
        self.endPoint.y():
        return None

      return QgsRectangle(self.startPoint, self.endPoint)

  def deactivate(self):
  #AttributeError: 'NoneType' object has no attribute 'deactivate'
      #QgsMapTool.deactivate(self)
      #self.emit(SIGNAL("deactivated()"))
      pass

