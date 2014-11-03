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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from osgr import *

class osgrLayer(QObject):

  progChange = pyqtSignal(int)
  progMax = pyqtSignal(int)
  gridComplete = pyqtSignal()

  def __init__(self, iface):
  
    super(osgrLayer,self).__init__()
    self.canvas = iface.mapCanvas()
    self.iface = iface
    
    # Get a reference to an osgr object
    self.osgr = osgr()
    
  def createLayer(self):
  
    # Create layer
    self.vl = QgsVectorLayer("Polygon?crs=epsg:27700", "OSGR grid squares", "memory")
    self.pr = self.vl.dataProvider()
    
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

  def boxDragged(self, xMin, yMin, xMax, yMax, selectedFeatures):
    
    self.canvas.setRenderFlag(False)
    
    # If layer is not present, create it
    try:
       self.vl.startEditing()
    except:
        # Create grid layer
       self.createLayer()
       self.vl.startEditing()
    
    # Build the grid
    llx = (xMin // self.precision) * self.precision
    lly= (yMin // self.precision) * self.precision
    
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
            gr = self.osgr.grFromEN(x,y,self.precision)
            if gr <> "":
                points = [[QgsPoint(x,y), QgsPoint(x,y + self.precision), QgsPoint(x + self.precision,y + self.precision), QgsPoint(x + self.precision,y)]]
                fet = QgsFeature()
                fet.setGeometry(QgsGeometry.fromPolygon(points))
                fet.setAttributes([self.precisionText, self.osgr.grFromEN(x,y,self.precision)])
                #self.pr.addFeatures([fet])
                
                # If the selected features list is not empty, ensure that square overlaps feature before adding
                if len(selectedFeatures) > 0:
                    for ftrSelected in selectedFeatures:
                        geom = ftrSelected.geometry()
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
    
    