# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NBNDialog
                                 A QGIS plugin
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

from . import ui_nbn 
import os.path
import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import urllib
import json 
import hashlib, uuid
import shutil
import csv
import zipfile
from io import BytesIO
import re
import datetime
import random
from . import osgr
from . import envmanager
from . import filedialog


class NBNDialog(QWidget, ui_nbn.Ui_nbn):

    displayNBNCSVFile = pyqtSignal(basestring)

    def __init__(self, iface, dockwidget):
        QWidget.__init__(self)
        ui_nbn.Ui_nbn.__init__(self)
        self.setupUi(self)
        self.canvas = iface.mapCanvas()
        self.iface = iface
    
        self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        
        self.treeNodesExact = {} 
        self.treeNodesFuzzy = {} 

        # Get a reference to an osgr object and an osgrLayer object
        self.osgr = osgr.osgr()
        
        # Load the environment stuff
        self.env = envmanager.envManager()
        
        self.pbSpeciesWMS.clicked.connect(self.WMSFetchSpecies)
        self.butTaxonSearch.clicked.connect(self.taxonSearch)
        self.leTaxonSearch.returnPressed.connect(self.taxonSearch)
        self.butClearLast.clicked.connect(self.removeMap)
        self.butClear.clicked.connect(self.removeMaps)
        self.butHelp.clicked.connect(self.helpFile)
        self.butGithub.clicked.connect(self.github)
        #self.pbRefreshDatasets.clicked.connect(self.refreshDatasets)
        self.pbRefreshDatasets.clicked.connect(self.refreshProviders)
        self.pbRefreshSpeciesLists.clicked.connect(self.refreshSpeciesLists)
        self.pbUncheckAll.clicked.connect(self.uncheckAll)
        self.pbUncheckAllSpeciesList.clicked.connect(self.uncheckAllSpeciesList)
        self.twProviders.itemClicked.connect(self.providersClick)
        self.twSpeciesLists.itemClicked.connect(self.speciesListClick)
        self.twTaxa.itemClicked.connect(self.taxaTwClick)
        self.cbStartYear.stateChanged.connect(self.checkFilters)
        self.cbEndYear.stateChanged.connect(self.checkFilters)
        self.pbBuffer.clicked.connect(self.generateBuffer)
        self.pbClearLastBuffer.clicked.connect(self.removeBuffer)
        self.rbGR.toggled.connect(self.bufferEnableDisable)
        self.rbEN.toggled.connect(self.bufferEnableDisable)
        self.pbDownload.clicked.connect(self.downloadNBNObservations)
        self.pbClearFilters.clicked.connect(self.clearAllFilters)
        self.pbClearTaxonFilters.clicked.connect(self.clearTaxonFilters)
        self.pbBrowseNbnOutputFolder.clicked.connect(self.browseNbnOutputFolder)
        self.twDownloaded.itemDoubleClicked.connect(self.downloadClicked)
        self.twTaxa.itemDoubleClicked.connect(self.selectTaxa)
        self.lwTaxa.itemDoubleClicked.connect(self.removeTaxa)
        self.cbShowAllMetadata.stateChanged.connect(self.showHideMetadataColumns)
        
        # Map canvas events
        self.canvas.extentsChanged.connect(self.mapExtentsChanged)
        self.canvas.selectionChanged.connect(self.checkMapSelectionFilter)
        self.iface.currentLayerChanged.connect(self.checkMapSelectionFilter)
        
        # Make a coordinate translator. Also need global references to OSGB and canvas CRSs since
        # they cannot be retrieved from a translator object.
        self.canvasCrs = self.canvas.mapSettings().destinationCrs()
        self.osgbCrs = QgsCoordinateReferenceSystem("EPSG:27700")
        self.transformCrs = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), QgsCoordinateReferenceSystem("EPSG:27700"), QgsProject.instance())
        
        # Inits
        self.layers = []
        self.buffers = []
        self.tvks = {} #Initialise tvk dictionary
        self.butClearLast.setIcon(QIcon( self.pathPlugin % "images/removelayer.png" ))
        self.butClear.setIcon(QIcon( self.pathPlugin % "images/removelayers.png" ))
        self.pbSpeciesWMS.setIcon(QIcon( self.pathPlugin % "images/nbngridmap.png" ))
        self.pbDownload.setIcon(QIcon( self.pathPlugin % "images/nbndownload.png" ))
        self.butTaxonSearch.setIcon(QIcon( self.pathPlugin % "images/speciesinventory.png" ))
        self.pbBuffer.setIcon(QIcon( self.pathPlugin % "images/buffer.png" ))
        self.pbClearLastBuffer.setIcon(QIcon( self.pathPlugin % "images/bufferclear.png" ))
        self.sbPointSize.setValue(6)
        self.mcbWMSColour.setColor(QColor('#cd3844'))

        self.butHelp.setIcon(QIcon( self.pathPlugin % "images/info.png" ))
        self.butGithub.setIcon(QIcon( self.pathPlugin % "images/github.png" ))
        self.twTaxa.setHeaderLabel("Matching taxa")
        self.guiFile = None
        self.infoFile = os.path.join(os.path.dirname( __file__ ), "infoNBNTool.txt")
        self.readProviderFile()
        self.readSpeciesListFile()
        self.datasetSelectionChanged()
        self.speciesListSelectionChanged()
        self.checkFilters()
        self.bufferEnableDisable()
        self.lblMetadata.setText("")
        self.defaultColumns = []
        self.cbShowAllMetadata.setEnabled(False)
       

        self.WMSType = self.enum(species=1, dataset=2, designation=3)

        # Populate the download reason combobox
        self.cboDownloadReason.addItem("Reason for download", -99)
        url = 'https://logger.nbnatlas.org/service/logger/reasons'
        res = self.restRequest(url)
        self.reasonTips = {}
        if not res is None:
            jsonData = json.loads(res.data()) 
            for reason in jsonData:
                if not reason["deprecated"]:
                    splitName = reason["name"].split("|")
                    self.cboDownloadReason.addItem(splitName[0], reason["id"])

                    tip = ""
                    if len(splitName) > 1:
                        tip = splitName[1]
                    self.reasonTips[reason["id"]] = tip

        self.cboDownloadReason.currentIndexChanged.connect(self.downloadReasonChanged)

    def downloadReasonChanged(self):
        if self.cboDownloadReason.currentData() != -99:
            self.cboDownloadReason.setToolTip(self.reasonTips[self.cboDownloadReason.currentData()])
        else:
            self.cboDownloadReason.setToolTip("Specify a reason for NBN download")

    def browseNbnOutputFolder(self):
    
        #Reload env
        self.env.loadEnvironment()
        
        dlg = QFileDialog
        
        if os.path.exists(self.leNbnOutputFolder.text()):
            strInitPath = self.leNbnOutputFolder.text()
        else:
            strInitPath = ""
            
        folderName = dlg.getExistingDirectory(self, "Browse for NBN download folder", strInitPath)
        if folderName:
            self.leNbnOutputFolder.setText(folderName)
            self.leNbnOutputFolder.setToolTip(folderName)

    def showEvent(self, ev):
        # Load the environment stuff
        self.env = envmanager.envManager()

        # Set the download folder if set in env file
        self.leNbnOutputFolder.setText(self.env.getEnvValue("nbn.downloadfolder"))

        return QWidget.showEvent(self, ev)
        
    def enum(self, **enums):
        return type('Enum', (), enums)

    def logMessage(self, strMessage, level=Qgis.Info):
        QgsMessageLog.logMessage(strMessage, "NBN Tool", level)
    
    def infoMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Info", strMessage, level=Qgis.Info)
        
    def warningMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Warning", strMessage, level=Qgis.Warning)
        
    def errorMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Error", strMessage, level=Qgis.Critical)
        
    def uncheckAll(self):
              
        for iProvider in range(self.twProviders.topLevelItemCount()):
            twiProvider = self.twProviders.topLevelItem(iProvider)
            twiProvider.setCheckState(0, Qt.Unchecked)
            for iDataset in range(twiProvider.childCount()):
                twiDataset = twiProvider.child(iDataset)
                twiDataset.setCheckState(0, Qt.Unchecked)
            
        self.datasetSelectionChanged()

    def uncheckAllSpeciesList(self):

        for iListType in range(self.twSpeciesLists.topLevelItemCount()):
            twiListType = self.twSpeciesLists.topLevelItem(iListType)
            for iSpeciesList in range(twiListType.childCount()):
                twiSpeciesList = twiListType.child(iSpeciesList)
                twiSpeciesList.setCheckState(0, Qt.Unchecked)
            
        self.speciesListSelectionChanged()

    def bufferEnableDisable(self):
        gr = self.rbGR.isChecked()
        en = self.rbEN.isChecked()
        self.lePointBufferGR.setEnabled(gr)
        self.sbEasting.setEnabled(en)
        self.sbNorthing.setEnabled(en)
        self.rbBritishEN.setEnabled(en)
        self.rbIrishEN.setEnabled(en)

    def generateBuffer(self):
    
        gridType = ""

        if self.rbGR.isChecked():
            #Get grid mid point of GR
            gridRef = self.lePointBufferGR.text().strip()
            ret = self.osgr.enFromGR(gridRef)
            if ret[0] == 0:
                self.warningMessage(ret[3])
                return
                
            sName = gridRef
            
            easting = ret[0]
            northing = ret[1]
            gridType = ret[4]
        else:
            easting = self.sbEasting.value()
            northing = self.sbNorthing.value()
            
            if self.rbBritishEN.isChecked():
                gridType = "os"
            else:
                gridType= "irish"
            
            sName = str(easting) + "/" + str(northing) + " (" + gridType + ")"

        sName = sName + " " + str(self.sbBuffer.value()) + "m"
        
        geom = self.osgr.circleGeom(easting, northing, self.sbBuffer.value())
        
        # Create layer 
        if gridType == "os":
            epsg = "27700"
        else:
            epsg = "29903"

        self.vl = QgsVectorLayer("Polygon?crs=epsg:" + epsg, sName, "memory")
        self.pr = self.vl.dataProvider()
        self.buffers.append(self.vl.id())

        # Symbology
        props = { 'color' : '255,0,0,100', 'color_border' : '0,0,0,200', 'style' : 'solid', 'style_border' : 'solid' }
        s = QgsFillSymbol.createSimple(props)
        self.vl.setRenderer( QgsSingleSymbolRenderer( s ) )

        # Add geometry to layer
        fet = QgsFeature()
        fet.setGeometry(geom)

        # Needs an attribute otherwise it cannot be selected and geometry functions fail
        #self.pr.addAttributes([QgsField("id", QVariant.Int)])
        #attrs=[random.randrange(1, 100000)]
        ##attrs=[1]
        #fet.setAttributes(attrs)

        self.vl.startEditing()
        self.vl.addFeatures([fet])

        self.vl.commitChanges()
        self.vl.updateExtents()

         # Add to map layer registry
        QgsProject.instance().addMapLayer(self.vl)    

        # Zoom to buffer extent
        self.iface.actionZoomToLayer().trigger()
        
        self.checkMapSelectionFilter()
        
    def taxaTwClick(self, twItem, iCol):
        
        #If current item is checked, uncheck all others
        #Only one taxon can be checked.
        
        for twiKey in self.treeNodesExact:
            if not self.treeNodesExact[twiKey] == twItem and self.treeNodesExact[twiKey].checkState(0) == Qt.Checked:
                self.treeNodesExact[twiKey].setCheckState(0, Qt.Unchecked)
        for twiKey in self.treeNodesFuzzy:
            if not self.treeNodesFuzzy[twiKey] == twItem and self.treeNodesFuzzy[twiKey].checkState(0) == Qt.Checked:
                self.treeNodesFuzzy[twiKey].setCheckState(0, Qt.Unchecked)

        self.checkFilters()
        
    def datasetSelectionChanged(self):
        
        iChecked = 0
        for iProvider in range(self.twProviders.topLevelItemCount()):
            twiProvider = self.twProviders.topLevelItem(iProvider)
            for iDataset in range(twiProvider.childCount()):
                twiDataset = twiProvider.child(iDataset)
                if twiDataset.checkState(0) == Qt.Checked:
                    iChecked += 1
                    
        if iChecked == 0:
            self.lblDatasetFilter.setText("No datasets selected.")
        else:
            self.lblDatasetFilter.setText(str(iChecked) + " datasets selected.")
            
        self.checkFilters()

    def speciesListSelectionChanged(self):
        
        iChecked = 0
        for iType in range(self.twSpeciesLists.topLevelItemCount()):
            twiType = self.twSpeciesLists.topLevelItem(iType)
            for iList in range(twiType.childCount()):
                twiList = twiType.child(iList)
                if twiList.checkState(0) == Qt.Checked:
                    iChecked += 1
                    
        if iChecked == 0:
            self.lblSpeciesListFilter.setText("No species lists selected.")
        else:
            self.lblSpeciesListFilter.setText(str(iChecked) + " species lists selected.")
            
        self.checkFilters()

    def refreshProviders(self):

        self.twProviders.clear()
        
        url = 'https://registry.nbnatlas.org/ws/dataProvider'
        res = self.restRequest(url)

        if res is None:
            return

        responseText = res.data().decode('utf-8')
        #responseText = res.data()

        # Write the json data to a file
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "providers.json"))
        with open(datafile, 'w') as jsonfile:
            jsonfile.write(responseText)
            
        # Rebuild dataset tree
        self.readProviderFile()
        self.datasetSelectionChanged()

    def refreshSpeciesLists(self):

        self.twSpeciesLists.clear()
        
        url = 'https://lists.nbnatlas.org/ws/speciesList?max=1000'
        res = self.restRequest(url)

        if res is None:
            return

        responseText = res.data().decode('utf-8')

        # Write the json data to a file
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "species-lists.json"))
        with open(datafile, 'w') as jsonfile:
            jsonfile.write(responseText)
            
        # Rebuild dataset tree
        self.readSpeciesListFile()
        self.speciesListSelectionChanged()
         
    def providersClick(self, twi):

        if twi.text(2) == "provider" and  twi.childCount() == 0:
            
            url = 'https://registry.nbnatlas.org/ws/dataProvider/' + twi.text(1)
            res = self.restRequest(url)
            if res is None:
                return

            jsonData = json.loads(res.data()) 

            twi.setExpanded(True)

            for dataResource in jsonData["dataResources"]:
                QgsMessageLog.logMessage("dataset: " + dataResource["name"], "NBN Tool") 

                # Create a tree item for the dataset
                twiDataset = QTreeWidgetItem(twi)
                twiDataset.setText(0, dataResource["name"])
                twiDataset.setText(1, dataResource["uid"])
                twiDataset.setText(2, "dataset")
                twiDataset.setExpanded(False)
                twiDataset.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                twiDataset.setCheckState(0, twi.checkState(0))

        elif twi.text(2) == "provider":

            #If provider is checked, then check all children
            #If provider is unchecked, then uncheck all children

            #if twi.checkState(0) == Qt.Checked:
            for i in range(0, twi.childCount()):
                twi.child(i).setCheckState(0, twi.checkState(0))

        else: #dataset
            
            if twi.checkState(0) == Qt.Unchecked:
                #If a dataset is unchecked, then uncheck provider
                twi.parent().setCheckState(0, Qt.Unchecked)
            else:
                #If all datasets are checked, then check provider
                allChecked = True
                for i in range(0, twi.parent().childCount()):
                    if twi.parent().child(i).checkState(0) ==  Qt.Unchecked:
                        allChecked = False
                        break
                if allChecked:
                    twi.parent().setCheckState(0, Qt.Checked)
                else:
                    twi.parent().setCheckState(0, Qt.Unchecked)

        self.datasetSelectionChanged()

    def speciesListClick(self):

        self.speciesListSelectionChanged()

    def readProviderFile(self):
           
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "providers.json"))
        if not os.path.isfile(datafile):
            self.infoMessage("NBN Atlas data providers file not found.")
            return

        try:
            with open(datafile) as f:
                jsonData = json.load(f)
        except:
            self.warningMessage("NBN Atlas data providers file failed to load. Use the refresh button to generate a new one.")
            return

        for jDataset in jsonData:
        
            #Create a new top level tree item for the dataset provider organisation
            twiProvider = QTreeWidgetItem(self.twProviders)
            twiProvider.setText(0, jDataset["name"])
            twiProvider.setText(1, jDataset["uid"])
            twiProvider.setText(2, "provider")
            twiProvider.setExpanded(False)
            twiProvider.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            twiProvider.setCheckState(0, Qt.Unchecked) # 0 is the column number 

        self.twProviders.sortItems(0, Qt.AscendingOrder)

    def readSpeciesListFile(self):

        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "species-lists.json"))
        if not os.path.isfile(datafile):
            self.infoMessage("NBN Atlas species list file not found.")
            return

        try:
            with open(datafile) as f:
                jsonData = json.load(f)
        except:
            self.warningMessage("NBN Atlas data species list file failed to load. Use the refresh button to generate a new one.")
            return

        #List types are initialised to known list types so that order can be specified
        knownListTypes = ["CONSERVATION_LIST", "SENSITIVE_LIST", "LOCAL_LIST", "COMMON_HABITAT"]
        excludeListTypes = ["TEST"]
        readListTypes = []
        listTypes = []
        for speciesList in jsonData["lists"]:
            if not speciesList["listType"] in readListTypes and not speciesList["listType"] in excludeListTypes:
                readListTypes.append(speciesList["listType"])

        for speciesList in knownListTypes:
            if speciesList in readListTypes:
                listTypes.append(speciesList)

        for speciesList in readListTypes:
            if not speciesList in listTypes:
                listTypes.append(speciesList)

        for listType in listTypes:
            twiListType = QTreeWidgetItem(self.twSpeciesLists)
            twiListType.setText(0, listType.replace("_", " ").capitalize())

        for speciesList in jsonData["lists"]:
            listType=speciesList["listType"].replace("_", " ").capitalize()
            matchItems = self.twSpeciesLists.findItems(listType, Qt.MatchExactly, 0)
            if len(matchItems) == 1:
                twiList = QTreeWidgetItem(matchItems[0])
                twiList.setText(0, speciesList["listName"])
                twiList.setText(1, speciesList["dataResourceUid"])
                twiList.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                twiList.setCheckState(0, Qt.Unchecked) 

    def helpFile(self):

        ##iface.layerTreeView().setSelectionMode( QAbstractItemView.MultiSelection )

        ## Select your layers, this time they are not mutually exclusive
        #i=0

        ##QgsProject.instance().layerTreeRoot().
        #for layer in self.layers:
        #    iface.layerTreeView().setCurrentLayer(layer)
        #    #QgsProject.instance().layerTreeRoot().setCurrentLayer(layer)
        #    break
        ##iface.layerTreeView().setSelectionMode( QAbstractItemView.ExtendedSelection )
        
        #return
        
        QDesktopServices().openUrl(QUrl("http://www.fscbiodiversity.uk/qgisnbnatlastool"))

        #self.guiFile = filedialog.FileDialog(self.iface, self.infoFile)
        #self.guiFile.setVisible(True)

    def github(self):
        QDesktopServices().openUrl(QUrl("https://github.com/FieldStudiesCouncil/QGIS-Biological-Recording-Tools/issues"))
   
    def taxonSearch(self):
        #NBN Atlas search
        if self.leTaxonSearch.text() == "":
            self.iface.messageBar().pushMessage("No search term specified.", level=Qgis.Info)
            return

        url = 'https://species-ws.nbnatlas.org/search?q=' + self.leTaxonSearch.text() + '&pageSize=50&fq=taxonomicStatus:accepted'
        #url = 'https://species-ws.nbnatlas.org/search?q=' + self.leTaxonSearch.text() + '&pageSize=100'
        res = self.restRequest(url)

        #self.logMessage(url)

        if res is None:
            return

        responseText = res.data().decode('utf-8')

        #self.logMessage(responseText)
        jsonData = json.loads(responseText) 
        jResponseList = jsonData["searchResults"]["results"]
        lightGrey = QBrush(QColor(130,130,130,255))

        #Tree view
        self.twTaxa.clear()
        self.treeNodesExact = {}
        self.treeNodesFuzzy = {} 

        #Create top level items for exact and fuzzy matches
        twiExact = QTreeWidgetItem(self.twTaxa)
        twiExact.setText(0, "Exact match")
        twiExact.setExpanded(False)
        twiExact.setFlags(Qt.ItemIsEnabled) #By resetting the flags, we take off default isSelectable

        twiFuzzy = QTreeWidgetItem(self.twTaxa)
        twiFuzzy.setText(0, "Fuzzy match")
        twiFuzzy.setExpanded(False)
        twiFuzzy.setFlags(Qt.ItemIsEnabled) #By resetting the flags, we take off default isSelectable

        for jTaxon in jResponseList:
        
            #QgsMessageLog.logMessage(jTaxon["name"], "NBN Tool")

            #Is this a fuzzy match or an exact match?
            if jTaxon["name"].lower() == self.leTaxonSearch.text().lower() or jTaxon["commonNameSingle"].lower() == self.leTaxonSearch.text().lower():
                treeNodes = self.treeNodesExact
                twiParent = twiExact
            else:
                treeNodes = self.treeNodesFuzzy
                twiParent = twiFuzzy

            try:
                tKingdom = jTaxon["kingdom"]
                if tKingdom is None:
                    tKingdom = ""
            except:
                tKingdom = ""

            try:
                tPhylum = jTaxon["phylum"]
                if tPhylum is None:
                    tPhylum = ""
            except:
                tPhylum = ""

            try:
                tClass = jTaxon["class"]
                if tClass is None:
                    tClass = ""
            except:
                tClass = ""

            try:
                tOrder = jTaxon["order"]
                if tOrder is None:
                    tOrder = ""
            except:
                tOrder = ""

            try:
                tFamily = jTaxon["family"]
                if tFamily is None:
                    tFamily = ""
            except:
                tFamily = ""

            try:
                tGenus = jTaxon["genus"]
                if tFamily is None:
                    tGenus = ""
            except:
                tGenus = ""

            if 'commonNameSingle' in jTaxon and jTaxon["commonNameSingle"] != "":
                tName = jTaxon["name"] + " (" + jTaxon["commonNameSingle"] + ")"
            else:
                tName = jTaxon["name"]

            if tKingdom != "" and not tKingdom in(treeNodes.keys()):
                #Create a new top level tree item for the taxon group
                twiKingdom = QTreeWidgetItem(twiParent)
                twiKingdom.setText(0, tKingdom + ' (Kingdom)')
                twiKingdom.setExpanded(True)
                twiKingdom.setForeground(0, lightGrey)
                twiKingdom.setFlags(Qt.ItemIsEnabled) #By resetting the flags, we take off default isSelectable
                twiKingdom.setIcon(0, QIcon( self.pathPlugin % "images/taxonomy20x16.png" ))
                try:
                    twiKingdom.setToolTip(0, jTaxon["kingdomGuid"])
                except:
                    pass
                #Add to dictionary
                treeNodes[tKingdom] = twiKingdom
            elif tKingdom != "":
                twiKingdom = treeNodes[tKingdom]
            if tKingdom != "":
                twiParent = twiKingdom

            if tPhylum != "" and not tPhylum in(treeNodes.keys()):
                #Create a new top level tree item for the taxon group
                twiPhylum = QTreeWidgetItem(twiParent)
                twiPhylum.setText(0, tPhylum + ' (Phylum)')
                twiPhylum.setExpanded(True)
                twiPhylum.setForeground(0, lightGrey)
                twiPhylum.setFlags(Qt.ItemIsEnabled) #By resetting the flags, we take off default isSelectable
                twiPhylum.setIcon(0, QIcon( self.pathPlugin % "images/taxonomy20x16.png" ))
                try:
                    twiPhylum.setToolTip(0, jTaxon["phylumGuid"])
                except:
                    pass
                #self.twTaxa.addTopLevelItem(twiPhylum)
                #Add to dictionary
                treeNodes[tPhylum] = twiPhylum
            elif tPhylum != "":
                twiPhylum = treeNodes[tPhylum]
            if tPhylum != "":
                twiParent = twiPhylum

            if tClass != "" and not tClass in(treeNodes.keys()):
                #Create a new top level tree item for the taxon group
                twiClass = QTreeWidgetItem(twiParent)
                twiClass.setText(0, tClass + ' (Class)')
                twiClass.setExpanded(True)
                twiClass.setForeground(0, lightGrey)
                twiClass.setFlags(Qt.ItemIsEnabled) #By resetting the flags, we take off default isSelectable
                twiClass.setIcon(0, QIcon( self.pathPlugin % "images/taxonomy20x16.png" ))
                try:
                    twiClass.setToolTip(0, jTaxon["classGuid"])
                except:
                    pass
                #self.twTaxa.addTopLevelItem(twiClass)
                #Add to dictionary
                treeNodes[tClass] = twiClass
            elif tClass != "":
                twiClass = treeNodes[tClass]
            if tClass != "":
                twiParent = twiClass

            if tOrder != "" and not tOrder in(treeNodes.keys()):
                #Create a new top level tree item for the taxon group
                twiOrder = QTreeWidgetItem(twiParent)
                twiOrder.setText(0, tOrder + ' (Order)')
                twiOrder.setExpanded(True)
                twiOrder.setForeground(0, lightGrey)
                twiOrder.setFlags(Qt.ItemIsEnabled) #By resetting the flags, we take off default isSelectable
                twiOrder.setIcon(0, QIcon( self.pathPlugin % "images/taxonomy20x16.png" ))
                try:
                    twiOrder.setToolTip(0, jTaxon["orderGuid"])
                except:
                    pass
                #self.twTaxa.addTopLevelItem(twiOrder)
                #Add to dictionary
                treeNodes[tOrder] = twiOrder
            elif tOrder != "":
                twiOrder = treeNodes[tOrder]
            if tOrder != "":
                twiParent = twiOrder

            if tFamily != "" and not tFamily in(treeNodes.keys()):
                #Create a new top level tree item for the taxon group
                twiFamily = QTreeWidgetItem(twiParent)
                twiFamily.setText(0, tFamily + ' (Family)')
                twiFamily.setExpanded(True)
                twiFamily.setForeground(0, lightGrey)
                twiFamily.setFlags(Qt.ItemIsEnabled) #By resetting the flags, we take off default isSelectable
                twiFamily.setIcon(0, QIcon( self.pathPlugin % "images/taxonomy20x16.png" ))
                try:
                    twiFamily.setToolTip(0, jTaxon["familyGuid"])
                except:
                    pass
                #self.twTaxa.addTopLevelItem(twiFamily)
                #Add to dictionary
                treeNodes[tFamily] = twiFamily
            elif tFamily != "":
                twiFamily = treeNodes[tFamily]
            if tFamily != "":
                twiParent = twiFamily   

            if tGenus != "" and not tGenus in(treeNodes.keys()):
                #Create a new top level tree item for the taxon group
                twiGenus = QTreeWidgetItem(twiParent)
                twiGenus.setText(0, tGenus + ' (Genus)')
                twiGenus.setExpanded(True)
                twiGenus.setForeground(0, lightGrey)
                twiGenus.setFlags(Qt.ItemIsEnabled) #By resetting the flags, we take off default isSelectable
                twiGenus.setIcon(0, QIcon( self.pathPlugin % "images/taxonomy20x16.png" ))
                try:
                    twiGenus.setToolTip(0, jTaxon["genusGuid"])
                except:
                    pass
                #Add to dictionary
                treeNodes[tGenus] = twiGenus
            elif tGenus != "":
                twiGenus = treeNodes[tGenus]
            if tGenus != "":
                twiParent = twiGenus   

            #Create a child tree item for the preferred TVK group
            twiPTVK = QTreeWidgetItem(twiParent)
            twiPTVK.setData(0, Qt.ToolTipRole, jTaxon["guid"])
            twiPTVK.setText(0, tName)
            twiPTVK.setIcon(0, QIcon( self.pathPlugin % "images/Taxon20x16.png" ))
            #twiPTVK.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            #twiPTVK.setFlags(Qt.ItemIsEnabled)
            #twiPTVK.setCheckState(0, Qt.Unchecked) # 0 is the column number 
            twiPTVK.setExpanded(True)
            #self.twTaxa.addTopLevelItem(twiPTVK)
            #Add to dictionary
            treeNodes[jTaxon["guid"]] = twiPTVK

        if twiExact.childCount() > 0:
            twiExact.setExpanded(True)
        elif twiFuzzy.childCount() > 0:
            twiFuzzy.setExpanded(True)

    def datasetsSelected(self):
        
        for iProvider in range(self.twProviders.topLevelItemCount()):
            twiProvider = self.twProviders.topLevelItem(iProvider)
            if twiProvider.checkState(0) == Qt.Checked:
                return True
            for iDataset in range(twiProvider.childCount()):
                twiDataset = twiProvider.child(iDataset)
                if twiDataset.checkState(0) == Qt.Checked:
                    return True
        return False

    def selectedSpeciesLists(self):
        speciesLists = []
        for iListType in range(self.twSpeciesLists.topLevelItemCount()):
            twiListType = self.twSpeciesLists.topLevelItem(iListType)
            for iSpeciesList in range(twiListType.childCount()):
                twiSpeciesList = twiListType.child(iSpeciesList)
                if twiSpeciesList.checkState(0) == Qt.Checked:
                    speciesLists.append(twiSpeciesList.text(1))
        
        if len(speciesLists) > 0:
            return speciesLists
        else:
            return None
                       
    def getSelectedTVK(self):

        if self.lwTaxa.count() == 0:
            self.logMessage("No taxa selected")
            return None
        else:
            i = 0
            tvks = []
            while i < self.lwTaxa.count():
                lwi = self.lwTaxa.item(i)
                tvks.append(lwi.toolTip())
                i += 1

            self.logMessage("Taxa selected: " + str(len(tvks)))
            return tvks

    def makeFilterQuery(self):

        #Filters
        fq = ''

        #Taxon
        tvks = self.getSelectedTVK()
        if not tvks is None:
            if fq == '':
                fq = "&fq="
            else:
                fq = fq + '+AND+'

            if len(tvks) == 1:
                fq = fq + 'lsid:' + tvks[0]
            else:
                fq = fq + '(lsid:' + tvks[0]
                i = 1
                while i < len(tvks):
                    fq = fq + '+OR+lsid:' + tvks[i]
                    i += 1
                fq = fq + ')'

        #Year filter
        startYear = None
        endYear = None
        if self.cbStartYear.checkState() == Qt.Checked:
            startYear = self.sbStartYear.value()
        if self.cbEndYear.checkState() == Qt.Checked:
            endYear = self.sbEndYear.value()
        # Year validity check
        if not startYear is None and not endYear is None:
            if startYear > endYear:
                self.infoMessage("End year, if specified, must come after start year (or be equal to it), if specified.")
                return None
        #Set filter string for year range
        if not startYear is None or not endYear is None:
            if startYear is None:
                startYear = 1600
            if endYear is None:
                endYear = datetime.datetime.now().year
            if fq == '':
                fq = "&fq="
            else:
                fq = fq + '+AND+'
            fq = fq + 'year:[' + str(startYear) + '+TO+' + str(endYear) + ']'


        #Species lists
        if not self.selectedSpeciesLists() is None:
            if fq == '':
                fq = "&fq="
            else:
                fq = fq + '+AND+'
            guids = self.selectedSpeciesLists()
            if len(guids) == 1:
                fq = fq + 'species_list_uid:' + guids[0]
            else:
                fq = fq + '(species_list_uid:' + guids[0]
                i = 1
                while i < len(guids):
                    fq = fq + '+OR+species_list_uid:' + guids[i]
                    i += 1
                fq = fq + ')'

        #Dataset providers and datasets
        iDatasetCount = 0
        providers = []
        datasets = []
        for iProvider in range(self.twProviders.topLevelItemCount()):
            twiProvider = self.twProviders.topLevelItem(iProvider)
            if twiProvider.checkState(0) == Qt.Checked:
                providers.append(twiProvider.text(1))
            else:
                for iDataset in range(twiProvider.childCount()):
                    twiDataset = twiProvider.child(iDataset)
                    if twiDataset.checkState(0) == Qt.Checked:
                        datasets.append(twiDataset.text(1))

        fqd=''
        #Providers
        if len(providers) == 1:
            fqd = fqd + 'data_provider_uid:' + providers[0]
        elif len(providers) > 1:
            fqd = fqd + 'data_provider_uid:('
            iProvider = 0
            for uid in providers:
                 if iProvider == 0:
                     fqd = fqd + uid
                 else:
                     fqd = fqd + '+OR+' + uid
                 iProvider+=1
            fqd = fqd + ')'
        #Join provider and dataset portion if necessary
        if len(datasets) > 0 and len(providers) > 0:
            fqd = fqd + '+OR+'
        #Datasets (where not all datasets for a provider wanted)
        if len(datasets) == 1:
            fqd = fqd + 'data_resource_uid:' + datasets[0]
        elif len(datasets) > 1:
            fqd = fqd + 'data_resource_uid:('
            iDataset = 0
            for uid in datasets:
                 if iDataset == 0:
                     fqd = fqd + uid
                 else:
                     fqd = fqd + '+OR+' + uid
                 iDataset+=1
            fqd = fqd + ')'

        if len(datasets) > 0 and len(providers) > 0:
            fqd = '(' + fqd + ')'

        if len(fqd) > 0:
            if fq == '':
                fq = "&fq="
            else:
                fq = fq + '+AND+'
            fq = fq + fqd

        #Return filter query
        self.logMessage("fq: " + fq)
        return fq

    def getLayerName(self):

        layerName = ""

        #Taxon
        tvks = self.getSelectedTVK()
        if not tvks is None:
            if len(tvks) == 1:
                taxon = self.taxonDetails(tvks[0])
                layerName += " " + taxon["taxonConcept"]["nameString"]
            else:
                layerName += " multiple taxa"

        #Year filters
        startYear = None
        endYear = None
        if self.cbStartYear.checkState() == Qt.Checked:
            startYear = self.sbStartYear.value()
        if self.cbEndYear.checkState() == Qt.Checked:
            endYear = self.sbEndYear.value()
        if not startYear is None and not endYear is None:
            if startYear == endYear:
                layerName += " " + str(startYear)
            else:
                layerName += " " + str(startYear) + "-" + str(endYear)
        elif not startYear is None:
            layerName += " " + str(startYear) + "-"
        elif not endYear is None:
            layerName += " -" + str(endYear)

        #Provider filters
        providers = []
        datasets = []
        for iProvider in range(self.twProviders.topLevelItemCount()):
            twiProvider = self.twProviders.topLevelItem(iProvider)
            if twiProvider.checkState(0) == Qt.Checked:
                providers.append(twiProvider.text(1))
            else:
                for iDataset in range(twiProvider.childCount()):
                    twiDataset = twiProvider.child(iDataset)
                    if twiDataset.checkState(0) == Qt.Checked:
                        datasets.append(twiDataset.text(1))

        if len(providers) == 1:
            layerName += " provider-" + providers[0]
        elif len(providers) > 1:
            layerName += " providers-several"

        if len(datasets) == 1:
            layerName += " dataset-" + datasets[0]
        elif len(datasets) > 1:
            layerName += " datasets-several"

        #Species lists
        if not self.selectedSpeciesLists() is None:
            guids = self.selectedSpeciesLists()
            if len(guids) == 1:
                layerName += " list-" + guids[0]
            else:
                layerName += " lists-several"

        #Polygon
        polySearch = self.getSelectedFeatureWKT()
        if not polySearch is None:
            layerName += " geom-from-" + self.iface.activeLayer().name()

        return layerName.strip()

    def WMSFetchSpecies(self):

        tvks = self.getSelectedTVK()
        if tvks is None:
            self.iface.messageBar().pushMessage("Info", "You must first specify a taxon filter for a WMS map layer.", level=Qgis.Info)
            return

        if len(tvks) > 1:
            self.iface.messageBar().pushMessage("Info", "You must only specify one taxon filter for a WMS map layer.", level=Qgis.Info)
            return

        #Check that taxon rank is allowable given current limitations of Atlas WMS
        allowedRanks = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]

        tvk=tvks[0]
        taxon = self.taxonDetails(tvk)
        taxonName = taxon["taxonConcept"]["nameString"]
        taxonRank = taxon["taxonConcept"]["rankString"]

        if not taxonRank in allowedRanks:
            self.infoMessage(("The taxonomic rank - " + taxonRank + " - of " + taxonName + " is not one "
                                "which can be used with the NBN Atlas' current implementation of WMS "
                                "from within QGIS. Allowed ranks include, family, genus and species"))
            return

        #parentGuid = taxon["taxonConcept"]["parentGuid"]

        #Get full taxon details for the parent of selected guid
        #parent = self.taxonDetails(parentGuid)
        #parentName = parent["taxonConcept"]["nameString"]
        #parentRank = parent["taxonConcept"]["rankString"]

        #Build WMS base URL
        #baseURL = 'https://records-dev-ws.nbnatlas.org'
        baseURL = 'https://records-ws.nbnatlas.org'
        baseURL = baseURL + '/ogc/ows?q=*:*'
        #baseURL = baseURL + parentRank + ':' + parentName.replace(" ", "_")

        #Build Atlas WMS ENV parameter for styling
        envParam='&ENV=name:circle;opacity:1.0;'
        envParam += 'size:' + str(self.sbPointSize.value()) + ';'
        envParam += 'color:' + self.mcbWMSColour.color().name()[1:] + ';'
        if self.cbGridSize.currentIndex() == 1:
            envParam += 'colourmode:osgrid;gridres:singlegrid;'
        if self.cbGridLabels.isChecked():
            envParam += 'gridlabels:true;'

        baseURL = baseURL + envParam
        if self.cbOutline.isChecked():
            baseURL = baseURL + '&OUTLINE=TRUE'

        #Add query filter to baseURL if appropriate
        fq = self.makeFilterQuery()
        if fq is None: #Filter errors detected and reported
            return
        baseURL = baseURL + fq

        #Add WKT filter
        polySearch = self.getSelectedFeatureWKT()
        if not polySearch is None:
            baseURL = baseURL + '&wkt=' + polySearch

        uri = QgsDataSourceUri()
        uri.setParam('url', baseURL)
        uri.setParam('IgnoreGetMapUrl', '1')

        #Species with subgenus, e.g. Bombus (Psithyrus) rupestris, are a problem because the layer returned by
        #GetCapabilities for this will be Bombus_rupestris, so we have to chop out anything in brackets.
        taxonNameMod = re.sub(r'\([^)]*\)', '', taxonName)
        taxonNameMod = re.sub( '\s+', ' ', taxonNameMod).strip() #Replaces mutliple whitespace with single whitespace
        uri.setParam('layers', taxonRank + ':' + taxonNameMod.replace(" ", "_"))
        QgsMessageLog.logMessage("layers: " + taxonRank + ':' + taxonNameMod.replace(" ", "_"), "NBN Tool")
        #uri.setParam('layers', 'ALA:occurrences')
        uri.setParam('format', 'image/png')
        if self.cbGridSize.currentIndex() == 1:
            uri.setParam('crs', 'EPSG:27700')
        else:
            uri.setParam('crs', 'EPSG:3857')
        uri.setParam('styles', '')
  
        #rlayer = QgsRasterLayer(str(uri.encodedUri()), self.getLayerName() + " WMS", 'wms')
        #For v3, using str(uri.encodedUri()) no longer works. The leading b and single quotes
        #are not valid. Can't find a better way to generate a string from byte array than this below.
        encodedUri = str(uri.encodedUri())
        rlayer = QgsRasterLayer(encodedUri[2:len(encodedUri)-1], self.getLayerName() + " WMS", 'wms')

        if not rlayer.isValid():
            self.infoMessage(("The NBN Atlas WMS did not return a layer for this query. "
                              "The specified filters probably result in zero records. "
                              "But if you have a polygon filter, it might be a problem"
                              "with that."))
            return

        opacity = (100-self.hsTransparency.value()) * 0.01
        rlayer.renderer().setOpacity(opacity)
        self.layers.append(rlayer.id())
        QgsProject.instance().addMapLayer(rlayer)
        #self.iface.legendInterface().setLayerExpanded(rlayer, False)
        QgsProject.instance().layerTreeRoot().findLayer(rlayer.id()).setExpanded(False)
        
        #None of these worked to refresh layers panel when layer expanded - these were attempts to overcome
        #a weird refreshing problem when the NBN Atlas legend shown (but not very important since legend not useful).
        #self.canvas.refresh()
        #self.iface.legendInterface().refreshLayerSymbology(rlayer) 
        #QCoreApplication.processEvents() 
        #qApp.processEvents()

        return

    def checkTransform(self):
        
        try:
            # Not sure why, but this sometimes crashes after another failure in module
            if self.canvasCrs != self.canvas.mapSettings().destinationCrs():
                self.canvasCrs = self.canvas.mapSettings().destinationCrs()
                self.transformCrs = QgsCoordinateTransform(self.canvasCrs, self.osgbCrs, QgsProject.instance())
        except:
            pass
        
    def mapExtentsChanged(self):
   
        rectExtent = self.canvas.extent()
        self.checkTransform()
        if self.canvasCrs != self.osgbCrs:
            mapWidth = self.transformCrs.transformBoundingBox(rectExtent).width()
        else:
            mapWidth = rectExtent.width()
        
        #self.iface.messageBar().pushMessage("Info", "Map width: " + str(int(mapWidth)), level=Qgis.Info)
        
        for layerID in self.layers:
            rlayer = None
            try:
                rlayer = QgsProject.instance().mapLayer(layerID)
            except:
                pass
                
            if not rlayer is None:
           
                if rlayer.name().endswith("auto") or rlayer.name().endswith("(auto)"):
                
                    #for strSub in rlayer.subLayers():
                    #    self.iface.messageBar().pushMessage("Info", strSub, level=Qgis.Info)
                        
                    if mapWidth < 15000:
                        #self.iface.messageBar().pushMessage("Info", "Grid-100m", level=Qgis.Info)
                        if rlayer.name().endswith("auto"):
                            rlayer.setSubLayerVisibility("Grid-10km", False)
                            rlayer.setSubLayerVisibility("Grid-2km", False)
                            rlayer.setSubLayerVisibility("Grid-1km", False)
                            rlayer.setSubLayerVisibility("Grid-100m", True)
                        elif " 100 m " in rlayer.name():
                            #self.iface.legendInterface().setLayerVisible(rlayer, True)
                            QgsProject.instance().layerTreeRoot().findLayer(rlayer.id()).setItemVisibilityChecked(True)
                        else:
                            #self.iface.legendInterface().setLayerVisible(rlayer, False)
                            QgsProject.instance().layerTreeRoot().findLayer(rlayer.id()).setItemVisibilityChecked(False)
                            
                    elif mapWidth < 100000:
                        #self.iface.messageBar().pushMessage("Info", "Grid-1km", level=Qgis.Info)
                        if rlayer.name().endswith("auto"):
                            rlayer.setSubLayerVisibility("Grid-10km", False)
                            rlayer.setSubLayerVisibility("Grid-2km", False)
                            rlayer.setSubLayerVisibility("Grid-1km", True)
                            rlayer.setSubLayerVisibility("Grid-100m", False)
                        elif " monad " in rlayer.name():
                            #self.iface.legendInterface().setLayerVisible(rlayer, True)
                            QgsProject.instance().layerTreeRoot().findLayer(rlayer.id()).setItemVisibilityChecked(True)
                        else:
                            #self.iface.legendInterface().setLayerVisible(rlayer, False)
                            QgsProject.instance().layerTreeRoot().findLayer(rlayer.id()).setItemVisibilityChecked(False)
                            
                    elif mapWidth < 250000:
                        #self.iface.messageBar().pushMessage("Info", "Grid-2km", level=Qgis.Info)
                        if rlayer.name().endswith("auto"):
                            rlayer.setSubLayerVisibility("Grid-10km", False)
                            rlayer.setSubLayerVisibility("Grid-2km", True)
                            rlayer.setSubLayerVisibility("Grid-1km", False)
                            rlayer.setSubLayerVisibility("Grid-100m", False)
                        elif " tetrad " in rlayer.name():
                            #self.iface.legendInterface().setLayerVisible(rlayer, True)
                            QgsProject.instance().layerTreeRoot().findLayer(rlayer.id()).setItemVisibilityChecked(True)
                        else:
                            #self.iface.legendInterface().setLayerVisible(rlayer, False)
                            QgsProject.instance().layerTreeRoot().findLayer(rlayer.id()).setItemVisibilityChecked(False)
                            
                    else:
                        #self.iface.messageBar().pushMessage("Info", "Grid-10km", level=Qgis.Info)
                        if rlayer.name().endswith("auto"):
                            rlayer.setSubLayerVisibility("Grid-10km", True)
                            rlayer.setSubLayerVisibility("Grid-2km", False)
                            rlayer.setSubLayerVisibility("Grid-1km", False)
                            rlayer.setSubLayerVisibility("Grid-100m", False)
                        elif " hectad " in rlayer.name():
                            #self.iface.legendInterface().setLayerVisible(rlayer, True)
                            QgsProject.instance().layerTreeRoot().findLayer(rlayer.id()).setItemVisibilityChecked(True)
                        else:
                            #self.iface.legendInterface().setLayerVisible(rlayer, False)
                            QgsProject.instance().layerTreeRoot().findLayer(rlayer.id()).setItemVisibilityChecked(False)
            
    def nameFromTVK(self, tvk):
       
        #Get the preferred taxon name for the TVK
        url = 'https://data.nbn.org.uk/api/taxa/' + tvk
        res = self.restRequest(url)

        if res is None:
            return

        responseText = res.data().decode('utf-8')
        jsonData = json.loads(responseText) 
        return (jsonData["name"])

    def taxonDetails(self, guid):
         #Get full taxon details for the selected guid
        url = 'https://species-ws.nbnatlas.org/species/' + guid
        res = self.restRequest(url)
        if res is None:
            self.iface.messageBar().pushMessage("Info", "No species found for TVK!.", level=Qgis.Info) #Should never happen
            return

        responseText = res.data().decode('utf-8')
        jsonData = json.loads(responseText) 
        return jsonData
        
    def removeMap(self):
        if len(self.layers) > 0:
            layerID = self.layers[-1]
            try:
                QgsProject.instance().removeMapLayer(layerID)
            except:
                pass
            self.layers = self.layers[:-1]
            self.canvas.refresh()
            
    def removeBuffer(self):
        if len(self.buffers) > 0:
            layerID = self.buffers[-1]
            try:
                QgsProject.instance().removeMapLayer(layerID)
            except:
                pass
            self.buffers = self.buffers[:-1]
            self.canvas.refresh()
            
    def removeMaps(self):
        for layerID in self.layers:
            try:
                QgsProject.instance().removeMapLayer(layerID)
            except:
                pass
        self.layers = [] 
        self.canvas.refresh()

    def downloadNBNObservations(self):

        #Collapse all download widget items
        self.twDownloaded.collapseAll()

        #A download reason must be specified
        if self.cboDownloadReason.currentData() == -99:
            self.iface.messageBar().pushMessage("Info", "You must specify a download reason from the drop-down list.", level=Qgis.Info)
            return

        #A writable output folder must be specified
        if self.leNbnOutputFolder.text().strip() == "":
            self.iface.messageBar().pushMessage("Info", "You must specify an output folder for the downloaded data.", level=Qgis.Info)
            return

        if not os.path.exists(self.leNbnOutputFolder.text()):
            self.iface.messageBar().pushMessage("Info", "The specified output folder cannot be found.", level=Qgis.Info)
            return

        #if not os.access(self.leNbnOutputFolder.text(), os.W_OK):
        #    self.iface.messageBar().pushMessage("Info", "The specified output folder is not writeable.", level=Qgis.Info)
        #    return
        #Try to create a temporary file
        try:
            touchFile = self.leNbnOutputFolder.text() + os.path.sep + "qgis-write-test"
            open(touchFile, 'w+').close()
            os.remove(touchFile)
        except:
            self.iface.messageBar().pushMessage("Info", "The specified output folder is not writeable.", level=Qgis.Info)
            return

        #A taxon or dataset filter must be specified
        if self.getSelectedTVK() is None and self.selectedSpeciesLists() is None and not self.datasetsSelected() and self.getSelectedFeatureWKT() is None:
            self.iface.messageBar().pushMessage("Info", "First specify one or more of taxon, dataset, species list or polygon filters.", level=Qgis.Info)
            return

        # Update filter display
        self.checkFilters()

        # Set current tab to next to last (download) tab
        self.tabWidget.setCurrentWidget(self.tabDownloads)

        # Add file to listbox
        fileName = os.path.join(self.leNbnOutputFolder.text(), self.getLayerName() + ".csv")
        splitName = os.path.split(fileName)
        twi = QTreeWidgetItem(self.twDownloaded, [splitName[1]], 0)
        twi.setToolTip(0, fileName)
        twi.setIcon(0, QIcon( self.pathPlugin % "images/download.png" ))
        
        #Add query filter to baseURL if appropriate
        fq = self.makeFilterQuery()
        if fq is None: #Filter errors detected and reported
            return

        endpoint = 'https://records-ws.nbnatlas.org/occurrences/index/download?reasonTypeId=' + str(self.cboDownloadReason.currentData()) + '&qa=none&q=*:*' + fq

        #Add WKT filter
        polySearch = self.getSelectedFeatureWKT()
        if not polySearch is None:
            endpoint = endpoint + '&wkt=' + polySearch

        self.restRequest(endpoint, None, callType="download", downloadInfo={"twi": twi, "csv": fileName, "reply": None})

    def clearTaxonFilters(self):
        self.lwTaxa.clear()

    def clearAllFilters(self):

        #Date filters
        self.cbStartYear.setChecked(False)
        self.cbEndYear.setChecked(False)

        #Taxon filter
        #for twiKey in self.treeNodesExact:
        #    self.treeNodesExact[twiKey].setCheckState(0, Qt.Unchecked)
        #for twiKey in self.treeNodesFuzzy:
        #    self.treeNodesFuzzy[twiKey].setCheckState(0, Qt.Unchecked)
        
        self.leTaxonSearch.setText("")
        self.lwTaxa.clear()
        self.treeNodesExact = {} 
        self.treeNodesFuzzy = {} 

        #Dataset filter
        self.uncheckAll()

        #Specieslist filter
        self.uncheckAllSpeciesList()

        #Polygon
        if self.getSelectedFeatureWKT() is not None:
            self.iface.activeLayer().removeSelection()
            
        #Reset indicator checkboxes
        self.checkFilters()

    def checkFilters(self):

        # Start year
        self.cbIndStartYear.setChecked(self.cbStartYear.isChecked())
        # End year
        self.cbIndEndYear.setChecked(self.cbEndYear.isChecked())
        # Taxon
        self.cbIndTaxon.setChecked(self.getSelectedTVK() is not None)
        # Dataset
        self.cbIndDataset.setChecked(self.datasetsSelected())   
        # Species List
        self.cbIndSpeciesList.setChecked(self.selectedSpeciesLists() is not None)
        # polygon
        self.cbIndPolygon.setChecked(self.getSelectedFeatureWKT() is not None)     
 
    def displayCSV(self):
    
        #Check that single file is selected in list
        #!! - need to check type of item selected - must be CSV
        if len(self.twDownloaded.selectedItems()) != 1:
            self.infoMessage("First select a single CSV file from the list")
            return

        twiSelected = self.twDownloaded.selectedItems()[0]
        csvFile = twiSelected.toolTip(0)
        
        #Emit signal that will cause biorec tool to display file
        self.displayNBNCSVFile.emit(csvFile)
                        
    def getSelectedFeatureWKT(self):
        
        ret = None
        filterGeom = None
        layer = self.iface.activeLayer()
        try:
            if layer is not None:
                if layer.type() == QgsMapLayer.VectorLayer:
                    selectedFeatures = layer.selectedFeatures()
                    if len(selectedFeatures) == 1:
                        feature = selectedFeatures[0]
                        if feature.geometry().type() == QgsWkbTypes.PolygonGeometry: #QGis.WKBPolygon:
                            filterGeom = feature.geometry()
        except:
            filterGeom = None
        
        if filterGeom is not None:
            # If the CRS of the layer is not WGS84, then
            # convert geometry, otherwise use as is.
            if layer.crs() != QgsCoordinateReferenceSystem("EPSG:4326"):
                tcrs = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
                filterGeom.transform(tcrs)

            ret = filterGeom.asWkt()
            
        return ret  
        
    def checkMapSelectionFilter(self):
        # Whenever the map selection changes, update the  
        # polygon filter indicator accordingly.
        if self.getSelectedFeatureWKT() is None:
            self.cbIndPolygon.setChecked(False)
        else:
            self.cbIndPolygon.setChecked(True)
        
    def getNetworkErrorMessage(self, error):
        #NOT USED
        if error == QNetworkReply.NoError:
            # No error condition.
            # Note: When the HTTP protocol returns a redirect no error will be reported.
            # You can check if there is a redirect with the
            # QNetworkRequest::RedirectionTargetAttribute attribute.
            return ''

        if error == QNetworkReply.ConnectionRefusedError:
            return 'The remote server refused the connection (the server is not accepting requests)'

        if error == QNetworkReply.RemoteHostClosedError :
            return 'The remote server closed the connection prematurely, before the entire reply was received and processed'

        if error == QNetworkReply.HostNotFoundError :
            return 'The remote host name was not found (invalid hostname)'

        if error == QNetworkReply.TimeoutError :
            return 'The connection to the remote server timed out'

        if error == QNetworkReply.OperationCanceledError :
            return 'The operation was cancelled via calls to abort() or close() before it was finished.'

        if error == QNetworkReply.SslHandshakeFailedError :
            return 'The SSL/TLS handshake failed and the encrypted channel could not be established. The sslErrors() signal should have been emitted.'

        if error == QNetworkReply.TemporaryNetworkFailureError :
            return 'The connection was broken due to disconnection from the network, however the system has initiated roaming to another access point.  The request should be resubmitted and will be processed as soon as the connection is re-established.'

        if error == QNetworkReply.ProxyConnectionRefusedError :
            return 'The connection to the proxy server was refused (the proxy server is not accepting requests)'

        if error == QNetworkReply.ProxyConnectionClosedError :
            return 'The proxy server closed the connection prematurely, before the entire reply was received and processed'

        if error == QNetworkReply.ProxyNotFoundError :
            return 'The proxy host name was not found (invalid proxy hostname)'

        if error == QNetworkReply.ProxyTimeoutError :
            return 'The connection to the proxy timed out or the proxy did not reply in time to the request sent'

        if error == QNetworkReply.ProxyAuthenticationRequiredError :
            return 'The proxy requires authentication in order to honour the request but did not accept any credentials offered (if any)'

        if error == QNetworkReply.ContentAccessDenied :
            return 'The access to the remote content was denied (similar to HTTP error 401)'

        if error == QNetworkReply.ContentOperationNotPermittedError :
            return 'The operation requested on the remote content is not permitted'

        if error == QNetworkReply.ContentNotFoundError :
            return 'The remote content was not found at the server (similar to HTTP error 404)'
        if error == QNetworkReply.AuthenticationRequiredError :
            return 'The remote server requires authentication to serve the content but the credentials provided were not accepted (if any)'

        if error == QNetworkReply.ContentReSendError :
            return 'The request needed to be sent again, but this failed for example because the upload data could not be read a second time.'

        if error == QNetworkReply.ProtocolUnknownError :
            return 'The Network Access API cannot honor the request because the protocol is not known'

        if error == QNetworkReply.ProtocolInvalidOperationError :
            return 'the requested operation is invalid for this protocol'

        if error == QNetworkReply.UnknownNetworkError :
            return 'An unknown network-related error was detected'

        if error == QNetworkReply.UnknownProxyError :
            return 'An unknown proxy-related error was detected'

        if error == QNetworkReply.UnknownContentError :
            return 'An unknown error related to the remote content was detected'

        if error == QNetworkReply.ProtocolFailure :
            return 'A breakdown in protocol was detected (parsing error, invalid or unexpected responses, etc.)'

        return 'An unknown network-related error was detected'

    def downLoadFinished(self, downloadInfo):

        QgsMessageLog.logMessage("Download finished fired", "NBN Tool")

        twiDownload = downloadInfo["twi"]
        fileName = downloadInfo["csv"]
        reply = downloadInfo["reply"]
        
        error = reply.error()
        if error != QNetworkReply.NoError:
            QgsMessageLog.logMessage("error generated", "NBN Tool")
            self.iface.messageBar().pushMessage("Error", "NBN web service error. Error: %d %s" % (error, reply.errorString()), level=Qgis.Warning)
            twiDownload.setIcon(0, QIcon( self.pathPlugin % "images/cross.png" ))
            return None
        else:
            twiDownload.setIcon(0, QIcon( self.pathPlugin % "images/eggtimer.jpg" ))
        try:
            result = reply.readAll()
            nbnZip = zipfile.ZipFile(BytesIO(result))

            fileNoExt = fileName[:-4]
            with open(fileNoExt + '.csv', 'wb') as csv:
                csv.write (nbnZip.read("data.csv"))
            with open(fileNoExt + '-citation.csv', 'wb') as csv:
                csv.write (nbnZip.read("citation.csv"))
            with open(fileNoExt + '-headings.csv', 'wb') as csv:
                csv.write (nbnZip.read("headings.csv"))

            twiDownload.setIcon(0, QIcon( self.pathPlugin % "images/tick.jpg" ))
            twiDownload.addChild(QTreeWidgetItem(['Data providers'], 0))
            twiDownload.child(0).setIcon(0, QIcon( self.pathPlugin % "images/citations.png" ))
            twiDownload.child(0).setToolTip(0, fileNoExt + '-citation.csv')
            twiHeadings = twiDownload.addChild(QTreeWidgetItem(['Column metadata'], 0))
            twiDownload.child(1).setIcon(0, QIcon( self.pathPlugin % "images/headings.png" ))
            twiDownload.child(1).setToolTip(0, fileNoExt + '-headings.csv')

            twiDownload.setExpanded(True)
        except:
            e = sys.exc_info()[0]
            QgsMessageLog.logMessage("Failed to write output file", "NBN Tool")
            self.iface.messageBar().pushMessage("Error", "Failed to write output file. Error: %s" % (str(e)), level=Qgis.Warning)
            twiDownload.setIcon(0, QIcon( self.pathPlugin % "images/cross.png" ))
        finally:
            reply.deleteLater()

    def selectTaxa(self, twi, iCol):

        if len(twi.toolTip(0)) > 0:
            lwiSelected = QListWidgetItem(self.lwTaxa)
            lwiSelected.setText(twi.text(0))
            lwiSelected.setIcon(QIcon( self.pathPlugin % "images/Taxon20x16.png" ))
            lwiSelected.setToolTip(twi.toolTip(0))

        self.checkFilters()
       
    def removeTaxa(self, lwi):
        iRow = self.lwTaxa.row(lwi)
        self.lwTaxa.takeItem(iRow)

        self.checkFilters()

    def downloadClicked(self, twi, iCol):

        #Get the path of the CSV from the tooltip
        filePath = twi.toolTip(0);

        #If this is the data CSV file then invoke self.displayCSV
        if filePath[-13:] != '-citation.csv' and filePath[-13:] != '-headings.csv':
            self.displayCSV()
            return

        #Otherwise, populate the metadata tab
        metadataInfo = "The file '" + filePath + "' "

        if filePath[-13:] == '-citation.csv':
            metadataInfo += ("details the organisations that provided the records you have downloaded. "
            "Look at the license agreement for each ('Rights' column) and use the citation text ('Citation' column) "
            "where appropriate to credit the data providers in your work.")
            self.defaultColumns=["Name", "Citation", "Rights", "Number of Records in Download"]
        else:
            metadataInfo += " details the columns included in the CSV data file you downloaded."
            self.defaultColumns=[]

        self.lblMetadata.setText(metadataInfo)

        #Load the table widget with the CSV
        self.twMetadata.clearContents()
        self.twMetadata.setSortingEnabled(False)
        with open(filePath, newline='') as csvfile:
            reader = csv.reader(csvfile)
            self.twMetadata.setRowCount(sum(1 for row in reader)-1)
        with open(filePath, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                self.twMetadata.setColumnCount(len(row))
                #self.twMetadata.setHorizontalHeaderLabels(row) 
                colCount = 0
                for cellText in row:
                    headerItem = QTableWidgetItem(cellText)
                    headerItem.setTextAlignment(Qt.AlignLeft)
                    self.twMetadata.setHorizontalHeaderItem(colCount, headerItem)
                    colCount += 1
                break
            rowCount = 0
            for row in reader:
                colCount = 0
                for cellText in row:
                    cell = QTableWidgetItem(cellText, 0)
                    self.twMetadata.setItem(rowCount, colCount, cell)
                    colCount += 1
                rowCount += 1
        self.twMetadata.setSortingEnabled(True)
        
        #Select the metadata tab
        self.tabWidget.setCurrentWidget(self.tabMetadata)

        #Sort out column visibility
        self.showHideMetadataColumns()

    def showHideMetadataColumns(self):
        if len(self.defaultColumns) == 0:
            self.cbShowAllMetadata.setCheckState(Qt.Unchecked)
            self.cbShowAllMetadata.setEnabled(False)
        else:
            self.cbShowAllMetadata.setEnabled(True)

            for i in range(0, self.twMetadata.columnCount()):

                headerItem = self.twMetadata.horizontalHeaderItem(i)
                self.logMessage(str(i) + " " +  headerItem.text())
                if (not headerItem.text() in self.defaultColumns) and self.cbShowAllMetadata.checkState() == Qt.Unchecked:
                    self.twMetadata.hideColumn(i)
                else:
                    self.twMetadata.showColumn(i)

    def restRequest(self, url, postData=None, callType="data", downloadInfo=None):
        #This function adapted from __sync_request function in
        #QuickMapServices plugin (extra_sources.py module)
        #Also informed by https://github.com/qgis/QGIS/pull/2299/files
        #and http://nullege.com/codes/search/PyQt4.QtNetwork.QNetworkAccessManager

        self.logMessage("Endpoint: " + url)

        endpoint = QUrl(url)
        request = QNetworkRequest(endpoint)

        # Determine if post or get and set accordingly
        if postData is None:
            QgsMessageLog.logMessage("Issue get request", "NBN Tool")
            reply = QgsNetworkAccessManager.instance().get(request)
        else:
            QgsMessageLog.logMessage("Issue post request", "NBN Tool")
            reply = QgsNetworkAccessManager.instance().post(request, postData)

        if callType == "download":
            downloadInfo["reply"] = reply
            #Don't know under what circumstances, but sometimes get an error at the end of execution...
            #reply.finished.connect(lambda: self.downLoadFinished(downloadInfo))
		    #NameError: free variable 'self' referenced before assignment in enclosing scope
            #So this needs trapping.
            try:
                reply.finished.connect(lambda: self.downLoadFinished(downloadInfo))
            except:
                e = sys.exc_info()[0]
                QgsMessageLog.logMessage("error generated lambda", "NBN Tool")
                downloadInfo["twi"].setIcon(0, QIcon( self.pathPlugin % "images/cross.png" ))
                self.iface.messageBar().pushMessage("Error", "NBN web service error. Error: %s" % (str(e)), level=Qgis.Warning)
            return

        # Wait
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        QgsMessageLog.logMessage("exec loop", "NBN Tool")
        loop.exec_()
        QgsMessageLog.logMessage("loop ended", "NBN Tool")
        reply.finished.disconnect(loop.quit)
        loop = None

        error = reply.error()
        if error != QNetworkReply.NoError:
            QgsMessageLog.logMessage("error generated", "NBN Tool")
            self.iface.messageBar().pushMessage("Error", "NBN web service error. Error: %d %s" % (error, reply.errorString()), level=Qgis.Warning)
            return None

        # If the return is a re-direction then execute that redirection
        resultCode = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if resultCode in [301, 302, 307]:
            redirectUrl = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
            return self.restRequest(redirectUrl, postData, callType)

        # Set the result object
        result = reply.readAll()
        reply.deleteLater()

        QgsMessageLog.logMessage("returning result", "NBN Tool")
        return result

   

