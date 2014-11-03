# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OsgrDialog
                                 A QGIS plugin
 OS grid reference tools
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
from ui_osgr import Ui_osgr
import os.path
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from osgr import *
from osgrLayer import *
from drag_box_tool import *

class OsgrDialog(QWidget, Ui_osgr):
    
  def __init__(self, iface, dockwidget):
    QWidget.__init__(self)
    Ui_osgr.__init__(self)
    self.setupUi(self)
    self.canvas = iface.mapCanvas()
    self.iface = iface
    self.rbGridSquare = QgsRubberBand(self.canvas, False)

    # Get a reference to an osgr object and an osgrLayer object
    self.osgr = osgr()
    self.osgrLayer = osgrLayer(iface)
    
    # Make a coordinate translator. Also need global references to OSGB and canvas CRSs since
    # they cannot be retrieved from a translator object.
    self.canvasCrs = self.canvas.mapRenderer().destinationCrs()
    self.osgbCrs = QgsCoordinateReferenceSystem("EPSG:27700")
    self.transformCrs = QgsCoordinateTransform(self.canvas.mapRenderer().destinationCrs(), QgsCoordinateReferenceSystem("EPSG:27700"))
    
    # Set the button graphics
    self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
    self.butGridTool.setIcon(QIcon( self.pathPlugin % "images/osgr.png" ))
    self.butGridPoly.setIcon(QIcon( self.pathPlugin % "images/osgrPoly.png" ))
    self.butClear.setIcon(QIcon( self.pathPlugin % "images/cross.png" ))
    
    # Connect the controls to their events
    self.cbGROnClick.clicked.connect(self.cbGROnClickClicked)
    self.cbGRShowSquare.clicked.connect(self.cbGRShowSquareClicked)
    self.cboPrecision.currentIndexChanged.connect(self.cboPrecisionChanged)
    self.butLocate.clicked.connect(self.butLocateClicked)
    self.butGridTool.clicked.connect(self.butGridToolClicked)
    self.butGridPoly.clicked.connect(self.GridPoly)
    self.butClear.clicked.connect(self.ClearGrid)
    self.cbLabel.clicked.connect(self.LabelChecked)
    self.butCancel.clicked.connect(self.cancelGrid)
    
    # Handle canvas events
    self.canvas.mapToolSet.connect(self.mapToolClicked)
    self.canvas.xyCoordinates.connect(self.canvasMouseMove)
    
    # Handle events from the osgrLayer object
    self.osgrLayer.progChange.connect(self.setProgBarValue)
    self.osgrLayer.progMax.connect(self.setProgBarMax)
    self.osgrLayer.gridComplete.connect(self.gridControlsEnable)
    
    # Create the GR click tool based on a QgsMapToolEmitPoint tool
    self.clickTool = QgsMapToolEmitPoint(self.canvas)
    self.clickTool.canvasClicked.connect(self.canvasClicked)
    
    # Create the grid square drag tool based on a custom rectangle tool
    self.dragTool = RectangleMapTool(self.canvas, self.iface)
    self.dragTool.boxDragged.connect(self.boxDragged)
    
    # Initialisations
    self.easting = 0
    self.northing = 0
    self.cboPrecisionChanged(0)
    self.LabelChecked()
    
    
    
  def setProgBarValue(self, value):
    self.pbGridSquares.setValue(value)
    
  def setProgBarMax(self, value):
    self.pbGridSquares.setMaximum(value)
  
  def cancelGrid(self):
    self.osgrLayer.cancelGrid()
    
  def LabelChecked(self):
    self.osgrLayer.setShowLabels(self.cbLabel.isChecked())
    
  def ClearGrid(self):
    self.osgrLayer.clear()

  def butGridToolClicked(self, pos):
    # Make the GR tool the current map tool
    if self.butGridTool.isChecked():
      #self.butGridTool.setIcon(QIcon( self.pathPlugin % "images/osgrDown2.jpg" ))
      self.canvas.setMapTool(self.dragTool)
    else:
      #self.butGridTool.setIcon(QIcon( self.pathPlugin % "images/osgr.png" ))
      self.canvas.unsetMapTool(self.dragTool)
      
  def boxDragged(self):
    self.GenerateSquares(self.dragTool.xMinimum, self.dragTool.yMinimum, self.dragTool.xMaximum, self.dragTool.yMaximum, [])
    
  def GridPoly(self):
  
    if not self.isOSGB():
        return
        
    layer = self.iface.activeLayer()
    if layer.type() == QgsMapLayer.VectorLayer:
        selectedFeatures = layer.selectedFeatures()
        if len(selectedFeatures) > 0:
            rect = layer.boundingBoxOfSelected() 	
            self.GenerateSquares(rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum(), selectedFeatures)
        else:
            self.iface.messageBar().pushMessage("Info", "There are no features selected in the active layer.", level=QgsMessageBar.INFO)
    else:
        self.iface.messageBar().pushMessage("Info", "The active layer is not a vector layer.", level=QgsMessageBar.INFO)
    
  def GenerateSquares(self, xMin, yMin, xMax, yMax, selectedFeatures):
  
    if not self.isOSGB():
        return
        
    llx = (xMin // self.precision) * self.precision
    lly= (yMin // self.precision) * self.precision
    iSquares = (((xMax - llx) // self.precision + 1) * ((yMax - lly) // self.precision + 1))
    if iSquares > 1000:
        ret = QMessageBox.warning(self, "Warning",
                "Large area specified relative to the precision (" + self.cboPrecision.currentText() + "). This could generate up to " + str(int(iSquares)) + " grid squares which could take some time. Do you want to continue? (You can interrupt with the Cancel button.)",
                QMessageBox.Ok, QMessageBox.Cancel)
        if ret == QMessageBox.Cancel:
            return
    self.gridControlsEnableDisable(False)
    self.osgrLayer.boxDragged(xMin, yMin, xMax, yMax, selectedFeatures)
    
  def gridControlsEnable(self):
    self.gridControlsEnableDisable(True)
    
  def gridControlsEnableDisable(self, bool):
    self.butGridPoly.setEnabled(bool)
    self.butGridTool.setEnabled(bool)
    self.butClear.setEnabled(bool)
    self.cbLabel.setEnabled(bool)
    
  def isOSGB(self):
    self.checkTransform()
    if self.canvasCrs != self.osgbCrs:
        self.iface.messageBar().pushMessage("Info", "The map canvas CRS needs to be set to EPSG:27700 for this function", level=QgsMessageBar.WARNING)
        return False
    else:
        return True
        
  def checkTransform(self):
    if self.canvasCrs != self.canvas.mapRenderer().destinationCrs():
        self.canvasCrs = self.canvas.mapRenderer().destinationCrs()
        self.transformCrs = QgsCoordinateTransform(self.canvasCrs, self.osgbCrs)
     
  def butLocateClicked(self, pos):
  
    if not self.isOSGB():
        return
        
    res = self.osgr.enFromGR(self.leOSGR.text())
    
    if res[0] == 0:
        self.iface.messageBar().pushMessage("Warning", res[3], level=QgsMessageBar.WARNING)
    else:
        precision = res[2]
        x0 = (res[0] - precision / 1.8)
        x1 = (res[0] + precision / 1.8)
        y0 = (res[1] - precision / 1.8)
        y1 = (res[1] + precision / 1.8)
        
        ll = QgsPoint(x0, y0)
        ur = QgsPoint(x1, y1)
        rect = QgsRectangle(ll, ur)
        centre = QgsPoint(res[0], res[1])
        #rect = QgsRectangle(centre, centre)
        self.canvas.setExtent(rect)
        self.canvas.refresh()
        
        if precision == 1:
            self.cboPrecision.setCurrentIndex(0)
        elif precision == 10:
            self.cboPrecision.setCurrentIndex(1)
        elif precision == 100:
            self.cboPrecision.setCurrentIndex(2)
        elif precision == 1000:
            self.cboPrecision.setCurrentIndex(3)
        elif precision == 2000:
            self.cboPrecision.setCurrentIndex(4)
        elif precision == 5000:
            self.cboPrecision.setCurrentIndex(5)
        elif precision == 10000:
            self.cboPrecision.setCurrentIndex(6)
        elif precision == 100000:
            self.cboPrecision.setCurrentIndex(7)
            
        self.displayOSGR(centre)
    
  def cboPrecisionChanged(self, int):
  
    # Set precision and colour for grid square
    if self.cboPrecision.currentIndex() == 0:
        precision = 1
        colour = QColor(0,0,0)
    elif self.cboPrecision.currentIndex() == 1:
        precision = 10
        colour = QColor(255,0,255)
    elif self.cboPrecision.currentIndex() == 2:
        precision = 100
        colour = QColor(255,0,0)
    elif self.cboPrecision.currentIndex() == 3:
        precision = 1000
        colour = QColor(0,255,255)
    elif self.cboPrecision.currentIndex() == 4:
        precision = 2000
        colour = QColor(0,255,0)
    elif self.cboPrecision.currentIndex() == 5:
        precision = 5000
        colour = QColor(255,255,0)
    elif self.cboPrecision.currentIndex() == 6:
        precision = 10000
        colour = QColor(128,128,218)
    else:
        precision = 100000
        colour = QColor(0,0,255)
        
    self.precision = precision
    self.grPrecision = precision
    self.grColour = colour
    
    self.displayOSGR(QgsPoint(self.easting,self.northing))
    
    self.osgrLayer.setPrecision(self.grPrecision)
    self.osgrLayer.setPrecisionText(self.cboPrecision.currentText())

  def cbGROnClickClicked(self):
    # Make the GR tool the current map tool
    self.canvas.setMapTool(self.clickTool)
    self.leOSGR.setText("")
    self.clearMapGraphics()
    
  def cbGRShowSquareClicked(self):
    self.clearMapGraphics()
        
  def clearMapGraphics(self):
    # Delete any rubberband graphics
    try:
        self.canvas.scene().removeItem(self.rbGridSquare)
    except:
        pass
    
  def mapToolClicked(self, tool):
    # We get here whenever the mapTool changes - useful for un-setting custom mapTool buttons
    if (tool != self.clickTool):
        self.cbGROnClick.setChecked(False)
        self.cbGRShowSquare.setChecked(False)
    if (tool != self.dragTool):
        self.butGridTool.setChecked(False)
        #self.butGridTool.setIcon(QIcon( self.pathPlugin % "images/osgr.png" ))
        
  def canvasMouseMove(self, point):
    try:
        if self.cbGROnClick.isChecked() == False:
            self.displayOSGR(point)
    except:
        #Catches an error on map canvas event handler that can happen if the tool unloaded?
        pass
        
  def displayOSGR(self, point):
  
    self.checkTransform()
        
    if self.canvasCrs != self.osgbCrs:
        transPoint = self.transformCrs.transform(point)
    else:
        transPoint = point
   
    #Save the current point
    self.easting = transPoint.x()
    self.northing = transPoint.y()
    
    #Show the grid square if appropriate   
    self.leOSGR.setText(self.osgr.grFromEN(transPoint.x(),transPoint.y(), self.grPrecision))
    self.clearMapGraphics()
    
    if self.canvasCrs == self.osgbCrs: #Only do this for OSGB
        if (self.leOSGR.text() != "" and self.cbGRShowSquare.isChecked()):
        
            x0 = (transPoint.x()//self.grPrecision) * self.grPrecision
            y0 = (transPoint.y()//self.grPrecision) * self.grPrecision
            r = QgsRubberBand(self.canvas, False)  # False = a polyline
            points = [QgsPoint(x0,y0), QgsPoint(x0,y0 + self.grPrecision), QgsPoint(x0 + self.grPrecision, y0 + self.grPrecision), QgsPoint(x0 + self.grPrecision,y0), QgsPoint(x0,y0)]
            
            #transPoints = transformCrs.transform(QgsGeometry.fromPolyline(points), ReverseTransform )
            #r.setToGeometry(transPoints)
            r.setToGeometry(QgsGeometry.fromPolyline(points), None)
            r.setColor(self.grColour)
            r.setWidth(2)
            self.rbGridSquare = r
        
  def canvasClicked(self, point, button):
    self.displayOSGR(point)
    
  def __unload(self):
    self.clearMapGraphics()