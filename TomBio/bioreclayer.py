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
from envmanager import *

class biorecLayer(QObject):

    def __init__(self, iface, iColGr, iColAb, model, pteLog):
  
        super(biorecLayer,self).__init__()
        self.canvas = iface.mapCanvas()
        self.iface = iface
        
        # Store passed parameters
        
        self.model = model
        self.pteLog = pteLog
        self.iColGr = iColGr
        self.iColAb = iColAb
        
        # Other defaults
        self.name = "Biological records"
        self.iColTaxa = 0
        self.transparency = 0
        
        # Get a reference to an osgr object
        self.osgr = osgr()
        
        # Load the environment stuff
        self.env = envManager()
        
    def setName(self, name):
        self.name = name
        
    def setTaxa(self, taxa):
        self.taxa = taxa
        
    def setColTaxa(self, iColTaxa):
        self.iColTaxa = iColTaxa
        
    def setTransparency(self, transparency):
        self.transparency = transparency
        
    def createMapLayer(self, mapType, symbolType, styleFile=None):
        
        # Create layer
        if mapType == "Records as points":
            self.vl = QgsVectorLayer("Point?crs=epsg:27700", self.name, "memory")
        else:
            self.vl = QgsVectorLayer("Polygon?crs=epsg:27700", self.name, "memory")
        
        self.pr = self.vl.dataProvider()
        self.vl.setLayerTransparency(self.transparency)
        
        #if not symbolStyle is None:
        #    self.vl.setRendererV2( QgsSingleSymbolRendererV2( symbolStyle ) ) 
        
        if not styleFile is None:
            self.vl.loadNamedStyle(styleFile)
        
        # Add to map layer registry
        QgsMapLayerRegistry.instance().addMapLayer(self.vl)
    
        # Create the geometry and attributes
        if mapType.startswith("Records"):
            self.addFieldsToTable(mapType)
        else:
            self.addFieldsToAtlas(mapType, symbolType)
            
    def setVisibility(self, bVisibility):
        self.iface.legendInterface().setLayerVisible(self.vl, bVisibility)
        
    def setExpanded(self, bExpanded):
        self.iface.legendInterface().setLayerExpanded(self.vl, bExpanded)
  
    def removeFromMap(self):
        # Remove from layer
        # If the layer has already been removed via native QGIS, this will fail
        try:
            QgsMapLayerRegistry.instance().removeMapLayer(self.vl.id())
        except:
            pass
        
    def addFieldsToTable(self, mapType):
        
        #self.pteLog.appendPlainText("Add fields to table reached ")
        
        iCols = 0
        for i in range(self.model.columnCount()):
            attr = self.model.horizontalHeaderItem(i).text()
            if attr != "":
                #self.pteLog.appendPlainText("Col " + attr)
                
                # Set default value for Taxon column
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
            
        self.canvas.setRenderFlag(False)
        self.vl.startEditing()
            
        fets = []
        for i in range(self.model.rowCount()):
            if self.includeTaxon(i):
            
                if not self.model.item(i, self.iColGr) is None:
                
                    gr = self.model.item(i, self.iColGr).text()
                    
                    #self.pteLog.appendPlainText("gr IS " + gr)
                    
                    if mapType == "Records as points":
                        geom = self.osgr.geomFromGR(gr, "point")
                    else:
                        geom = self.osgr.geomFromGR(gr, "square")
                        
                    if geom != None:
                        #self.pteLog.appendPlainText("make feature")
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
        self.canvas.setRenderFlag(True)
        
    def addFieldsToAtlas(self, mapType, symbolType):
        
        self.pr.addAttributes([QgsField("GridRef", QVariant.String)])
        self.pr.addAttributes([QgsField("Records", QVariant.Int)])
        self.pr.addAttributes([QgsField("Abundance", QVariant.Int)])
            
        self.canvas.setRenderFlag(False)
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
            gridPrecision = 100000
            
        if symbolType == "Atlas squares":
            symbol = "square"
        else:
            symbol = "circle"
                    
        for i in range(self.model.rowCount()):
            
            if self.includeTaxon(i):
                
                if not self.model.item(i, self.iColGr) is None:
                
                    grOriginal = self.model.item(i, self.iColGr).text()
                    
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
                                
                            
                    
                    ret = self.osgr.convertGr(grOriginal, gridPrecision)
                    if ret[1] != "":
                        self.pteLog.appendPlainText(ret[1])
                        
                    gr = ret[0]
                    geom = self.osgr.geomFromGR(gr, symbol)
                    
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
        self.canvas.setRenderFlag(True)

    def includeTaxon(self, i):
        # Check if taxa is in list
       
        if len(self.taxa) == 0:
            return(True)
    
        taxon = self.model.item(i, self.iColTaxa).text()
        
        if taxon in self.taxa:
            return(True)
        else:
            return(False)
        