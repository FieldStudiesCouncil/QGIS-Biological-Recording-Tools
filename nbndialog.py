# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NBNDialog
                                 A QGIS plugin
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

from ui_nbn import Ui_nbn
import os.path
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from filedialog import FileDialog
import urllib, urllib2
#import cookielib
import json 
import hashlib, uuid
import shutil
from osgr import *
from envmanager import *
#import threading
import csv

#import requests

class NBNDialog(QWidget, Ui_nbn):

    displayNBNCSVFile = pyqtSignal(basestring)

    def __init__(self, iface, dockwidget):
        QWidget.__init__(self)
        Ui_nbn.__init__(self)
        self.setupUi(self)
        self.canvas = iface.mapCanvas()
        self.iface = iface
    
        self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        
        # Get a reference to an osgr object and an osgrLayer object
        self.osgr = osgr()
        
        # Load the environment stuff
        self.env = envManager()
        
        # WMS
        self.pbSpeciesWMS.clicked.connect(self.WMSFetchSpecies)
        self.pbDatasetWMS.clicked.connect(self.WMSFetchDataset)
        self.pbDesignationWMS.clicked.connect(self.WMSFetchDesignation)
        self.butTaxonSearch.clicked.connect(self.taxonSearch)
        self.butClearLast.clicked.connect(self.removeMap)
        self.butClear.clicked.connect(self.removeMaps)
        self.pbLogin.clicked.connect(self.loginNBN)
        self.pbLogout.clicked.connect(self.logoutNBN)
        self.butHelp.clicked.connect(self.helpFile)
        self.pbAttention.clicked.connect(self.nbnAttentionFile)
        self.pbRefreshDatasets.clicked.connect(self.refreshDatasets)
        self.pbRefreshDesignations.clicked.connect(self.refreshDesignations)
        self.pbRefreshGroups.clicked.connect(self.refreshGroups)
        self.pbRefreshAreas.clicked.connect(self.refreshBothAreas)
        self.pbUncheckAll.clicked.connect(self.uncheckAll)
        self.twDatasets.itemClicked.connect(self.datasetTwClick)
        self.twDesignations.itemClicked.connect(self.designationTwClick)
        self.twGroups.itemClicked.connect(self.groupTwClick)
        self.twAreas.itemClicked.connect(self.siteTwClick)
        self.twTaxa.itemClicked.connect(self.taxaTwClick)
        self.cbStartYear.stateChanged.connect(self.checkFilters)
        self.cbEndYear.stateChanged.connect(self.checkFilters)
        self.rbAbsence.toggled.connect(self.checkFilters)
        self.leGridRef.textChanged.connect(self.checkFilters)
        self.twAreaCategories.itemDoubleClicked.connect(self.readAreaFile)
        self.pbBuffer.clicked.connect(self.generateBuffer)
        self.pbClearLastBuffer.clicked.connect(self.removeBuffer)
        self.rbGR.toggled.connect(self.bufferEnableDisable)
        self.pbDownloadGridRef.clicked.connect(self.downloadNBNObservations)
        self.pbSendToBiorec.clicked.connect(self.displayCSV)
        
        # Map canvas events
        self.canvas.extentsChanged.connect(self.mapExtentsChanged)
        self.canvas.selectionChanged.connect(self.checkMapSelectionFilter)
        self.iface.currentLayerChanged.connect(self.checkMapSelectionFilter)
        
        # Make a coordinate translator. Also need global references to OSGB and canvas CRSs since
        # they cannot be retrieved from a translator object.
        self.canvasCrs = self.canvas.mapRenderer().destinationCrs()
        self.osgbCrs = QgsCoordinateReferenceSystem("EPSG:27700")
        self.transformCrs = QgsCoordinateTransform(self.canvas.mapRenderer().destinationCrs(), QgsCoordinateReferenceSystem("EPSG:27700"))
        
        # Inits
        self.nbnOSLayerName = "NBN OS Backdrop"
        self.layers = []
        self.buffers = []
        self.tvks = {} #Initialise tvk dictionary
        self.pbSendToBiorec.setIcon(QIcon( self.pathPlugin % "images/maptaxa.png" ))
        self.butClearLast.setIcon(QIcon( self.pathPlugin % "images/removelayer.png" ))
        self.butClear.setIcon(QIcon( self.pathPlugin % "images/removelayers.png" ))
        self.pbSpeciesWMS.setIcon(QIcon( self.pathPlugin % "images/nbngridmap.png" ))
        self.pbDatasetWMS.setIcon(QIcon( self.pathPlugin % "images/nbngridmap.png" ))
        self.pbDesignationWMS.setIcon(QIcon( self.pathPlugin % "images/nbngridmap.png" ))
        self.pbDownloadGridRef.setIcon(QIcon( self.pathPlugin % "images/nbndownload.png" ))
        self.butTaxonSearch.setIcon(QIcon( self.pathPlugin % "images/speciesinventory.png" ))
        self.pbBuffer.setIcon(QIcon( self.pathPlugin % "images/buffer.png" ))
        self.pbClearLastBuffer.setIcon(QIcon( self.pathPlugin % "images/bufferclear.png" ))
        self.pbAttention.setIcon(QIcon( self.pathPlugin % "images/warning.png" ))
        self.pbAttention.setText("NBN changes coming - click for details")
        #self.butOS.setIcon(QIcon( self.pathPlugin % "images/os.png" ))
        self.butHelp.setIcon(QIcon( self.pathPlugin % "images/bang.png" ))
        self.twTaxa.setHeaderLabel("Matching taxa")
        self.noLoginText = "Not logged in to NBN. Default NBN access will apply."
        self.lblLoginStatus.setText (self.noLoginText)
        self.currentNBNUser = ""
        self.nbnAthenticationCookie = None
        self.guiFile = None
        self.infoFile = os.path.join(os.path.dirname( __file__ ), "infoNBNTool.txt")
        self.nbnAttentionFile = os.path.join(os.path.dirname( __file__ ), "nbnAttention.txt")
        self.readDatasetFile()
        self.readDesignationFile()
        self.readGroupFile()
        self.readAreaCategoriesFile()
        self.datasetSelectionChanged()
        self.checkFilters()
        self.lblSiteDataset.setText("")
        self.bufferEnableDisable()
        
        self.WMSType = self.enum(species=1, dataset=2, designation=3)
     
    def showEvent(self, ev):
        # Load the environment stuff
        self.env = envManager()
        self.leUsername.setText(self.env.getEnvValue("nbn.username"))
        self.lePassword.setText(self.env.getEnvValue("nbn.password"))
        return QWidget.showEvent(self, ev)        
        
    def enum(self, **enums):
        return type('Enum', (), enums)
    
    def infoMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Info", strMessage, level=QgsMessageBar.INFO)
        
    def warningMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Warning", strMessage, level=QgsMessageBar.WARNING)
        
    def errorMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Error", strMessage, level=QgsMessageBar.CRITICAL)
        
    def bugTest(self):
        url = ("url=https://gis.nbn.org.uk/SingleSpecies/NHMSYS0000530739&" +
        "layers=Grid-100m&layers=Grid-1km&layers=Grid-2km&layers=Grid-10km" +
        "&styles=&styles=&styles=&styles=" +
        "&format=image/png&crs=EPSG:27700")
        
        rlayer = QgsRasterLayer(url, 'NBN WMS layer', 'wms')
        QgsMapLayerRegistry.instance().addMapLayer(rlayer)
        
        rlayer.setSubLayerVisibility("Grid-10km", False)
        rlayer.setSubLayerVisibility("Grid-2km", True)
        rlayer.setSubLayerVisibility("Grid-1km", False)
        rlayer.setSubLayerVisibility("Grid-100m", False)
        
    def uncheckAll(self):
              
        for iProvider in range(self.twDatasets.topLevelItemCount()):
            twiProvider = self.twDatasets.topLevelItem(iProvider)
            twiProvider.setCheckState(0, Qt.Unchecked)
            for iDataset in range(twiProvider.childCount()):
                twiDataset = twiProvider.child(iDataset)
                twiDataset.setCheckState(0, Qt.Unchecked)
            
        self.datasetSelectionChanged()
        
    def bufferEnableDisable(self):
        if self.rbGR.isChecked():
            self.sbEasting.setEnabled(False)
            self.sbNorthing.setEnabled(False)
            self.lePointBufferGR.setEnabled(True)
        else:
            self.sbEasting.setEnabled(True)
            self.sbNorthing.setEnabled(True)
            self.lePointBufferGR.setEnabled(False)
           
    def generateBuffer(self):
    
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
        else:
            easting = self.sbEasting.value()
            northing = self.sbNorthing.value()
            
            sName = str(easting) + "/" + str(northing)
            
        sName = sName + " " + str(self.sbBuffer.value()) + "m"
        
        geom = self.osgr.circleGeom(easting, northing, self.sbBuffer.value())
        
        # Create layer 
        self.vl = QgsVectorLayer("Polygon?crs=epsg:27700", sName, "memory")
        self.pr = self.vl.dataProvider()
        self.buffers.append(self.vl.id())

        # Symbology
        props = { 'color' : '255,0,0,100', 'color_border' : '0,0,0,200', 'style' : 'solid', 'style_border' : 'solid' }
        s = QgsFillSymbolV2.createSimple(props)
        self.vl.setRendererV2( QgsSingleSymbolRendererV2( s ) )

        # Add to map layer registry
        QgsMapLayerRegistry.instance().addMapLayer(self.vl)    
        
        # Add geometry to layer
        fet = QgsFeature()
        fet.setGeometry(geom)
        self.vl.startEditing()
        self.vl.addFeatures([fet])
        self.vl.commitChanges()
        self.vl.updateExtents()

        # Zoom to buffer extent
        self.iface.actionZoomToLayer().trigger()
        
        self.checkMapSelectionFilter()
        
    def datasetTwClick(self, twItem, iCol):
              
        for iDataset in range(twItem.childCount()):
            twiDataset = twItem.child(iDataset)
            twiDataset.setCheckState(0, twItem.checkState(0))
            
        if twItem.childCount() > 0:
            twItem.setExpanded(twItem.checkState(0) == Qt.Checked)
            
        self.datasetSelectionChanged()
        
    def taxaTwClick(self, twItem, iCol):
        
        #If current item is checked, uncheck all others
        #Only one taxon can be checked.
        
        if twItem.checkState(0) == Qt.Checked:
            for iGroup in range(self.twTaxa.topLevelItemCount()):
                twiGroup = self.twTaxa.topLevelItem(iGroup)
                for iTaxa in range(twiGroup.childCount()):
                    twiTaxa = twiGroup.child(iTaxa)
                    if not twiTaxa == twItem:
                        twiTaxa.setCheckState(0, Qt.Unchecked)
                        
        self.checkFilters()
        
    def designationTwClick(self, twItem, iCol):
        
        #If current item is checked, uncheck all others
        #Only one designation can be checked.
        
        if twItem.checkState(0) == Qt.Checked:
            for iDesignation in range(self.twDesignations.topLevelItemCount()):
                twiDesignation = self.twDesignations.topLevelItem(iDesignation)
                if not twiDesignation == twItem:
                    twiDesignation.setCheckState(0, Qt.Unchecked)
            
        self.checkFilters()
        
    def datasetSelectionChanged(self):
        
        iChecked = 0
        for iProvider in range(self.twDatasets.topLevelItemCount()):
            twiProvider = self.twDatasets.topLevelItem(iProvider)
            for iDataset in range(twiProvider.childCount()):
                twiDataset = twiProvider.child(iDataset)
                if twiDataset.checkState(0) == Qt.Checked:
                    iChecked += 1
                    
        if iChecked == 0:
            self.lblDatasetFilter.setText("No datasets selected.")
        else:
            self.lblDatasetFilter.setText(str(iChecked) + " datasets selected.")
            
        self.checkFilters()
         
    def groupTwClick(self, twItem, iCol):
        
        #If current item is checked, uncheck all others
        #Only one group can be checked.
        
        if twItem.checkState(0) == Qt.Checked:
            for iGroup in range(self.twGroups.topLevelItemCount()):
                twiGroup = self.twGroups.topLevelItem(iGroup)
                if not twiGroup == twItem:
                    twiGroup.setCheckState(0, Qt.Unchecked)
        
        self.checkFilters()        
        
    def siteTwClick(self, twItem, iCol):
        
        #If current item is checked, uncheck all others
        #Only one site can be checked.
        
        if twItem.checkState(0) == Qt.Checked:
            for iSite in range(self.twAreas.topLevelItemCount()):
                twiSite = self.twAreas.topLevelItem(iSite)
                if not twiSite == twItem:
                    twiSite.setCheckState(0, Qt.Unchecked)
        
        self.checkFilters()
         
    def refreshGroups(self):
        
        self.twGroups.clear()
        
        url = 'https://data.nbn.org.uk/api/taxonOutputGroups'
        res = self.restRequest(url)

        if res is None:
            return

        #responseText = res.data().decode('utf-8')
        responseText = res.data()

        # Write the json data to a file
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "taxongroups.json"))
        with open(datafile, 'w') as jsonfile:
            jsonfile.write(responseText)
            
        # Rebuild designation tree
        self.readGroupFile()
        
        self.checkFilters()
        
    def refreshAreaCategories(self):
        
        self.twAreaCategories.clear()
       
        url = 'https://data.nbn.org.uk/api/siteBoundaryCategories'
        res = self.restRequest(url)

        if res is None:
            return

        #responseText = res.data().decode('utf-8')
        responseText = res.data()

        # Write the json data to a file
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "siteboundarycats.json"))
        with open(datafile, 'w') as jsonfile:
            jsonfile.write(responseText)
            
        # Rebuild area category tree
        self.readAreaCategoriesFile()
        
    def refreshBothAreas(self):
        self.refreshAreaCategories()
        self.refreshAreas()
        
    def refreshAreas(self):
        
        self.twAreas.clear()
        
        twis = self.twAreaCategories.selectedItems()
        if len(twis) == 0:
            #self.infoMessage("First select a site boundary dataset.")
            return
            
        twi = twis[0]
        nbnKey = twi.toolTip(0)
      
        url = 'https://data.nbn.org.uk/api/siteBoundaryDatasets/%s/siteBoundaries' % nbnKey
        res = self.restRequest(url)

        if res is None:
            return

        #responseText = res.data().decode('utf-8')
        responseText = res.data()

        # Write the json data to a file
        datafile = self.pathPlugin % ("NBNCache%s%s%s" % (os.path.sep, nbnKey, ".json"))
        with open(datafile, 'w') as jsonfile:
            jsonfile.write(responseText)
            
        # Rebuild area tree
        self.readAreaFile()
    
    def readGroupFile(self):
    
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "taxongroups.json"))
        if not os.path.isfile(datafile):
            self.infoMessage("NBN group file not found.")
            return
        try:
            with open(datafile) as f:
                jsonData = json.load(f)
        except:
            self.warningMessage("NBN group file failed to load. Use the refresh button to generate a new one.")
            return
          
        """
        groups = {}
       
        for jGroup in jsonData:
                 
            try:
                keyParent = jGroup["parentTaxonGroupKey"]
            except:
                keyParent = "NoParentKey"
                
            key = jGroup["key"]
            name = jGroup["name"]
            
            if keyParent in groups:
                parentDict = groups[keyParent]
            else:
                parentDict = groups[keyParent] = {}
                
            parentDict[name] = key
            
        #Iterate in the desired order
        for keyParent in sorted(groups.keys()):
            parentDict = groups[keyParent]
            for nameKey in sorted(parentDict.keys()):
                key = parentDict[nameKey]

                # Create a tree item for the group
                twiGroup = QTreeWidgetItem(self.twGroups)
                twiGroup.setText(0, nameKey)
                twiGroup.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                twiGroup.setCheckState(0, Qt.Unchecked) # 0 is the column number 
                twiGroup.setToolTip(0, key)
                self.twGroups.addTopLevelItem(twiGroup)
        """
        for jGroup in jsonData:
                 
            # Create a tree item for the group
            twiGroup = QTreeWidgetItem(self.twGroups)
            twiGroup.setText(0, jGroup["name"])
            twiGroup.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            twiGroup.setCheckState(0, Qt.Unchecked) # 0 is the column number 
            twiGroup.setToolTip(0, jGroup["key"])
            self.twGroups.addTopLevelItem(twiGroup)
                
        self.twGroups.sortItems(0, Qt.AscendingOrder)
    
    def readAreaCategoriesFile(self):
    
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "siteboundarycats.json"))
        if not os.path.isfile(datafile):
            self.infoMessage("NBN site boundary category file not found. Use the refresh button to generate a new one.")
            return
        try:
            with open(datafile) as f:
                jsonData = json.load(f)
        except:
            self.warningMessage("NBN site boundary category file failed to load. Use the refresh button to generate a new one.")
            return

        for jAC in jsonData:
                 
            # Create a top-level tree item for the dataset category
            twiAC = QTreeWidgetItem(self.twAreaCategories)
            twiAC.setText(0, jAC["name"])
            self.twAreaCategories.addTopLevelItem(twiAC)
            
            for jDataset in jAC["siteBoundaryDatasets"]:
                # Create a tree item for the dataset
                twiDataset = QTreeWidgetItem(twiAC)
                twiDataset.setText(0, jDataset["title"])
                twiDataset.setToolTip(0, str(jDataset["datasetKey"]))
                self.twAreaCategories.addTopLevelItem(twiDataset)
        
    def readAreaFile(self):
    
        self.twAreas.clear()
        QCoreApplication.processEvents()
        
        twis = self.twAreaCategories.selectedItems()
        
        if len(twis) == 0:
            return
        
        if twis[0].childCount() > 0:
            return

        twi = twis[0]
        nbnKey = twi.toolTip(0)
        nbnName = twi.text(0)
        
        
        datafile = self.pathPlugin % ("NBNCache%s%s%s" % (os.path.sep, nbnKey, ".json"))
        if not os.path.isfile(datafile):
            self.refreshAreas()
            #self.infoMessage("File not found for '%s'. Use the site refresh button to generate a new one." % nbnName)
            return
        try:
            with open(datafile) as f:
                jsonData = json.load(f)
        except:
            self.warningMessage("File not found for '%s' failed to load. Use the refresh button to generate a new one." % nbnName)
            return
        
        self.lblSiteDataset.setText("%s:" % nbnName)
        
        for jSite in jsonData:
                 
            # Create a tree item for the group
            twiSite = QTreeWidgetItem(self.twAreas)
            twiSite.setText(0, jSite["name"])
            twiSite.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            twiSite.setCheckState(0, Qt.Unchecked) # 0 is the column number 
            twiSite.setToolTip(0, str(jSite["identifier"]))
            self.twAreas.addTopLevelItem(twiSite)
                
        self.twAreas.sortItems(0, Qt.AscendingOrder)
        
    def refreshDesignations(self):
        
        self.twDesignations.clear()
        
        url = 'https://data.nbn.org.uk/api/designations'
        res = self.restRequest(url)

        if res is None:
            return

        #responseText = res.data().decode('utf-8')
        responseText = res.data()

        # Write the json data to a file
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "designations.json"))
        with open(datafile, 'w') as jsonfile:
            jsonfile.write(responseText)
            #json.dump(responseText, jsonfile)

        # Rebuild designation tree
        self.readDesignationFile()
  
        self.checkFilters()
        
    def readDesignationFile(self):
    
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "designations.json"))
        if not os.path.isfile(datafile):
            self.infoMessage("NBN designation file not found.")
            return
            
        try:
            with open(datafile) as f:
                jsonData = json.load(f)
        except:
            self.warningMessage("NBN designation file failed to load. Use the refresh button to generate a new one.")
            return
            
        treeNodes = {} #Dictionary
        
        for jDesignation in jsonData:
                 
            # Create a tree item for the designation
            twiDesignation = QTreeWidgetItem(self.twDesignations)
            twiDesignation.setText(0, jDesignation["code"])
            twiDesignation.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            twiDesignation.setCheckState(0, Qt.Unchecked) # 0 is the column number 
            twiDesignation.setToolTip(0, jDesignation["name"])
            self.twDesignations.addTopLevelItem(twiDesignation)
                
        self.twDesignations.sortItems(0, Qt.AscendingOrder)
        
    def refreshDatasets(self):
        
        self.twDatasets.clear()
        
        url = 'https://data.nbn.org.uk/api/datasets'
        res = self.restRequest(url)

        if res is None:
            return

        #responseText = res.data().decode('utf-8')
        responseText = res.data()

        # Write the json data to a file
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "datasets.json"))
        with open(datafile, 'w') as jsonfile:
            jsonfile.write(responseText)
            
        # Rebuild dataset tree
        self.readDatasetFile()
        self.datasetSelectionChanged()
            
    def readDatasetFile(self):
    
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "datasets.json"))
        if not os.path.isfile(datafile):
            self.infoMessage("NBN dataset file not found.")
            return
            
        try:
            with open(datafile) as f:
                jsonData = json.load(f)
        except:
            self.warningMessage("NBN dataset file failed to load. Use the refresh button to generate a new one.")
            return
            
        treeNodes = {} #Dictionary
        
        for jDataset in jsonData:
        
            if not jDataset["organisationName"] in(treeNodes.keys()):
                #Create a new top level tree item for the dataset provider organisation
                twiOrganisation = QTreeWidgetItem(self.twDatasets)
                twiOrganisation.setText(0, jDataset["organisationName"])
                twiOrganisation.setExpanded(False)
                twiOrganisation.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                twiOrganisation.setCheckState(0, Qt.Unchecked) # 0 is the column number 
                self.twDatasets.addTopLevelItem(twiOrganisation)
                #Add to dictionary
                treeNodes[jDataset["organisationName"]] = twiOrganisation
            else:
                twiOrganisation = treeNodes[jDataset["organisationName"]]
            
            # Create a tree item for the dataset
            twiDataset = QTreeWidgetItem(twiOrganisation)
            twiDataset.setText(0, jDataset["title"])
            twiDataset.setExpanded(False)
            twiDataset.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            twiDataset.setCheckState(0, Qt.Unchecked) # 0 is the column number 
            twiDataset.setToolTip(0, jDataset["key"])
            self.twDatasets.addTopLevelItem(twiOrganisation)
                
        self.twDatasets.sortItems(0, Qt.AscendingOrder)
        
    def helpFile(self):
        
        #if self.guiFile is None:
        self.guiFile = FileDialog(self.iface, self.infoFile)
        
        self.guiFile.setVisible(True)

    def nbnAttentionFile(self):
        
        #if self.guiFile is None:
        self.guiFile = FileDialog(self.iface, self.nbnAttentionFile)
        
        self.guiFile.setVisible(True)    
        
    def taxonSearch(self):
        if self.leTaxonSearch.text() == "":
            self.iface.messageBar().pushMessage("No search term specified.", level=QgsMessageBar.INFO)
            return

        url = 'https://data.nbn.org.uk/api/taxa?q=' + self.leTaxonSearch.text()
        res = self.restRequest(url)

        if res is None:
            return

        responseText = res.data().decode('utf-8')
        jsonData = json.loads(responseText) 
        jResponseList = jsonData["results"]

         #Tree view
        self.twTaxa.clear()
        treeNodes = {} #Dictionary
        
        for jTaxon in jResponseList:
        
            if not jTaxon["taxonOutputGroupName"] in(treeNodes.keys()):
                #Create a new top level tree item for the taxon group
                twiGroup = QTreeWidgetItem(self.twTaxa)
                twiGroup.setText(0, jTaxon["taxonOutputGroupName"])
                twiGroup.setExpanded(False)
                twiGroup.setFlags(Qt.ItemIsEnabled) #By resetting the flags, we take off default isSelectable
                twiGroup.setIcon(0, QIcon( self.pathPlugin % "images/Group20x16.png" ))
                self.twTaxa.addTopLevelItem(twiGroup)
                #Add to dictionary
                treeNodes[jTaxon["taxonOutputGroupName"]] = twiGroup
            else:
                twiGroup = treeNodes[jTaxon["taxonOutputGroupName"]]
                
            if not jTaxon["ptaxonVersionKey"] in(treeNodes.keys()):
                #Create a child tree item for the preferred TVK group
                twiPTVK = QTreeWidgetItem(twiGroup)
                twiPTVK.setText(0, jTaxon["ptaxonVersionKey"])
                #twiPTVK.setText(0, self.nameFromTVK(jTaxon["ptaxonVersionKey"]))
                #twiPTVK.setIcon(0, QIcon( self.pathPlugin % "images/Taxon20x16.png" ))
                twiPTVK.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                twiPTVK.setCheckState(0, Qt.Unchecked) # 0 is the column number 
                twiPTVK.setExpanded(True)
                self.twTaxa.addTopLevelItem(twiPTVK)
                #Add to dictionary
                treeNodes[jTaxon["ptaxonVersionKey"]] = twiPTVK
            else:
                twiPTVK = treeNodes[jTaxon["ptaxonVersionKey"]]
                
            #Create a new child item for the taxon name
            twiName = QTreeWidgetItem(twiPTVK)
            twiName.setText(0, jTaxon["name"])
            twiName.setIcon(0, QIcon( self.pathPlugin % "images/Synonym20x16.png" ))
            twiName.setFlags(Qt.ItemIsEnabled) #By resetting the flags, we take off default isSelectable
            self.twTaxa.addTopLevelItem(twiName)

    def getSelectedTaxonOutputGroup(self):
        
        #Selected taxon output group
        for iGroup in range(self.twGroups.topLevelItemCount()):
            twiGroup = self.twGroups.topLevelItem(iGroup)
            if twiGroup.checkState(0) == Qt.Checked:
                return twiGroup.toolTip(0)
                
        return None
        
    def getSelectedSite(self):
        
        #Selected site
        for iSite in range(self.twAreas.topLevelItemCount()):
            twiSite = self.twAreas.topLevelItem(iSite)
            if twiSite.checkState(0) == Qt.Checked:
                return twiSite.toolTip(0)
                
        return None
        
    def getSelectedDesignation(self):
        
        #Selected designation
        iDesignationCount = 0
        for iDesignation in range(self.twDesignations.topLevelItemCount()):
            twiDesignation = self.twDesignations.topLevelItem(iDesignation)
            if twiDesignation.checkState(0) == Qt.Checked:
                iDesignationCount += 1
                selectedDesignationKey = twiDesignation.text(0)
                strName = twiDesignation.text(0)
                            
                return (strName, selectedDesignationKey)
        return ()
        
    def WMSFetchDesignation(self):
                            
        ret = self.getSelectedDesignation()
     
        #Check item in treeview is selected
        if len(ret) == 0:
            self.iface.messageBar().pushMessage("Info", "First select a designation.", level=QgsMessageBar.INFO)
            return
        else:
            strName = ret[0]
            selectedDesignationKey = ret[1]
            
        #selectedDesignationKey = "NOTABLE" # For testing
        
        #Get the map from NBN
        url = 'https://gis.nbn.org.uk/DesignationSpeciesDensity/'
        
        #Designation
        url = url + selectedDesignationKey
        #self.infoMessage(url)
        
        self.WMSFetch(url, strName, self.WMSType.designation)
        
    def getSelectedDatasets(self):
        
        ret = {}
        # Selected datasets
        iDatasetCount = 0
        for iProvider in range(self.twDatasets.topLevelItemCount()):
            twiProvider = self.twDatasets.topLevelItem(iProvider)
            for iDataset in range(twiProvider.childCount()):
                twiDataset = twiProvider.child(iDataset)
                if twiDataset.checkState(0) == Qt.Checked:
                    iDatasetCount += 1
                    selectedDatasetKey = twiDataset.toolTip(0)
                    strName = twiDataset.text(0)
                    
                    ret[selectedDatasetKey] = strName
        return ret
                    
    def WMSFetchDataset(self):
       
        datasets = self.getSelectedDatasets()
         
        #Check item in treeview is selected
        if len(datasets) == 0:
            self.iface.messageBar().pushMessage("Info", "First select a dataset.", level=QgsMessageBar.INFO)
            return
        elif len(datasets) > 1:
            self.iface.messageBar().pushMessage("Info", "More than one dataset selected. You can only use one for the dataset species density map.", level=QgsMessageBar.INFO)
            return
            
        selectedDatasetKey = datasets.keys()[0]
        strName = datasets[selectedDatasetKey]
            
        #selectedDatasetKey = "GA001349" # For testing
        
        #Get the map from NBN
        url = 'https://gis.nbn.org.uk/DatasetSpeciesDensity/'
        
        #Dataset
        url = url + selectedDatasetKey
        
        self.WMSFetch(url, strName, self.WMSType.dataset)
        
    def getSelectedTVK(self):
       
        iCount = 0
        for iGroup in range(self.twTaxa.topLevelItemCount()):
            twiGroup = self.twTaxa.topLevelItem(iGroup)
            for iTaxa in range(twiGroup.childCount()):
                twiTaxa = twiGroup.child(iTaxa)
                if twiTaxa.checkState(0) == Qt.Checked:
                    iCount += 1
                    selectedTVK = twiTaxa.text(0)
                    
        #Check item in treeview is selected
        if iCount == 0:
            return None
        else:
            return selectedTVK
        
    def WMSFetchSpecies(self):
        
        selectedTVK = self.getSelectedTVK()
        if selectedTVK is None:
            self.iface.messageBar().pushMessage("Info", "First check a taxon code (TVK).", level=QgsMessageBar.INFO)
            return
           
        #Get the map from NBN
        url = 'https://gis.nbn.org.uk/SingleSpecies/'
        
        #Taxon
        url = url + selectedTVK
        
        #Name
        strName = self.nameFromTVK(selectedTVK)
        
        #Get the OS map if requested and not already displayed
        if self.cbOS.isChecked():
            if len(QgsMapLayerRegistry.instance().mapLayersByName(self.nbnOSLayerName)) == 0:
                self.osBackdrop(selectedTVK)
        
        #Get the species map
        self.WMSFetch(url, strName, self.WMSType.species)

    def WMSFetch(self, url, strName, wmsType):
        
        bURLextended = False
        
        #Set user login stuff
        if not self.leUsername.text() == "" and not self.lePassword.text() == "":
            url = url + "?username=" + self.leUsername.text()
            hashed_password = hashlib.md5(self.lePassword.text()).hexdigest()
            url = url + "&userkey=" + hashed_password
            bURLextended = True
            
        #Start year filter
        if self.cbStartYear.isChecked():
            if not bURLextended:
                url = url + "?"
            else:
                url = url + "&"
            url = url + "startyear=" + str(self.sbStartYear.value())
            bURLextended = True
            
        #End year filter
        if self.cbEndYear.isChecked():
            if not bURLextended:
                url = url + "?"
            else:
                url = url + "&"
            url = url + "endyear=" + str(self.sbEndYear.value())
            bURLextended = True
            
        #Presence/absence
        if self.rbAbsence.isChecked():
            if not bURLextended:
                url = url + "?"
            else:
                url = url + "&"
            url = url + "abundance=absence"
            bURLextended = True
        
        #Datasets
        if wmsType == self.WMSType.species or wmsType == self.WMSType.designation:
            strDatasets = ""
            for iProvider in range(self.twDatasets.topLevelItemCount()):
                twiProvider = self.twDatasets.topLevelItem(iProvider)
                for iDataset in range(twiProvider.childCount()):
                    twiDataset = twiProvider.child(iDataset)
                    if twiDataset.checkState(0) == Qt.Checked:
                        if strDatasets == "":
                            strDatasets = "datasets=" + twiDataset.toolTip(0)
                        else:
                            strDatasets = strDatasets + "," + twiDataset.toolTip(0)
            
            if strDatasets <> "":
                if not bURLextended:
                    url = url + "?"
                else:
                    url = url + "&"
                url = url + strDatasets
                bURLextended = True
            
        #URL encode      
        url = urllib.quote_plus(url) # encode the url
        
        #Set layer stuff
        strStyles="&styles="
        if self.cbGridSize.currentIndex() == 4:
            strLayers = "&layers=Grid-100m"
            strName = strName + " NBN 100 m"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType)
        elif self.cbGridSize.currentIndex() == 3:
            strLayers = "&layers=Grid-1km"
            strName = strName + " NBN monad"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType)
        elif self.cbGridSize.currentIndex() == 2:
            strLayers = "&layers=Grid-2km"
            strName = strName + " NBN tetrad"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType)
        elif self.cbGridSize.currentIndex() == 1:
            strLayers = "&layers=Grid-10km"
            strName = strName + " NBN hectad"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType)
        #elif self.cbGridSize.currentIndex() == 1:
        #    strLayers = "&layers=Grid-10km&layers=Grid-2km&layers=Grid-1km&layers=Grid-100m"
        #    strStyles="&styles=&styles=&styles=&styles="
        #    strName = strName + " NBN auto"
        #    self.addWMSRaster(url, strLayers, strStyles, strName, wmsType)
        else:
            strNamePrefix = strName
            strLayers = "&layers=Grid-100m"
            strName = strNamePrefix + " NBN 100 m (auto)"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType, 0, 15000)
            strLayers = "&layers=Grid-1km"
            strName = strNamePrefix + " NBN monad (auto)"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType, 15001, 100000)
            strLayers = "&layers=Grid-2km"
            strName = strNamePrefix + " NBN tetrad (auto)"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType, 100001, 250000)
            strLayers = "&layers=Grid-10km"
            strName = strNamePrefix + " NBN hectad (auto)"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType, 250000, 100000000)
                 
        if strName.endswith("auto") or strName.endswith("(auto)"):
            #self.canvas.extentsChanged.emit() #Doesn't seem to invoke the web service, perhaps because the extents haven't actually changed
            rectExtent = self.canvas.extent()
            self.canvas.setExtent(QgsRectangle())
            self.canvas.refresh()
            self.canvas.setExtent(rectExtent)
            self.canvas.refresh()
            
    def osBackdrop(self, tvk="NBNSYS0000530739"):
    
        url = urllib.quote_plus('https://gis.nbn.org.uk/SingleSpecies/%s' % tvk) 
        strStyles="&styles="
        strLayers = "&layers=OS-Scale-Dependent"
        self.addWMSRaster(url, strLayers, strStyles, self.nbnOSLayerName, self.WMSType.species)
            
    def addWMSRaster(self, url, strLayers, strStyles, strName, wmsType, minExtent=0, maxExtent=0):
    
        url = 'url=' + url + strLayers + strStyles + "&format=image/png&crs=EPSG:27700" #falls over without the styles argument
        url = url.replace(' ','%20')      
        rlayer = QgsRasterLayer(url, 'layer', 'wms')
        
        if not rlayer.isValid():
            self.iface.messageBar().pushMessage("Error", "Layer failed to load. URL: " + url, level=QgsMessageBar.CRITICAL)
            return None

        rlayer.setLayerName(strName)
        opacity = (100-self.hsTransparency.value()) * 0.01
        rlayer.renderer().setOpacity(opacity)
        
        """
        #Doesn't work at the anticipated zoom levels
        #So we set visibility manually using mapExtentsChanged event
        if not (minExtent == 0 and  maxExtent == 0):
            rlayer.setMinimumScale(minExtent)
            rlayer.setMaximumScale(maxExtent)
            rlayer.toggleScaleBasedVisibility(True)
        """
        
        if strName != self.nbnOSLayerName:
            self.layers.append(rlayer.id())
        QgsMapLayerRegistry.instance().addMapLayer(rlayer)
        if not wmsType == self.WMSType.species:
            self.iface.legendInterface().setLayerExpanded(rlayer, False)
        self.canvas.refresh()
        return rlayer
            
    def checkTransform(self):
        
        try:
            # Not sure why, but this sometimes crashes after another failure in module
            if self.canvasCrs != self.canvas.mapRenderer().destinationCrs():
                self.canvasCrs = self.canvas.mapRenderer().destinationCrs()
                self.transformCrs = QgsCoordinateTransform(self.canvasCrs, self.osgbCrs)
        except:
            pass
        
    def mapExtentsChanged(self):
   
        rectExtent = self.canvas.extent()
        self.checkTransform()
        if self.canvasCrs != self.osgbCrs:
            mapWidth = self.transformCrs.transformBoundingBox(rectExtent).width()
        else:
            mapWidth = rectExtent.width()
        
        #self.iface.messageBar().pushMessage("Info", "Map width: " + str(int(mapWidth)), level=QgsMessageBar.INFO)
        
        for layerID in self.layers:
            rlayer = None
            try:
                rlayer = QgsMapLayerRegistry.instance().mapLayer(layerID)
            except:
                pass
                
            if not rlayer is None:
           
                if rlayer.name().endswith("auto") or rlayer.name().endswith("(auto)"):
                
                    #for strSub in rlayer.subLayers():
                    #    self.iface.messageBar().pushMessage("Info", strSub, level=QgsMessageBar.INFO)
                        
                    if mapWidth < 15000:
                        #self.iface.messageBar().pushMessage("Info", "Grid-100m", level=QgsMessageBar.INFO)
                        if rlayer.name().endswith("auto"):
                            rlayer.setSubLayerVisibility("Grid-10km", False)
                            rlayer.setSubLayerVisibility("Grid-2km", False)
                            rlayer.setSubLayerVisibility("Grid-1km", False)
                            rlayer.setSubLayerVisibility("Grid-100m", True)
                        elif " 100 m " in rlayer.name():
                            self.iface.legendInterface().setLayerVisible(rlayer, True)
                        else:
                            self.iface.legendInterface().setLayerVisible(rlayer, False)
                            
                    elif mapWidth < 100000:
                        #self.iface.messageBar().pushMessage("Info", "Grid-1km", level=QgsMessageBar.INFO)
                        if rlayer.name().endswith("auto"):
                            rlayer.setSubLayerVisibility("Grid-10km", False)
                            rlayer.setSubLayerVisibility("Grid-2km", False)
                            rlayer.setSubLayerVisibility("Grid-1km", True)
                            rlayer.setSubLayerVisibility("Grid-100m", False)
                        elif " monad " in rlayer.name():
                            self.iface.legendInterface().setLayerVisible(rlayer, True)
                        else:
                            self.iface.legendInterface().setLayerVisible(rlayer, False)
                            
                    elif mapWidth < 250000:
                        #self.iface.messageBar().pushMessage("Info", "Grid-2km", level=QgsMessageBar.INFO)
                        if rlayer.name().endswith("auto"):
                            rlayer.setSubLayerVisibility("Grid-10km", False)
                            rlayer.setSubLayerVisibility("Grid-2km", True)
                            rlayer.setSubLayerVisibility("Grid-1km", False)
                            rlayer.setSubLayerVisibility("Grid-100m", False)
                        elif " tetrad " in rlayer.name():
                            self.iface.legendInterface().setLayerVisible(rlayer, True)
                        else:
                            self.iface.legendInterface().setLayerVisible(rlayer, False)
                            
                    else:
                        #self.iface.messageBar().pushMessage("Info", "Grid-10km", level=QgsMessageBar.INFO)
                        if rlayer.name().endswith("auto"):
                            rlayer.setSubLayerVisibility("Grid-10km", True)
                            rlayer.setSubLayerVisibility("Grid-2km", False)
                            rlayer.setSubLayerVisibility("Grid-1km", False)
                            rlayer.setSubLayerVisibility("Grid-100m", False)
                        elif " hectad " in rlayer.name():
                            self.iface.legendInterface().setLayerVisible(rlayer, True)
                        else:
                            self.iface.legendInterface().setLayerVisible(rlayer, False)    
            
    def nameFromTVK(self, tvk):
       
        #Get the preferred taxon name for the TVK
        url = 'https://data.nbn.org.uk/api/taxa/' + tvk
        res = self.restRequest(url)

        if res is None:
            return

        responseText = res.data().decode('utf-8')
        jsonData = json.loads(responseText) 
        return (jsonData["name"])
        
    def removeMap(self):
        if len(self.layers) > 0:
            layerID = self.layers[-1]
            try:
                QgsMapLayerRegistry.instance().removeMapLayer(layerID)
            except:
                pass
            self.layers = self.layers[:-1]
            
    def removeBuffer(self):
        if len(self.buffers) > 0:
            layerID = self.buffers[-1]
            try:
                QgsMapLayerRegistry.instance().removeMapLayer(layerID)
            except:
                pass
            self.buffers = self.buffers[:-1]
            
    def removeMaps(self):
        for layerID in self.layers:
            try:
                QgsMapLayerRegistry.instance().removeMapLayer(layerID)
            except:
                pass
        self.layers = [] 
        
    def loginNBN(self):
        
        if not self.nbnAthenticationCookie is None:
            self.infoMessage("You are already logged in to the NBN as '" + self.currentNBNUser + "'")
            return

        username = self.leUsername.text()
        password = self.lePassword.text()
        postData = QByteArray()
        postData.append('username=' + username + '&')
        postData.append('password=' + password)

        url = 'https://data.nbn.org.uk/api/user/login'
        self.restRequest(url, postData, callType="login")

        return
      
    def logoutNBN(self):
        
        if self.nbnAthenticationCookie is None:
            self.infoMessage("Can't logout because you are not logged in to the NBN")
            return

        url = 'https://data.nbn.org.uk/api/user/logout'
        self.restRequest(url, callType="logout")

        return
       
    def downloadAsyncTest(self, reply):

        error = reply.error()
        if error != QNetworkReply.NoError:
            QgsMessageLog.logMessage("error generated", "NBN Tool Rest call")
            self.iface.messageBar().pushMessage("Error", "NBN Rest service error. Error: %d %s" % (error, reply.errorString()), level=QgsMessageBar.WARNING)
            return None

        # Set the result object
        result = reply.readAll()
        QgsMessageLog.logMessage(str(result), "NBN Tool Rest call")

        reply.deleteLater()
        return

    def downloadNBNObservationsTest(self):

        endpoint = QUrl('https://data.nbn.org.uk/api/taxonObservations/NBNSYS0000008676')
        request = QNetworkRequest(endpoint)

        #QgsMessageLog.logMessage(str(endpoint), "NBN Tool Rest call")

        cj = QNetworkCookieJar()
        cj.setAllCookies([self.nbnAthenticationCookie])
        QgsNetworkAccessManager.instance().setCookieJar(cj)

        #if callType == "download":
        #    QgsNetworkAccessManager.instance().finished.connect(self.downLoadFinished)

        reply = QgsNetworkAccessManager.instance().get(request)

        #reply.finished.connect(self.downloadAsyncTest(reply))
        reply.finished.connect(lambda arg=reply: self.downloadAsyncTest(arg))
        return

        # Wait
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        loop.exec_()
        reply.finished.disconnect(loop.quit)
        loop = None

        error = reply.error()
        if error != QNetworkReply.NoError:
            QgsMessageLog.logMessage("error generated", "NBN Tool Rest call")
            self.iface.messageBar().pushMessage("Error", "NBN Rest service error. Error: %d %s" % (error, reply.errorString()), level=QgsMessageBar.WARNING)
            return None

        # Set the result object
        result = reply.readAll()
        QgsMessageLog.logMessage(str(result), "NBN Tool Rest call")

        reply.deleteLater()

    def downloadNBNObservations(self):
        """
        The filters applicable to this resource are as follows;

          *  Year Filters
               *  startYear (...&startYear=2000&...)
               *  endYear (...&endYear=2012&...)
          *  Taxonomic Filters
               *  ptvk (....&ptvk=[NHMSYS0020706144, NBNSYS0000176784,....]&....)
               *  designation (...&designation=BERN-A1&...)
               *  taxonOutputGroup (...&taxonOutputGroup=NHMSYS0000079976&...)
          *  Dataset Filters
               *  datasetKey (...&datasetKey=[GA000466,....]&...)
          *  Spatial Filters
               *  featureID AND spatialRelationship (within / overlaps) (...&featureID=GA0008850&spatialRelationship=within&...)
               *  gridRef (OSGB, OSI, 10km down to 100m sqaures) (...&gridRef=TA2172&...)
               *  polygon (WKT WGS-84 polygon string) (...&polygon=...&...)
          *  Other Filters
               * absence (...&absence=true&...)
               * sensitive (...&sensitive=true&...)
        """
        
        #Initialise filter parameters
        startYear = None
        endYear = None
        ptvk = None
        designation = None
        taxonOutputGroup = None
        datasetKey = None
        gridRef = None
        polygon = None
        absence = None

        # Update filter display
        self.checkFilters()
        
        # Check that user is logged in
        if self.nbnAthenticationCookie is None:
            self.infoMessage("You must be logged in to the NBN to use this service.")
            return   
    
        # Build params dictionary
        params = {}
        
        # startYear
        if self.cbStartYear.checkState() == Qt.Checked:
            startYear = self.sbStartYear.value()
            params["startYear"] = startYear
            
        # endYear
        if self.cbEndYear.checkState() == Qt.Checked:
            endYear = self.sbEndYear.value()
            params["endYear"] = endYear
            
        # Year validity check
        if not startYear is None and not endYear is None:
            if startYear > endYear:
                self.infoMessage("End year, if specified, must come after start year (or be equal to it), if specified.")
                return
        
        # ptvk
        ptvk = self.getSelectedTVK() # Returns None if none selected
        if not ptvk is None:
            params["ptvk"] = ptvk
            
        # designation
        ret = self.getSelectedDesignation()
        if len(ret) > 0:
            designation = ret[1]
            params["designation"] = designation
            
        # taxonOutputGroup
        taxonOutputGroup = self.getSelectedTaxonOutputGroup()
        if not taxonOutputGroup is None:
            params["taxonOutputGroup"] = taxonOutputGroup
            
        # datasetKey
        selectedDatasets = self.getSelectedDatasets()
        
        # It should be possible to select more than one dataset (if another
        # filter is specified, but this does not appear to currently work
        # 17th Dec 2014
        if len(selectedDatasets) > 1:
            self.infoMessage("Currently, only one dataset can  be specified for each download query.")
            return
            
        if len(selectedDatasets) > 0:
            datasetKey = ""
            for key in selectedDatasets.keys():
                if datasetKey <> "":
                    datasetKey = datasetKey + ","
                datasetKey = datasetKey + key
            params["datasetKey"] = datasetKey
            
            #self.infoMessage("datasetKey=" + params["datasetKey"])
            
        # featureID
        featureID = self.getSelectedSite()
        if not featureID is None:
            params["featureID"] = featureID
            params["spatialRelationship"] = "overlaps"
            
        # gridRef
        
        #params["spatialRelationship"] = "within"
        
        if self.leGridRef.text().strip() <> "":
            gridRef = self.leGridRef.text().strip()
            
            ret = self.osgr.checkGR(gridRef)
            
            if ret[0] == 0:
                self.warningMessage(ret[1])
                return
                
            if ret[0] < 100 or ret[0] > 10000 or ret[0] == 5000:
                self.warningMessage("Grid reference, if specified, must be 6 fig, monad, tetrad or hectad.")
                return
                
            params["gridRef"] = gridRef
            
        # polygon
        polygon = self.getSelectedFeatureWKT()
        if not polygon is None:
            #self.infoMessage("WKT: " + polygon)
            params["polygon"] = polygon
            
        # absence
        if self.rbAbsence.isChecked():
            absence = "true"
            params["absence"] = absence
                     
        # Check that the a valid combination of filters has been specified
        """
        You must supply at least one of the following filters;
          *  A Taxonomic Filter
          *  Spatial Filter
          *  Dataset filter
        """
        bValidFilters = False
        for param in params.keys():
            if param == "ptvk":
                bValidFilters = True
                break
            if param == "datasetKey":
                bValidFilters = True
                break
            if param == "polygon":
                bValidFilters = True
                break
            if param == "featureID":
                bValidFilters = True
                break
            if param == "gridRef":
                bValidFilters = True
                break
                
        if not bValidFilters:
            self.infoMessage("You must specify at least one of the following filters: taxon, dataset, polygon, Site or grid reference.")
            return
            
        #Get a location for the output file.
        self.env.loadEnvironment()
        
        if os.path.exists(self.env.getEnvValue("nbn.downloadfolder")):
            strInitPath = self.env.getEnvValue("nbn.downloadfolder")
        else:
            strInitPath = ""
            
        dlg = QFileDialog
        fileName = dlg.getSaveFileName(self, "Specify output CSV for downloaded records", strInitPath, "CSV Files (*.csv)")
        if not fileName:
            return
            
        # Set current tab to last (download) tab
        self.tabWidget.setCurrentIndex(self.tabWidget.count()-1)
        
        self.runDownload(fileName, params)
        
    def checkFilters(self):

        # Start year
        self.cbIndStartYear.setChecked(self.cbStartYear.isChecked())
        # End year
        self.cbIndEndYear.setChecked(self.cbEndYear.isChecked())
        # Taxon
        self.cbIndTaxon.setChecked(self.getSelectedTVK() is not None)
        # Designation
        self.cbIndDesignation.setChecked(len(self.getSelectedDesignation()) > 0)
        # Taxon group
        self.cbIndGroup.setChecked(self.getSelectedTaxonOutputGroup() is not None)
        # Dataset
        self.cbIndDataset.setChecked(len(self.getSelectedDatasets()) > 0)
            
        # Site
        self.cbIndSite.setChecked(self.getSelectedSite() is not None)
       
        # gridRef
        self.cbIndGridRef.setChecked(self.leGridRef.text().strip() <> "")
          
        # polygon
        self.cbIndPolygon.setChecked(self.getSelectedFeatureWKT() is not None)
        
        # Absence
        self.cbIndAbsence.setChecked(self.rbAbsence.isChecked())
 
    def displayCSV(self):
    
        #Check that single file is selected in list
        if len(self.lwDownloaded.selectedItems()) != 1:
            self.infoMessage("First select a single CSV file from the list")
            return
            
        lwiSelected = self.lwDownloaded.selectedItems()[0]
        csvFile = lwiSelected.toolTip()
        
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
                        if feature.geometry().wkbType() == QGis.WKBPolygon:
                            filterGeom = feature.geometry()
        except:
            filterGeom = None
        
        if filterGeom is not None:
            # If the CRS of the layer is not WGS84, then
            # convert geometry, otherwise use as is.
            if layer.crs() != QgsCoordinateReferenceSystem("EPSG:4326"):
                tcrs = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem("EPSG:4326"))
                filterGeom.transform(tcrs)

            ret = filterGeom.exportToWkt()
            
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

    def runDownload(self, fileName, params):

        # Add file to listbox
        splitName = os.path.split(fileName)
        self.lwDownloaded.addItem(splitName[1])
        lwi = self.lwDownloaded.item(self.lwDownloaded.count()-1)
        lwi.setToolTip(fileName)
        
        lwi.setIcon(QIcon( self.pathPlugin % "images/download.png" ))

        if len(params) == 1 and (params.keys()[0] == "ptvk" or params.keys()[0] == "datasetKey"):      
            # If only a tvk or dataset key passed, we use specific endpoints for them
            endpoint = 'https://data.nbn.org.uk/api/taxonObservations/' + params.values()[0]
            self.restRequest(endpoint, callType="download", downloadInfo={"lwi": lwi, "csv": fileName, "reply": None})
        else:
            # Otherwise we use the general combined filter endpoint
            endpoint = 'https://data.nbn.org.uk/api/taxonObservations/'
            postData = QByteArray()
            for key in params.keys():
                if postData.length() > 0:
                    postData.append('&')
                postData.append(key + '=' + str(params[key]))
            self.restRequest(endpoint, postData, callType="download", downloadInfo={"lwi": lwi, "csv": fileName, "reply": None})

    def downLoadFinished(self, downloadInfo):

        QgsMessageLog.logMessage("Download finished fired", "NBN Tool Rest call")

        lwiDownload = downloadInfo["lwi"]
        fileName = downloadInfo["csv"]
        reply = downloadInfo["reply"]
        
        error = reply.error()
        if error != QNetworkReply.NoError:
            QgsMessageLog.logMessage("error generated", "NBN Tool Rest call")
            self.iface.messageBar().pushMessage("Error", "NBN Rest service error. Error: %d %s" % (error, reply.errorString()), level=QgsMessageBar.WARNING)
            lwiDownload.setIcon(QIcon( self.pathPlugin % "images/cross.png" ))
            return None
        else:
            lwiDownload.setIcon(QIcon( self.pathPlugin % "images/eggtimer.jpg" ))

        # Write the json data to csv
        result = reply.readAll()
        responseText = result.data() #.decode('utf-8')

        #QgsMessageLog.logMessage("Response text", "NBN Tool Rest call")
        #QgsMessageLog.logMessage(responseText, "NBN Tool Rest call")

        try:
            # If csv is to be enriched with dataset names, create datasets dictionary from file
            datasets={}
            if self.cbDatasetNames.isChecked():
                datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "datasets.json"))
                if os.path.isfile(datafile):
                    with open(datafile) as f:
                        jsonDatasets = json.load(f)       
                    for dataset in jsonDatasets:
                        datasets[dataset["key"]] = dataset["title"]

            jsonData = json.loads(responseText)

            with open(fileName, 'wb') as csvfile:
                #csvw = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                csvw = csv.writer(csvfile, dialect='excel')
                headerRow = []
                for jRecord in jsonData:
                    # Have to go through entire file because different records
                    # have different attributes. So to get all names, parse
                    # all records.
                    headerRow = list(set(headerRow + jRecord.keys()))
                    
                if len(datasets) > 0:
                    headerRow.append("datasetName")
                    
                csvw.writerow(headerRow)
                
                for jRecord in jsonData:
                    attrRow = []
                    for header in headerRow:
                        if header in jRecord.keys():
                            attrRow.append(jRecord[header])
                        elif header == "datasetName":
                            try:
                                #If the dataset is missing, the line below will fail
                                attrRow.append(datasets[jRecord["datasetKey"]])
                            except Exception, e:
                                attrRow.append("Dataset not found. Try refreshing Tom.bio NBN dataset filter.")
                        else:
                            attrRow.append("")
                        
                    csvw.writerow([unicode(s).encode("utf-8") for s in attrRow])
                        
            lwiDownload.setIcon(QIcon( self.pathPlugin % "images/tick.jpg" ))
        except Exception, e:
            QgsMessageLog.logMessage("Failed to write output file", "NBN Tool Rest call")
            self.iface.messageBar().pushMessage("Error", "Failed to write output file. Error: %s" % str(e), level=QgsMessageBar.WARNING)
            #self.error.emit("Failed to write output file '" + self.csv + "'. Error: %s" % str(e))
            lwi.setIcon(QIcon( self.pathPlugin % "images/cross.png" ))
            return

    def restRequest(self, url, postData=None, callType="data", downloadInfo=None):
        #This function adapted from __sync_request function in
        #QuickMapServices plugin (extra_sources.py module)
        #Also informed by https://github.com/qgis/QGIS/pull/2299/files
        #and http://nullege.com/codes/search/PyQt4.QtNetwork.QNetworkAccessManager

        endpoint = QUrl(url)
        request = QNetworkRequest(endpoint)

        QgsMessageLog.logMessage(str(endpoint), "NBN Tool Rest call")

        # Set authentication cookie if set and this is either a call to logout or a call to download data
        if (callType == "download" or callType == "logout" ) and not self.nbnAthenticationCookie is None:
            QgsMessageLog.logMessage("setting authentication cookie", "NBN Tool Rest call")
            cj = QNetworkCookieJar()
            cj.setAllCookies([self.nbnAthenticationCookie])
            QgsNetworkAccessManager.instance().setCookieJar(cj)

        if callType == "login":
            QgsMessageLog.logMessage("setting empty cookiejar", "NBN Tool Rest call")
            cj = QNetworkCookieJar()
            QgsNetworkAccessManager.instance().setCookieJar(cj)

        # Set determine if post or get and set accordingly
        if postData is None:
            QgsMessageLog.logMessage("Issue get request", "NBN Tool Rest call")
            reply = QgsNetworkAccessManager.instance().get(request)
        else:
            QgsMessageLog.logMessage("Issue post request", "NBN Tool Rest call")
            reply = QgsNetworkAccessManager.instance().post(request, postData)

        #self.restReplies.append(reply)

        if callType == "download":
            QgsMessageLog.logMessage("Connecting to downloadFinished", "NBN Tool Rest call")
            #reply.finished.connect(self.downLoadFinished(reply, lwiDownload))
            downloadInfo["reply"] = reply
            #reply.finished.connect(lambda arg=downloadInfo: self.downLoadFinished(arg))
            #Don't know under what circumstances, but sometimes get an error at the end of execution...
            #reply.finished.connect(lambda: self.downLoadFinished(downloadInfo))
			#NameError: free variable 'self' referenced before assignment in enclosing scope
            #So this needs trapping
            try:
                reply.finished.connect(lambda: self.downLoadFinished(downloadInfo))

                #reply.finished.connect(self.downLoadFinished(downloadInfo))
                #reply.finished.connect(lambda arg=downloadInfo: self.downLoadFinished(arg))
            except Exception, e:
                QgsMessageLog.logMessage("error generated", "NBN Tool Rest call")
                downloadInfo["lwi"].setIcon(QIcon( self.pathPlugin % "images/cross.png" ))
                self.iface.messageBar().pushMessage("Error", "NBN Rest service error. Error: %s" % str(e), level=QgsMessageBar.WARNING)
            return

        # Wait
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        QgsMessageLog.logMessage("exec loop", "NBN Tool Rest call")
        loop.exec_()
        QgsMessageLog.logMessage("loop ended", "NBN Tool Rest call")
        reply.finished.disconnect(loop.quit)
        loop = None

        error = reply.error()
        if error != QNetworkReply.NoError:
            QgsMessageLog.logMessage("error generated", "NBN Tool Rest call")
            self.iface.messageBar().pushMessage("Error", "NBN Rest service error. Error: %d %s" % (error, reply.errorString()), level=QgsMessageBar.WARNING)
            return None

        # If the return is a re-direction then execute that redirection
        resultCode = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if resultCode in [301, 302, 307]:
            redirectUrl = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
            return self.restRequest(redirectUrl, postData, callType)

        # Set the result object
        result = reply.readAll()
        reply.deleteLater()

        # For login calls, save authentication cookie
        if callType == "login":
            for cookie in cj.allCookies():
                #QgsMessageLog.logMessage(str(cookie.name()), "NBN Tool", QgsMessageLog.INFO)
                #QgsMessageLog.logMessage(str(cookie.value()), "NBN Tool", QgsMessageLog.INFO)
                if cookie.name() == 'nbn.token_key':
                    self.nbnAthenticationCookie = cookie
                    self.currentNBNUser = self.leUsername.text()
                    self.lblLoginStatus.setText ("You are logged in as '" + self.currentNBNUser + "'")
        
        # For logouts
        if callType == "logout":
            self.lblLoginStatus.setText (self.noLoginText)
            self.currentNBNUser = ""
            self.nbnAthenticationCookie = None

        QgsMessageLog.logMessage("returning result", "NBN Tool Rest call")

        return result

