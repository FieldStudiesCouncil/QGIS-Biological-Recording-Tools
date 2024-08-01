# -*- coding: utf-8 -*-
"""
/***************************************************************************
 osgrLayer
        A class for handling grid squares generated 'on the fly'
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
from PyQt5.QtNetwork import *
#from osgr import *
#from envmanager import *
from . import osgr
from . import envmanager

class osgrLayer(QObject):

  progChange = pyqtSignal(int)
  progMax = pyqtSignal(int)
  gridComplete = pyqtSignal()

  def __init__(self, iface):
  
    super(osgrLayer,self).__init__()
    self.canvas = iface.mapCanvas()
    self.iface = iface
   
    # Get a reference to an osgr object
    self.osgr = osgr.osgr()
    self.vl = None

  def getCRS(self):
    if self.vl is None:
        return None
    else:
        try:
            #Vector layer Could have been removed
            return self.vl.crs()
        except:
            return None
    
  def infoMessage(self, strMessage):
    self.iface.messageBar().pushMessage("Info", strMessage, level=Qgis.Info)
    
  def logMessage(self, strMessage, level=Qgis.Info):
        QgsMessageLog.logMessage(strMessage, "OSGR Tool", level)

  def createLayer(self):
  
    # Create layer with the same CRS as the canvas.
    # Need to find a way to create a layer with specified CRS other than by EPSG string
    # because this is retained in general layer properties even after CRS is changed.
    # If layer created without CRS, the user is prompted to select one so that's not an option.
    #self.vl = QgsVectorLayer("Polygon?epsg:27700", "OSGR grid squares", "memory")
    #self.vl.setCrs(self.canvas.mapSettings().destinationCrs())

    QgsMessageLog.logMessage(self.canvas.mapSettings().destinationCrs().authid(), "OSGR Tool")

    self.vl = QgsVectorLayer("Polygon?crs=" + self.canvas.mapSettings().destinationCrs().authid() + "&field=GridType:string(22)&field=GridRef:string(12)", "OSGR grid squares", "memory")
    self.pr = self.vl.dataProvider()
    
    # Symbology
    props = { 'color_border' : '0,0,0,200', 'style' : 'no', 'style_border' : 'solid' }
    s = QgsFillSymbol.createSimple(props)
    self.vl.setRenderer( QgsSingleSymbolRenderer( s ) )
    
    # Labeling
    palyr = QgsPalLayerSettings()
    palyr.fieldName = 'GridRef' 
    palyr.placement =  Qgis.LabelPlacement.OverPoint 

    l = QgsVectorLayerSimpleLabeling(palyr)
    self.vl.setLabeling(l)

    if self.showLabels:
        self.vl.setLabelsEnabled(True)
    else:
        self.vl.setLabelsEnabled(False)
    
    # Add to map layer registry
    QgsProject.instance().addMapLayer(self.vl)
    
  def clear(self):
    try:
        QgsProject.instance().removeMapLayer(self.vl.id())
    except:
        pass
    
  def setGrType(self, grType):
    self.grType = grType

  def setPrecision(self, precision):
    self.precision = precision
  
  def setPrecisionText(self, precisionText):
    self.precisionText = precisionText
    
  def setShowLabels(self, boolShowLabels):
    self.showLabels = boolShowLabels

    if not self.vl is None:
        QgsMessageLog.logMessage("self.vl IS set", 'OSGRLayer', Qgis.Info)
        if self.showLabels:
            self.vl.setLabelsEnabled(True)
        else:
            self.vl.setLabelsEnabled(False)
        self.vl.triggerRepaint()
    else:
        QgsMessageLog.logMessage("No self.vl set", 'OSGRLayer', Qgis.Info)
    try:
        pass
    except:
        pass
        
  def cancelGrid(self):
    self.cancel = True


  def addSquare(self, gr, grType, precisionText, square):
     #Transform square to output layer CRS if required
    if grType == "os" and self.vl.crs().authid() != "EPSG:27700":
        transGrid = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:27700"), self.vl.crs(), QgsProject.instance())
    elif grType == "irish" and self.vl.crs().authid() != "EPSG:29903":
        transGrid = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:29903"), self.vl.crs(), QgsProject.instance())
    elif grType == "other" and self.vl.crs().authid() != self.canvas.mapSettings().destinationCrs().authid():
        transGrid = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), self.vl.crs(), QgsProject.instance())
    else:
        transGrid = None
    if transGrid is not None:
        square.transform(transGrid)

    fet = QgsFeature()
    fet.setGeometry(square)
                
    self.iface.messageBar().pushMessage("Info", gr, level=Qgis.Info)

    if gr != "na" and gr!="":
        fet.setAttributes([precisionText, gr])
    else:
        fet.setAttributes(["", ""])
                
    self.vl.addFeatures([fet])

  def GenerateSquares(self, xMin, yMin, xMax, yMax, selectedGeometries=[], selectedFeaturesCrs=None):
    
    self.canvas.setRenderFlag(False)

    # If layer is not present, create it
    try:
       self.vl.startEditing()
    except:
        # Create grid layer
       self.createLayer()
       self.vl.startEditing()
    
    # Apply any offsets specified in environment file
    self.env = envmanager.envManager()
    try:
        offsetX = float(self.env.getEnvValue("biorec.xGridOffset"))
    except:
        offsetX = 0

    try:
        offsetY = float(self.env.getEnvValue("biorec.yGridOffset"))
    except:
        offsetY = 0

    # Build the grid
    llx = ((xMin - offsetX) // self.precision) * self.precision + offsetX
    lly = ((yMin - offsetY) // self.precision) * self.precision + offsetY
    
    x = llx
    y = lly
    self.cancel = False
    iCount = 0
    
    xStep = (xMax - llx) // self.precision + 1
    yStep = (yMax - lly) // self.precision + 1
    
    iMax = int(xStep * yStep)
    self.progMax.emit(iMax)
    self.progChange.emit(0)
    
    while x < xMax:
        while y < yMax:
            # add a feature for the grid square (if it has a valid GR)
            
            if self.grType == "os" or self.grType == "irish":
                # This may return string 'na' if the precision 
                # is not a valid one for the grid.
                gr = self.osgr.grFromEN(x,y,self.precision, self.grType)
            else:
                gr = ""
                
            # If grid type os 'other' then always make a square (subject to overlap where appropriate).
            # If grid type is 'os' or 'irish' only make a square if valid GR
            if self.grType == "other" or  (gr != "" and gr != "na"):
                        
                points = [[QgsPointXY(x,y), QgsPointXY(x,y + self.precision), QgsPointXY(x + self.precision,y + self.precision), QgsPointXY(x + self.precision,y)]]
                square = QgsGeometry.fromPolygonXY(points)

                #At this point we have a square generated in the correct CRS - British, Irish or other (map canvas CRS)
                #and we can check to see if it overlaps with passed in geometries which have been passed in with
                #the correct CRS.
                include = False
                if len(selectedGeometries) > 0:
                    self.logMessage("testing oerlap")
                    for geom in selectedGeometries:
                        if geom.intersects(square):
                            self.logMessage("overlap found")
                            include = True
                            break
                else:
                    include = True

                if include:
                    self.addSquare(gr, self.grType, self.precisionText, square)
                    
            y += self.precision
            
            # Process other events so if user clicks cancel button, this operation is cancelled.
            iCount += 1
            self.progChange.emit(iCount)
            if iCount % 100 == 0:
                QCoreApplication.processEvents()
            if self.cancel:
                break
            
        y = lly
        x += self.precision
        if self.cancel:
            break
        
    self.cancel = False
    if self.cancel:
        self.vl.rollBack(True)
    else:
        # Commit changes
        self.vl.commitChanges()
        # update layer's extent when new features have been added
        # because change of extent in provider is not propagated to the layer
        self.vl.updateExtents()
        
    self.vl.removeSelection()
    self.canvas.setRenderFlag(True)
    self.progChange.emit(0)
    self.gridComplete.emit()

  def GenerateSquaresFromArray(self, grs):
    
    self.canvas.setRenderFlag(False)

    # If layer is not present, create it
    try:
       self.vl.startEditing()
    except:
        # Create grid layer
       self.createLayer()
       self.vl.startEditing()
    
    # Apply any offsets specified in environment file
    self.env = envmanager.envManager()
    try:
        offsetX = float(self.env.getEnvValue("biorec.xGridOffset"))
    except:
        offsetX = 0

    try:
        offsetY = float(self.env.getEnvValue("biorec.yGridOffset"))
    except:
        offsetY = 0

    self.cancel = False
    iCount = 0
    iMax = len(grs)
    self.progMax.emit(iMax)
    self.progChange.emit(0)
    
    for gr in grs:

        ret = self.osgr.checkGR(gr)
        precisionText = ret[1]
        grType = ret[2]

        if grType == "os":
            crs = "EPSG:27700"
        elif grType == "irish":
            crs = "EPSG:29903"
        else:
            crs = None
        
        if crs is not None:

            self.logMessage("processing " + gr + " " + crs)

            square = self.osgr.geomFromGR(gr, "square", crs)
            self.addSquare(gr, grType, precisionText, square)

        # Process other events so if user clicks cancel button, this operation is cancelled.
        iCount += 1
        self.progChange.emit(iCount)
        if iCount % 100 == 0:
            QCoreApplication.processEvents()
        if self.cancel:
            break

    self.cancel = False
    if self.cancel:
        self.vl.rollBack(True)
    else:
        # Commit changes
        self.vl.commitChanges()
        # update layer's extent when new features have been added
        # because change of extent in provider is not propagated to the layer
        self.vl.updateExtents()
        
    self.vl.removeSelection()
    self.canvas.setRenderFlag(True)
    self.progChange.emit(0)
    self.gridComplete.emit()









    
    