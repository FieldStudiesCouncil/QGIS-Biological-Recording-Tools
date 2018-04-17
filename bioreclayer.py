# -*- coding: utf-8 -*-
"""
/***************************************************************************
bioreclayer
        A class for representing biological records as a GIS layer
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
from . import osgr
from . import envmanager
from . import projection

class biorecLayer(QObject):

    def __init__(self, iface, csvLayer, pteLog):
  
        super(biorecLayer,self).__init__()
        self.canvas = iface.mapCanvas()
        self.iface = iface
        
        # Store passed parameters
        self.csvLayer = csvLayer
        self.pteLog = pteLog
        
        # Other defaults
        self.name = "Biological records"
        self.transparency = 0
        self.iColAb = -1
        self.iColTaxa = -1
        self.iColGr = -1
        self.iColX = -1
        self.iColY = -1
        self.gridSize = -1
        self.taxa = []
        
        # Get a reference to an osgr object
        self.osgr = osgr.osgr()
        # Get a reference to a projection object
        self.projection = None
        self.crsInput = None
        self.crsOutput = None
        
        # Load the environment stuff
        self.env = envmanager.envManager()
        
        self.vl = None  
        
        self.translationError = ""
    
    def logMessage(self, strMessage, level=Qgis.Info):
        QgsMessageLog.logMessage(strMessage, "Biological Records Tool", level)

    def infoMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Info", strMessage, level=Qgis.Info)
        
    def warningMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Warning", strMessage, level=Qgis.Warning)
    
    def getVectorLayer(self):
        return self.vl
        
    def setName(self, name):
        self.name = name
        
    def getName(self):
        return self.name
        
    def setTaxa(self, taxa):
        # Using a set class massively improves performance
        # later when searching for specific taxa in large lists
        self.taxa = set(taxa)
        
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
        
    def setCrs(self, crsInput, crsOutput):
        #self.projection = projection.projection(QgsCoordinateReferenceSystem(crsInput), self.canvas.mapSettings().destinationCrs())
        self.projection = projection.projection(QgsCoordinateReferenceSystem(crsInput), QgsCoordinateReferenceSystem(crsOutput))
        self.crsInput = crsInput
        self.crsOutput = crsOutput
        
    def setGridSize(self, gridSize):
        self.gridSize = gridSize
        
    def setTransparency(self, transparency):
        self.transparency = transparency
        if not self.vl is None:
            # If the layer has already been removed via native QGIS, this will fail
            try:
                self.vl.setOpacity(1 - self.transparency/100)
            except:
                pass
            
    def createMapLayer(self, mapType, symbolType, styleFile=None):
        
        # Create layer
        epsg = self.crsOutput
        if mapType == "Records as points":
            self.vl = QgsVectorLayer("Point?crs=" + epsg, self.name, "memory")
        else:
            self.vl = QgsVectorLayer("Polygon?crs=" + epsg, self.name, "memory")
        
        self.pr = self.vl.dataProvider()
        
        # Style stuff
        if not styleFile is None:
            self.vl.loadNamedStyle(styleFile)
        self.vl.setOpacity(1 - self.transparency/100)
    
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
            #self.iface.legendInterface().setLayerVisible(self.vl, bVisibility)
            QgsProject.instance().layerTreeRoot().findLayer(self.vl.id()).setItemVisibilityChecked(bVisibility)
        except:
            pass
            
    def setExpanded(self, bExpanded):
        # If the layer has already been removed via native QGIS, this will fail
        try:
            #self.iface.legendInterface().setLayerExpanded(self.vl, bExpanded)
            QgsProject.instance().layerTreeRoot().findLayer(self.vl.id()).setExpanded(bExpanded)
        except:
            pass
  
    def removeFromMap(self):
        # Remove from layer
        # If the layer has already been removed via native QGIS, this will fail
        try:
            QgsProject.instance().removeMapLayer(self.vl.id())
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
        
        for field in self.csvLayer.dataProvider().fields():
            attr = field.name()
            fieldType = field.typeName()
            if attr != "":
                bIsNumeric = False
                if fieldType == "integer":
                    self.pr.addAttributes([QgsField(attr, QVariant.Int)])
                    bIsNumeric = True

                if fieldType == "double":
                    self.pr.addAttributes([QgsField(attr, QVariant.Double)])
                    bIsNumeric = True

                if not bIsNumeric: 
                    self.pr.addAttributes([QgsField(attr, QVariant.String)])

        # Set up output map layer with attributes of types 
        # specified by in environment file.
        #for field in self.csvLayer.dataProvider().fields():
            #attr = field.name()
            #if attr != "":)
                #bIsNumeric = False
                #for colNumeric in self.env.getEnvValues("biorec.intcol"):
                    #if attr == colNumeric:
                        #self.pr.addAttributes([QgsField(attr, QVariant.Int)])
                        #bIsNumeric = True
                        #break
                #for colNumeric in self.env.getEnvValues("biorec.dblcol"):
                    #if attr == colNumeric:
                        #self.pr.addAttributes([QgsField(attr, QVariant.Double)])
                        #bIsNumeric = True
                        #break
                #if not bIsNumeric: 
                    #self.pr.addAttributes([QgsField(attr, QVariant.String)])

        self.vl.startEditing()   
        
        fets = []
        
        if len(self.taxa) == 1:
            # Taxa selected, so get 
            taxonFieldName = self.csvLayer.dataProvider().fields()[self.iColTaxa].name()

            # No indexing in set class so can't use self.taxa[0]
            for taxon in self.taxa: 
                #The regular expression (~ comparison) allows for leading and trailing white space on the taxa
                strFilter = '"%s" ~ \' *%s *\'' % (taxonFieldName, taxon.replace("'", r"\'"))

            #request = QgsFeatureRequest().setFilterExpression(QgsExpression(strFilter))
            request = QgsFeatureRequest().setFilterExpression(strFilter)
            iter = self.csvLayer.getFeatures(request)
            fets = fets + self.makeFeatures(iter, mapType) 
        else:
            # No taxa selected, so get all features from CSV
            iter = self.csvLayer.getFeatures()
            if len(self.taxa) == 0: 
                fets = self.makeFeatures(iter, mapType)
            else:
                # More than one taxa selected
                fets = self.makeFeatures(iter, mapType, True)
               
        self.vl.addFeatures(fets)
        self.vl.commitChanges()
        self.vl.updateExtents()
        self.vl.removeSelection()
        self.translationError = ""
        
    def makeFeatures(self, iter, mapType, bFilterTaxaV2=False):

        fets = []
        for feature in iter:
        
            if bFilterTaxaV2:

                try:
                    taxon = feature.attributes()[self.iColTaxa].strip()
                except:
                    taxon = "invalid"
                
            if not bFilterTaxaV2:
                bTaxonOkay = True
            elif bFilterTaxaV2 and taxon in self.taxa:
                bTaxonOkay = True
            else:
                bTaxonOkay = False
            
            if bTaxonOkay:
                geom = None
                if self.iColGr > -1:
                    try:
                        gr = feature.attributes()[self.iColGr].replace(" ", "")
                    except:
                        gr = "NULL"
                        
                    if gr != "NULL":
                        #Get geometry from OSGR
                        if mapType == "Records as points":
                            geom = self.osgr.geomFromGR(gr, "point")
                        else:
                            geom = self.osgr.geomFromGR(gr, "square")
                elif self.iColX > -1:
                    try:
                        strX = str(feature.attributes()[self.iColX]).strip()
                    except:
                        strX = "NULL"
                    try:
                        strY = str(feature.attributes()[self.iColY]).strip()
                    except:
                        strY = "NULL"
                        
                    if strX != "NULL" and strY != "NULL":
                        #Get point geometry from X, Y etc
                        try:
                            x = float(strX)
                            y = float(strY)
                        except:
                            x = None
                            y = None
                            
                        if x != None and y != None:
                            ret = self.projection.xyToPoint(x, y)
                            geom = ret[0]
                            err = ret[1]
                        else:
                            err = "Invalid x and or y values"
                        
                        if geom == None:
                            self.pteLog.appendPlainText(err)
                            errMap = "Translation errors - see log tab"
                            if errMap != self.translationError:
                                #self.warningMessage(errMap)
                                self.translationError = errMap
                else:
                    #Get the geometry from the map layer
                    pnt = feature.geometry().asPoint()
                    x = pnt.x()
                    y = pnt.y()
                    
                    ret = self.projection.xyToPoint(x, y)
                    geom = ret[0]
                    
                if geom != None:
                    fet = QgsFeature()
                    fet.setGeometry(geom)
                    fet.setAttributes(feature.attributes())
                    fets.append(fet)    
        return fets
        
    def addFieldsToAtlas(self, mapType, symbolType):
    
        # This procedure makes an atlas map
        self.pr.addAttributes([QgsField("GridRef", QVariant.String)])
        self.pr.addAttributes([QgsField("Records", QVariant.Int)])
        if self.env.getEnvValue("biorec.outtrim") != "true":
            self.pr.addAttributes([QgsField("Abundance", QVariant.Int)])
        self.pr.addAttributes([QgsField("Richness", QVariant.Int)])
        if self.env.getEnvValue("biorec.outtrim") != "true":
            self.pr.addAttributes([QgsField("Taxa", QVariant.String)])
            
        self.vl.startEditing()
        
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
            
        fetsDict = {}

        if len(self.taxa) == 1:
        
            taxonFieldName = self.csvLayer.dataProvider().fields()[self.iColTaxa].name()
            strFilter = ""
            for taxon in self.taxa:  #self.taxa is a set, so can't user self.taxa[0]
                #strFilter = '"%s" = \'%s\'' % (taxonFieldName, taxon)
                #The regular expression (~ comparison) allows for leading and trailing white space on the taxa
                strFilter = '"%s" ~ \' *%s *\'' % (taxonFieldName, taxon.replace("'", r"\'"))
                #QgsMessageLog.logMessage(strFilter, 'biorec')

            #request = QgsFeatureRequest().setFilterExpression(QgsExpression(strFilter
            request = QgsFeatureRequest().setFilterExpression(strFilter)
            iter = self.csvLayer.getFeatures(request)
            #fetsDict.update(self.makeAtlasFeatures(iter, gridPrecision, symbol))
            fetsDict = self.makeAtlasFeatures(iter, gridPrecision, symbol)
        else:
            iter = self.csvLayer.getFeatures()
            if len(self.taxa) == 0:
                # No taxa selected, so get all features from CSV
                fetsDict = self.makeAtlasFeatures(iter, gridPrecision, symbol)
            else:
                # More than one taxon selected - so filter based on taxa
                fetsDict = self.makeAtlasFeatures(iter, gridPrecision, symbol, True)

        # Now loop through the dictionary and create a feature for each one
        fets=[]
        for gr in fetsDict:
        
            fetDict = fetsDict[gr]
            fet = QgsFeature()
            fet.setGeometry(fetDict[0])
            if self.env.getEnvValue("biorec.outtrim") != "true":
                attrs = [gr, fetDict[1], fetDict[2], fetDict[3], fetDict[4]]
            else:
                attrs = [gr, fetDict[1], fetDict[3]]
            fet.setAttributes(attrs)
            fets.append(fet)
                
        self.vl.addFeatures(fets)
        self.vl.commitChanges()
        self.vl.updateExtents()
        self.vl.removeSelection()
        self.translationError = ""
        
    def makeAtlasFeatures(self, iter, gridPrecision, symbol, bFilterTaxaV2=False):
   
        fetsDict = {}
        taxaDict = {}

        for feature in iter:
            
            taxon = ""
            
            if bFilterTaxaV2:
                try:
                    taxon = feature.attributes()[self.iColTaxa]
                except:
                    taxon = "invalid"
                    
            if not bFilterTaxaV2:
                bTaxonOkay = True
            elif bFilterTaxaV2 and taxon in self.taxa:
                bTaxonOkay = True
            else:
                bTaxonOkay = False
            
            if bTaxonOkay:
                if self.iColGr > -1:
                    xOriginal = None
                    yOriginal = None
                    # Geocoding from OS grid ref
                    try:
                        grOriginal = str(feature.attributes()[self.iColGr]).replace(" ", "")
                    except:
                        grOriginal = "NULL"
                        
                    if grOriginal == "NULL":
                        grOriginal = None
                elif self.iColX > -1:
                    grOriginal = None
                    # Geocoding from x and y
                    try:
                        strX = str(feature.attributes()[self.iColX])
                    except:
                        strX = "NULL"
                    try:
                        strY = str(feature.attributes()[self.iColY])
                    except:
                        strY = "NULL"
                        
                    if strX == "NULL" or strY == "NULL":
                        xOriginal = None
                        yOriginal = None
                    else:
                        try:
                            xOriginal = float(strX)
                            yOriginal = float(strY)
                        except:
                            xOriginal = None
                            yOriginal = None
                else:
                    #Get the geometry from the map layer
                    pnt = feature.geometry().asPoint()
                    xOriginal = pnt.x()
                    yOriginal = pnt.y()
                       
                if not (self.iColGr > -1 and grOriginal == None) and not (self.iColGr == -1 and xOriginal == None):

                    # Get a value for abundance
                    if self.iColAb == -1:
                        abundance = 1
                    else:
                        try:
                            try:
                                abundance = int(str(feature.attributes()[self.iColAb]))
                            except:
                                abundance = 0
                            if abundance < 1:
                                abundance = 1
                        except:
                            abundance = 1
                    
                    if self.iColGr > -1:
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
                            fetsDict[gr] = [geom, 1, abundance, 1, ""]
                            taxaDict[gr] = [taxon]
                        else:
                            #Records
                            fetsDict[gr][1]+=1
                            #Abundance
                            fetsDict[gr][2]+=abundance
                            #Richness & Taxa
                            if not taxon in taxaDict[gr]:
                                fetsDict[gr][3]+=1 
                                taxaDict[gr].append(taxon)
                                #fetsDict[gr][4]+="#"+taxon
                            
        #Sort taxaDict to ensure that the taxa attribute includes taxa in 
        #same order for all grid references.
        for gr in fetsDict.keys():
            taxaDict[gr].sort()
            for taxon in taxaDict[gr]:
                fetsDict[gr][4]+="#"+taxon
            #Trim off first hash
            fetsDict[gr][4]=fetsDict[gr][4][1:]
            
        return fetsDict
        
    def includeTaxon(self, taxon):
        # Check if taxa is in list
       
        if len(self.taxa) == 0:
            return(True)

        if taxon in self.taxa:
            return(True)
        else:
            return(False)
        