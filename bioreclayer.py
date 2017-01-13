# -*- coding: utf-8 -*-
"""
/***************************************************************************
bioreclayer
        A class for representing biological records as a GIS layer
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
from projection import *
from envmanager import *

class biorecLayer(QObject):

    def __init__(self, iface, model, pteLog):
  
        super(biorecLayer,self).__init__()
        self.canvas = iface.mapCanvas()
        self.iface = iface
        
        # Store passed parameters
        self.model = model
        self.pteLog = pteLog
        
        # Other defaults
        self.name = "Biological records"
        self.transparency = 0
        self.iColAb = 0
        self.iColTaxa = 0
        self.iColGr = 0
        self.iColX = 0
        self.iColY = 0
        self.gridSize = 0
        
        # Get a reference to an osgr object
        self.osgr = osgr()
        # Get a reference to a projection object
        self.projection = None
        
        # Load the environment stuff
        self.env = envManager()
        
        self.vl = None  
        
        self.translationError = ""
        
    def infoMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Info", strMessage, level=QgsMessageBar.INFO)
        
    def warningMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Warning", strMessage, level=QgsMessageBar.WARNING)
    
    def getVectorLayer(self):
        return self.vl
        
    def setName(self, name):
        self.name = name
        
    def getName(self):
        return self.name
        
    def setTaxa(self, taxa):
        self.taxa = taxa
        
    def setColTaxa(self, iColTaxa):
        self.iColTaxa = iColTaxa
        
    def setColAb(self, iColAb):
        self.iColAb = iColAb
        
    def setColGr(self, iColGr):
        self.iColGr = iColGr
        
    def setColX(self, iColX):
        self.iColX = iColX
        
    def setColY(self, iColY):
        self.iColY = iColY
        
    def setCrs(self, crs):
        self.projection = projection(QgsCoordinateReferenceSystem(crs), self.canvas.mapRenderer().destinationCrs())
        
    def setGridSize(self, gridSize):
        self.gridSize = gridSize
        
    def setTransparency(self, transparency):
        self.transparency = transparency
        if not self.vl is None:
            # If the layer has already been removed via native QGIS, this will fail
            try:
                 self.vl.setLayerTransparency(self.transparency)
            except:
                pass
            
    def createMapLayer(self, mapType, symbolType, styleFile=None):
        
        # Create layer
        if self.iColGr > 0:
            epsg = "epsg:27700"
        else:
            epsg = self.canvas.mapRenderer().destinationCrs().authid()
        
        if mapType == "Records as points":
            self.vl = QgsVectorLayer("Point?crs=" + epsg, self.name, "memory")
        else:
            self.vl = QgsVectorLayer("Polygon?crs=" + epsg, self.name, "memory")
        
        self.pr = self.vl.dataProvider()
        self.vl.setLayerTransparency(self.transparency)
        
        #if not symbolStyle is None:
        #    self.vl.setRendererV2( QgsSingleSymbolRendererV2( symbolStyle ) ) 
        
        if not styleFile is None:
            self.vl.loadNamedStyle(styleFile)
        
        # Add to map layer registry
        #QgsMapLayerRegistry.instance().addMapLayer(self.vl)
    
        # Create the geometry and attributes
        if mapType.startswith("Records"):
            self.addFieldsToTable(mapType)
        else:
            self.addFieldsToAtlas(mapType, symbolType)
            
    def startEditing(self):
        # If the layer has already been removed via native QGIS, this will fail
        try:
            self.vl.startEditing()
        except:
            pass
        
    def rollBack(self):
        # If the layer has already been removed via native QGIS, this will fail
        try:
            self.vl.rollBack()
        except:
            pass
             
    def setVisibility(self, bVisibility):
        # If the layer has already been removed via native QGIS, this will fail
        try:
            self.iface.legendInterface().setLayerVisible(self.vl, bVisibility)
        except:
            pass
            
    def setExpanded(self, bExpanded):
         # If the layer has already been removed via native QGIS, this will fail
        try:
            self.iface.legendInterface().setLayerExpanded(self.vl, bExpanded)
        except:
            pass
  
    def removeFromMap(self):
        # Remove from layer
        # If the layer has already been removed via native QGIS, this will fail
        try:
            QgsMapLayerRegistry.instance().removeMapLayer(self.vl.id())
        except:
            pass
        
    def getID(self):
        if self.vl is None:
            return None
        else:
            try:
                id = self.vl.id()
            except:
                id = None
            return id
            
    def addFieldsToTable(self, mapType):
        # This procedure makes a map of either points or squares - one for each record.
        iCols = 0
        for i in range(self.model.columnCount()):
            attr = self.model.horizontalHeaderItem(i).text()
            if attr != "":
                #self.pteLog.appendPlainText("Col " + attr)
                
                bIsNumeric = False
                for colNumeric in self.env.getEnvValues("biorec.intcol"):
                    if attr == colNumeric:
                        self.pr.addAttributes([QgsField(attr, QVariant.Int)])
                        bIsNumeric = True
                        break
                for colNumeric in self.env.getEnvValues("biorec.dblcol"):
                    if attr == colNumeric:
                        self.pr.addAttributes([QgsField(attr, QVariant.Double)])
                        bIsNumeric = True
                        break
                if not bIsNumeric: 
                    self.pr.addAttributes([QgsField(attr, QVariant.String)]) #book
                iCols += 1

        self.vl.startEditing()
            
        fets = []
        for i in range(self.model.rowCount()):
            if self.includeTaxon(i):
                geom = None
                if self.iColGr > 0:
                    if not self.model.item(i, self.iColGr) is None:
                        #Get geometry from OSGR
                        gr = self.model.item(i, self.iColGr).text()
                        if mapType == "Records as points":
                            geom = self.osgr.geomFromGR(gr, "point")
                        else:
                            geom = self.osgr.geomFromGR(gr, "square")
                else:
                    if not self.model.item(i, self.iColX) is None and not self.model.item(i, self.iColY) is None:
                        #Get point geometry from X, Y etc
                        try:
                            x = float(self.model.item(i, self.iColX).text())
                            y = float(self.model.item(i, self.iColY).text())
                        except:
                            x = None
                            y = None
                            
                        if x != None and y != None:
                            ret = self.projection.xyToPoint(x, y)
                            geom = ret[0]
                            err = ret[1]
                        
                        if geom == None:
                            self.pteLog.appendPlainText(err)
                            errMap = "Translation errors - see log tab"
                            if errMap != self.translationError:
                                #self.warningMessage(errMap)
                                self.translationError = errMap
                                
                if geom != None:
                    fet = QgsFeature()
                    fet.setGeometry(geom)
                    
                    attrs = []
                    for j in range(iCols):
                        attr = self.model.item(i,j) # attr is a QStandardItem
                        if not attr is None:
                            attrs.append(attr.text())
                    fet.setAttributes(attrs)
                    fets.append(fet)
                    
        self.vl.addFeatures(fets)
        self.vl.commitChanges()
        self.vl.updateExtents()
        self.vl.removeSelection()
        self.translationError = ""
        
    def addFieldsToAtlas(self, mapType, symbolType):
        # This procedure makes an atlas map
        self.pr.addAttributes([QgsField("GridRef", QVariant.String)])
        self.pr.addAttributes([QgsField("Records", QVariant.Int)])
        self.pr.addAttributes([QgsField("Abundance", QVariant.Int)])
            
        self.vl.startEditing()
        fetsDict = {}
        
        if mapType.startswith("10 m"):
            gridPrecision = 10
        elif mapType.startswith("100 m"):
            gridPrecision = 100
        elif mapType.startswith("1 km"):
            gridPrecision = 1000
        elif mapType.startswith("2 km"):
            gridPrecision = 2000
        elif mapType.startswith("5 km"):
            gridPrecision = 5000
        elif mapType.startswith("10 km"):
            gridPrecision = 10000
        else:
            gridPrecision = self.gridSize
            
        if symbolType == "Atlas squares":
            symbol = "square"
        else:
            symbol = "circle"
                    
        for i in range(self.model.rowCount()):
            
            if self.includeTaxon(i):
                
                if self.iColGr > 0:
                    xOriginal = None
                    yOriginal = None
                    # Geocoding from OS grid ref
                    if self.model.item(i, self.iColGr) == None:
                        grOriginal = None
                    else:
                        grOriginal = self.model.item(i, self.iColGr).text()
                else:
                    grOriginal = None
                    # Geocoding from x and y
                    if self.model.item(i, self.iColX) == None or self.model.item(i, self.iColY) == None:
                        xOriginal = None
                        yOriginal = None
                    else:
                        xOriginal = self.model.item(i, self.iColX).text()
                        yOriginal = self.model.item(i, self.iColY).text()
               
                if not (self.iColGr > 0 and grOriginal == None) and not (self.iColGr == 0 and xOriginal == None):

                    # Get a value for abundance
                    if self.iColAb == -1:
                        abundance = 1
                    else:
                        if self.model.item(i, self.iColAb) == None:
                            abundance = 1
                        else:
                            try:
                                abundance = int(self.model.item(i, self.iColAb).text())
                                if abundance < 1:
                                    abundance = 1
                                #self.pteLog.appendPlainText(str(i) + ">>" + self.model.item(i, self.iColAb).text() + "<<>>" +str(abundance) + "<<")
                            except:
                                abundance = 1
                    
                    if self.iColGr > 0:
                        # Get atlas geometry from grid reference
                        ret = self.osgr.convertGr(grOriginal, gridPrecision)
                        if ret[1] != "":
                            self.pteLog.appendPlainText(ret[1])
                        gr = ret[0]
                        geom = self.osgr.geomFromGR(gr, symbol)
                    else:
                        # Get atlas geometry from x & y
                        ret = self.projection.xyToGridGeom(xOriginal, yOriginal, gridPrecision, symbol)
                        if ret[2] != "":
                            self.pteLog.appendPlainText(ret[2])
                            err = "Translation errors - see log tab"
                            if self.translationError != err:
                                #self.warningMessage(err)
                                self.translationError = err
                        gr = ret[0]
                        geom = ret[1]
                    
                    if not geom is None:
                        if fetsDict.get(gr, None) == None:
                            fetsDict[gr] = [geom, 1, abundance]
                        else:
                            #Records
                            fetsDict[gr][1]+=1
                            #Abundance
                            fetsDict[gr][2]+=abundance
                            
        # Now loop through the dictionary and create a feature for each one
        fets=[]
        for gr in fetsDict:
            fetDict = fetsDict[gr]
            fet = QgsFeature()
            fet.setGeometry(fetDict[0])
            attrs = [gr, fetDict[1], fetDict[2]]
            fet.setAttributes(attrs)
            fets.append(fet)
                
        self.vl.addFeatures(fets)
        self.vl.commitChanges()
        self.vl.updateExtents()
        self.vl.removeSelection()
        self.translationError = ""

    def includeTaxon(self, i):
        # Check if taxa is in list
       
        if len(self.taxa) == 0:
            return(True)
    
        taxon = self.model.item(i, self.iColTaxa).text()
        
        if taxon in self.taxa:
            return(True)
        else:
            return(False)
        