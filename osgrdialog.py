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
from . import ui_osgr
import os.path
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from . import osgr
from . import osgrLayer
from . import drag_box_tool

class OsgrDialog(QWidget, ui_osgr.Ui_osgr):
    
  def __init__(self, iface, dockwidget):
    QWidget.__init__(self)
    ui_osgr.Ui_osgr.__init__(self)
    self.setupUi(self)
    self.canvas = iface.mapCanvas()
    self.iface = iface
    self.rbGridSquare = QgsRubberBand(self.canvas, False)

    # Get a reference to an osgr object and an osgrLayer object
    self.osgr = osgr.osgr()
    self.osgrLayer = osgrLayer.osgrLayer(iface)
    
    # Make a coordinate translator. Also need global references to OSGB and canvas CRSs since
    # they cannot be retrieved from a translator object.
    self.canvasCrs = self.canvas.mapSettings().destinationCrs()
    self.osgbCrs = QgsCoordinateReferenceSystem("EPSG:27700")
    self.transformCrs = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), QgsCoordinateReferenceSystem("EPSG:27700"),  QgsProject.instance())
    
    # Set the button graphics
    self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
    self.butGridTool.setIcon(QIcon( self.pathPlugin % "images/osgr.png" ))
    self.butGridPoly.setIcon(QIcon( self.pathPlugin % "images/osgrPoly.png" ))
    self.butClear.setIcon(QIcon( self.pathPlugin % "images/cross.png" ))
    self.butHelp.setIcon(QIcon( self.pathPlugin % "images/info.png" ))
    self.butGithub.setIcon(QIcon( self.pathPlugin % "images/github.png" ))
    
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
    self.dsbGridSize.valueChanged.connect(self.setPrecision)
    self.butHelp.clicked.connect(self.helpFile)
    self.butGithub.clicked.connect(self.github)
    
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
    self.dragTool = drag_box_tool.RectangleMapTool(self.canvas, self.iface)
    self.dragTool.boxDragged.connect(self.boxDragged)
    
    # Initialisations
    self.easting = 0
    self.northing = 0
    self.LabelChecked()
    self.grPrecision = 0
    self.cboPrecisionChanged(0)
  
  def helpFile(self):
        QDesktopServices().openUrl(QUrl("http://www.tombio.uk/qgisosgrtool"))

  def github(self):
        QDesktopServices().openUrl(QUrl("https://github.com/burkmarr/QGIS-Biological-Recording-Tools/issues"))
        
  def infoMessage(self, strMessage):
    self.iface.messageBar().pushMessage("Info", strMessage, level=Qgis.Info)

  def warningMessage(self, strMessage):
    self.iface.messageBar().pushMessage("Warning", strMessage, level=Qgis.Warning)
 
  def setEnableDisable(self):
    if self.cboPrecision.currentIndex() == 8:
        # User-defined grid-size selected
        self.dsbGridSize.setEnabled(True)
    else:
        self.dsbGridSize.setValue(0)
        self.dsbGridSize.setEnabled(False)
        
  def gridControlsEnable(self):
    self.gridControlsEnableDisable(True)
    
  def gridControlsEnableDisable(self, bool):
    self.butGridPoly.setEnabled(bool)
    self.butGridTool.setEnabled(bool)
    self.butClear.setEnabled(bool)
    self.cbLabel.setEnabled(bool)
    
  def setPrecision(self, value):
    self.precision = value
    self.grPrecision = value
    self.osgrLayer.setPrecision(value)
    self.osgrLayer.setPrecisionText(self.cboPrecision.currentText())
    
  def isUserDefinedGrid(self):
    return (self.dsbGridSize.value() > 0)
    
  def isOSGB(self, showMessage=False):
    self.checkTransform()
    if self.canvasCrs != self.osgbCrs:
        if showMessage:
            self.iface.messageBar().pushMessage("Info", "The map canvas CRS needs to be set to EPSG:27700 for this function", level=Qgis.Warning)
        return False
    else:
        return True
        
  def checkTransform(self):
    if self.canvasCrs != self.canvas.mapSettings().destinationCrs():
        self.canvasCrs = self.canvas.mapSettings().destinationCrs()
        self.transformCrs = QgsCoordinateTransform(self.canvasCrs, self.osgbCrs, QgsProject.instance())
    
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
    self.canvas.refresh()

  def butGridToolClicked(self, pos):
    # Make the GR tool the current map tool
    if self.butGridTool.isChecked():
      self.canvas.setMapTool(self.dragTool)
    else:
      self.canvas.unsetMapTool(self.dragTool)
      
  def boxDragged(self):
    self.GenerateSquares(self.dragTool.xMinimum, self.dragTool.yMinimum, self.dragTool.xMaximum, self.dragTool.yMaximum)
    
  def GridPoly(self):
  
    # Only do the grid poly if map CRS is OSGB or if the the grid is of
    # a user defined, precision.
    if not self.isOSGB() and not self.isUserDefinedGrid():
        self.warningMessage("The project map CRS must be OSGB *or* you must be using a user-defined grid size")
        return
        
    layer = self.iface.activeLayer()
    if layer.type() == QgsMapLayer.VectorLayer:
        selectedFeatures = layer.selectedFeatures()
        if len(selectedFeatures) > 0:
            rectLayer = layer.boundingBoxOfSelected()
 
            # The selected features layer could be in any CRS. If it's not the same as the canvas CRS
            # we will have to transform the selected features.
            # We transform the bounding rectangle here and pass the transformation object
            # to the osgrLayer to transform the selected feature geometries.

            ##? Why not transform the actual geometry of the selected feature rather than it's BBox?##
            
            if self.canvas.mapSettings().destinationCrs() !=  layer.crs():
                #QgsMessageLog.logMessage("CRS transform", "OSGR Tool")
                trans = QgsCoordinateTransform(layer.crs(), self.canvas.mapSettings().destinationCrs(), QgsProject.instance())
                try:
                    rect = trans.transform(rectLayer)
                except:
                    self.iface.messageBar().pushMessage("Warning", "The bounding rectangle of the selected feature cannot be transformed from its layer's CRS to the current map CRS.", level=Qgis.Warning)
                    return
            else:
                trans = None
                rect = rectLayer
                
            self.GenerateSquares(rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum(), selectedFeatures, trans)
        else:
            self.iface.messageBar().pushMessage("Info", "There are no features selected in the active layer.", level=Qgis.Info)
    else:
        self.iface.messageBar().pushMessage("Info", "The active layer is not a vector layer.", level=Qgis.Info)
    
  def GenerateSquares(self, xMin, yMin, xMax, yMax, selectedFeatures=[], trans=None):
  
    if not self.isOSGB() and not self.isUserDefinedGrid():
        self.warningMessage("The project map CRS must be OSGB *or* you must be using a user-defined grid size")
        return
        
    if self.precision == 0:
        self.infoMessage("User-defined grid size must be greater than zero")
        return
        
    if self.osgrLayer.getCRS() != None and self.canvas.mapSettings().destinationCrs() != self.osgrLayer.getCRS():
        self.warningMessage("The grid layer CRS does not match the project map CRS. First delete the grid layer.")
        return
        
    llx = (xMin // self.precision) * self.precision
    lly = (yMin // self.precision) * self.precision
    
    iSquares = (((xMax - llx) // self.precision + 1) * ((yMax - lly) // self.precision + 1))
    if iSquares > 1000:
        ret = QMessageBox.warning(self, "Warning",
                "Large area specified relative to the precision (" + self.cboPrecision.currentText() + "). This could generate up to " + str(int(iSquares)) + " grid squares which could take some time. Do you want to continue? (You can interrupt with the Cancel button.)",
                QMessageBox.Ok, QMessageBox.Cancel)
        if ret == QMessageBox.Cancel:
            return
    self.gridControlsEnableDisable(False)
    
    self.osgrLayer.boxDragged(xMin, yMin, xMax, yMax, selectedFeatures, self.isOSGB(), trans)
     
  def butLocateClicked(self, pos):
  
    # The functionality to locate by grid reference 
    # is only available in map canvas is OSGB
    if not self.isOSGB(True):
        return
        
    res = self.osgr.enFromGR(self.leOSGR.text())
    
    if res[0] == 0:
        self.iface.messageBar().pushMessage("Warning", res[3], level=Qgis.Warning)
    else:
        precision = res[2]
        x0 = (res[0] - precision / 1.8)
        x1 = (res[0] + precision / 1.8)
        y0 = (res[1] - precision / 1.8)
        y1 = (res[1] + precision / 1.8)
        
        ll = QgsPointXY(x0, y0)
        ur = QgsPointXY(x1, y1)
        rect = QgsRectangle(ll, ur)
        centre = QgsPointXY(res[0], res[1])
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
    elif self.cboPrecision.currentIndex() == 7:
        precision = 100000
        colour = QColor(0,0,255)
    else:
        #User defined grid square
        precision = self.dsbGridSize.value()
        colour = QColor(255,0,255)
      
    self.setEnableDisable() #Must come before precision set
    self.setPrecision(precision)
    self.grColour = colour
    self.displayOSGR(QgsPoint(self.easting,self.northing))

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
        #pass
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
        
    #Transform the map canvas points if maps canvas is not set to OSGB
    #UNLESS a user-defined grid is set - this always works in the CRS
    #of the map canvas
    if self.canvasCrs != self.osgbCrs and not self.isUserDefinedGrid():
        try:
            transPoint = self.transformCrs.transform(point)
        except:
            self.leOSGR.setText("")
            self.clearMapGraphics()
            return
    else:
        transPoint = point
   
    #Save the current point
    self.easting = transPoint.x()
    self.northing = transPoint.y()
    
    gr = self.osgr.grFromEN(transPoint.x(),transPoint.y(), self.grPrecision)
    if gr != "na":
        self.leOSGR.setText(gr)
    else:
        self.leOSGR.setText("")
            
    #Show the grid square if appropriate 
    self.clearMapGraphics()
    
    #Only do this for canvas in OSGB or if there's a user-defined grid size
    if self.canvasCrs == self.osgbCrs or self.isUserDefinedGrid(): 
         
        #if (self.leOSGR.text() != "" or self.isUserDefinedGrid()) and self.cbGRShowSquare.isChecked():
        if self.cbGRShowSquare.isChecked() and self.grPrecision > 0:
        
            x0 = (transPoint.x()//self.grPrecision) * self.grPrecision
            y0 = (transPoint.y()//self.grPrecision) * self.grPrecision
            r = QgsRubberBand(self.canvas, False)  # False = a polyline
            points = [QgsPoint(x0,y0), QgsPoint(x0,y0 + self.grPrecision), QgsPoint(x0 + self.grPrecision, y0 + self.grPrecision), QgsPoint(x0 + self.grPrecision,y0), QgsPoint(x0,y0)]
            
            r.setToGeometry(QgsGeometry.fromPolyline(points), None)
            r.setColor(self.grColour)
            r.setWidth(2)
            self.rbGridSquare = r
           
  def canvasClicked(self, point, button):
    self.displayOSGR(point)
    
  def __unload(self):
    self.clearMapGraphics()