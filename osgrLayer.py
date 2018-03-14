# -*- coding: utf-8 -*-
"""
/***************************************************************************
 osgrLayer
        A class for handling grid squares generated 'on the fly'
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
    self.iface.messageBar().pushMessage("Info", strMessage, level=QgsMessageBar.INFO)
    
  def createLayer(self):
  
    # Create layer with the same CRS as the canvas.
    # Need to find a way to create a layer with specified CRS other than by EPSG string
    # because this is retained in general layer properties even after CRS is changed.
    # If layer created without CRS, the user is prompted to select one so that's not an option.
    self.vl = QgsVectorLayer("Polygon?epsg:27700", "OSGR grid squares", "memory")
    self.vl.setCrs(self.canvas.mapRenderer().destinationCrs())
    self.pr = self.vl.dataProvider()
    
    #QgsMessageLog.logMessage(self.canvas.mapRenderer()., "OSGR Tool")

    # Add fields
    self.pr.addAttributes( [ QgsField("GridType", QVariant.String), QgsField("GridRef", QVariant.String) ] )
    
    # Symbology
    
    props = { 'color_border' : '0,0,0,200', 'style' : 'no', 'style_border' : 'solid' }
    s = QgsFillSymbolV2.createSimple(props)
    self.vl.setRendererV2( QgsSingleSymbolRendererV2( s ) )
    
    # Labeling
    self.vl.setCustomProperty("labeling", "pal")
    self.vl.setCustomProperty("labeling/fontFamily", "Arial")
    self.vl.setCustomProperty("labeling/fontSize", "8")
    self.vl.setCustomProperty("labeling/fieldName", "GridRef")
    self.vl.setCustomProperty("labeling/placement", "1")
    if self.showLabels:
        self.vl.setCustomProperty("labeling/enabled", "true")
    else:
        self.vl.setCustomProperty("labeling/enabled", "false")
    
    # Add to map layer registry
    QgsMapLayerRegistry.instance().addMapLayer(self.vl)
    
  def clear(self):
    try:
        QgsMapLayerRegistry.instance().removeMapLayer(self.vl.id())
    except:
        pass
    
  def setPrecision(self, precision):
    self.precision = precision
  
  def setPrecisionText(self, precisionText):
    self.precisionText = precisionText
    
  def setShowLabels(self, boolShowLabels):
    self.showLabels = boolShowLabels
    try:
        if self.showLabels:
            self.vl.setCustomProperty("labeling/enabled", "true")
        else:
            self.vl.setCustomProperty("labeling/enabled", "false")
        self.vl.triggerRepaint()
    except:
        pass
        
  def cancelGrid(self):
    self.cancel = True

  def boxDragged(self, xMin, yMin, xMax, yMax, selectedFeatures=[], isOSGB=False, trans=None):
    
    self.canvas.setRenderFlag(False)
    
    # If selectedFeatures is not empty, then extract geometry to a list.
    # Also transform geometry if trans object is not empty. The trans object will transform from the
    # projection of the selected layer to the projection of the map canvas.
    # If the selected features list is not empty, ensure that square overlaps feature before adding
    selectedGeometries = []
    if len(selectedFeatures) > 0:
        for ftrSelected in selectedFeatures:
            geom = ftrSelected.geometry()
            if not trans is None:
                try:
                    geom.transform(trans)
                except:
                    pass
            selectedGeometries.append(geom)

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
            
            if isOSGB:
                # This may return string 'na' if the precision 
                # is not a valid one for OSGR.
                gr = self.osgr.grFromEN(x,y,self.precision)
            else:
                gr = ""
                
            # If not projection is OSGB then always make a square (subject to overlap where appropriate).
            # If projection is OSGB then only make a square if valid GR or precision not standard
            # OSGB precision (denoted by 'na' in GR).
            
            if not isOSGB or (isOSGB and gr != ""):
                        
                #self.infoMessage("gr is " + gr + " precision is " + str(self.precision))
                
                points = [[QgsPoint(x,y), QgsPoint(x,y + self.precision), QgsPoint(x + self.precision,y + self.precision), QgsPoint(x + self.precision,y)]]
                fet = QgsFeature()
                fet.setGeometry(QgsGeometry.fromPolygon(points))
                
                if gr != "na":
                    fet.setAttributes([self.precisionText, gr])
                    #self.pr.addFeatures([fet])
                else:
                    fet.setAttributes([self.precisionText, ""])
                
                # If the selected geometry list is not empty, ensure that square overlaps geometry before adding
                if len(selectedGeometries) > 0:
                    for geom in selectedGeometries:
                        if geom.intersects(fet.geometry()):
                            self.vl.addFeatures([fet])
                            break
                else:
                    self.vl.addFeatures([fet])
                    
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
    #self.vl.triggerRepaint()
    
    