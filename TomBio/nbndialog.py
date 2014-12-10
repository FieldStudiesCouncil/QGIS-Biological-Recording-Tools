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
import urllib
import urllib2
import cookielib
import json 
import hashlib, uuid
import shutil

#import requests

class NBNDialog(QWidget, Ui_nbn):

    def __init__(self, iface, dockwidget):
        QWidget.__init__(self)
        Ui_nbn.__init__(self)
        self.setupUi(self)
        self.canvas = iface.mapCanvas()
        self.iface = iface
    
        self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        
        # WMS
        self.pbSpeciesWMS.clicked.connect(self.WMSFetchSpecies)
        self.pbDatasetWMS.clicked.connect(self.WMSFetchDataset)
        self.pbDesignationWMS.clicked.connect(self.WMSFetchDesignation)
        self.butTaxonSearch.clicked.connect(self.TaxonSearch)
        self.butClearLast.clicked.connect(self.removeMap)
        self.butClear.clicked.connect(self.removeMaps)
        self.pbLogin.clicked.connect(self.loginNBN)
        self.pbLogout.clicked.connect(self.logoutNBN)
        self.butHelp.clicked.connect(self.helpFile)
        self.pbRefreshDatasets.clicked.connect(self.refreshDatasets)
        self.pbRefreshDesignations.clicked.connect(self.refreshDesignations)
        self.pbUncheckAll.clicked.connect(self.uncheckAll)
        self.twDatasets.itemClicked.connect(self.datasetTwClick)
        self.twDesignations.itemClicked.connect(self.designationTwClick)
        self.twTaxa.itemClicked.connect(self.taxaTwClick)
        
        # Map canvas events
        self.canvas.extentsChanged.connect(self.mapExtentsChanged)
        
        # Make a coordinate translator. Also need global references to OSGB and canvas CRSs since
        # they cannot be retrieved from a translator object.
        self.canvasCrs = self.canvas.mapRenderer().destinationCrs()
        self.osgbCrs = QgsCoordinateReferenceSystem("EPSG:27700")
        self.transformCrs = QgsCoordinateTransform(self.canvas.mapRenderer().destinationCrs(), QgsCoordinateReferenceSystem("EPSG:27700"))
        
        # Inits
        self.layers = []
        self.tvks = {} #Initialise tvk dictionary
        self.butClearLast.setIcon(QIcon( self.pathPlugin % "images/removelayer.png" ))
        self.butClear.setIcon(QIcon( self.pathPlugin % "images/removelayers.png" ))
        self.pbSpeciesWMS.setIcon(QIcon( self.pathPlugin % "images/nbn.png" ))
        self.pbDatasetWMS.setIcon(QIcon( self.pathPlugin % "images/nbn.png" ))
        self.pbDesignationWMS.setIcon(QIcon( self.pathPlugin % "images/nbn.png" ))
        self.butTaxonSearch.setIcon(QIcon( self.pathPlugin % "images/speciesinventory.png" ))
        self.butHelp.setIcon(QIcon( self.pathPlugin % "images/bang.png" ))
        self.twTaxa.setHeaderLabel("Matching taxa")
        self.noLoginText = "Not logged in to NBN. Default NBN access will apply."
        self.lblLoginStatus.setText (self.noLoginText)
        self.currentNBNUser = ""
        self.nbnAthenticationCookie = None
        self.guiFile = None
        self.infoFile = os.path.join(os.path.dirname( __file__ ), "infoNBNTool.txt")
        self.readDatasetFile()
        self.readDesignationFile()
        self.datasetSelectionChanged()
        self.designationSelectionChanged()
        #font = self.lblDatasetFilter.font()
        #font.setBold(True)
        #self.lblDatasetFilter.setFont(font)
        
        self.WMSType = self.enum(species=1, dataset=2, designation=3)
        
    def enum(self, **enums):
        return type('Enum', (), enums)
    
    def infoMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Info", strMessage, level=QgsMessageBar.INFO)
        
    def warningMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Warning", strMessage, level=QgsMessageBar.WARNING)
        
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
        
    def datasetTwClick(self, twItem, iCol):
        
        for iDataset in range(twItem.childCount()):
            twiDataset = twItem.child(iDataset)
            twiDataset.setCheckState(0, twItem.checkState(0))
            
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
        
    def designationTwClick(self, twItem, iCol):
        
        #If current item is checked, uncheck all others
        #Only one designation can be checked.
        
        if twItem.checkState(0) == Qt.Checked:
            for iDesignation in range(self.twDesignations.topLevelItemCount()):
                twiDesignation = self.twDesignations.topLevelItem(iDesignation)
                if not twiDesignation == twItem:
                    twiDesignation.setCheckState(0, Qt.Unchecked)
            
        self.designationSelectionChanged()
            
    def datasetSelectionChanged(self):
    
        iChecked = 0
        for iProvider in range(self.twDatasets.topLevelItemCount()):
            twiProvider = self.twDatasets.topLevelItem(iProvider)
            for iDataset in range(twiProvider.childCount()):
                twiDataset = twiProvider.child(iDataset)
                if twiDataset.checkState(0) == Qt.Checked:
                    iChecked += 1
                    
        if iChecked == 0:
            self.lblDatasetFilter.setText("No dataset filter will be applied.")
        else:
            self.lblDatasetFilter.setText("Filter will be applied for " + str(iChecked) + " selected datasets.")
            
    def designationSelectionChanged(self):
    
        iChecked = 0
        for iDesignation in range(self.twDesignations.topLevelItemCount()):
            twiDesignation = self.twDesignations.topLevelItem(iDesignation)
            if twiDesignation.checkState(0) == Qt.Checked:
                iChecked += 1
                    
        if iChecked == 0:
            self.lblDesignationFilter.setText("No designation filter will be applied.")
        else:
            self.lblDesignationFilter.setText("Filter will be applied for " + str(iChecked) + " selected designation.")
    
    def refreshDesignations(self):
        
        self.twDesignations.clear()
        
        try:
            data = urllib2.urlopen('https://data.nbn.org.uk/api/designations').read()
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Error", "HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Error", "Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
            return
        
        jsonData = json.loads(data)

        # Write the json data to a file
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "designations.json"))
        with open(datafile, 'w') as jsonfile:
            jsonfile.write(data)
            
        # Rebuild designation tree
        self.readDesignationFile()
        self.designationSelectionChanged()
    
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
        
        try:
            data = urllib2.urlopen('https://data.nbn.org.uk/api/datasets').read()
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Error", "HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Error", "Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
            return
        
        jsonData = json.loads(data)

        # Write the json data to a file
        datafile = self.pathPlugin % ("NBNCache%s%s" % (os.path.sep, "datasets.json"))
        with open(datafile, 'w') as jsonfile:
            jsonfile.write(data)
            
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
        
        #self.nbnTaxonObservations()
        #return
        
        if self.guiFile is None:
            self.guiFile = FileDialog(self.iface, self.infoFile)
        
        self.guiFile.setVisible(True)
        
    def nbnTaxonObservations(self):
        
        if self.nbnAthenticationCookie is None:
             return
             
        cj = cookielib.CookieJar()
        cj.set_cookie(self.nbnAthenticationCookie)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        params = urllib.urlencode({'datasetKey': 'GA000483', 'ptvk': 'NBNSYS0000008679'})
        try:
            #data = opener.open('https://data.nbn.org.uk/api/taxonObservations', params).read()
            data = opener.open('https://data.nbn.org.uk/api/datasets').read()
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Error", "HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Error", "Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
            return
        
        self.iface.messageBar().pushMessage("Info", "Success", level=QgsMessageBar.INFO)
        
        self.guiFile = FileDialog(self.iface, data)
        self.guiFile.setVisible(True)
        
    def TaxonSearch(self):
    
        if self.leTaxonSearch.text() == "":
            self.iface.messageBar().pushMessage("No search term specified.", level=QgsMessageBar.INFO)
            return
        try:
            #url = 'https://data.nbn.org.uk/api/search/taxa?q=' + self.leTaxonSearch.text()
            url = 'https://data.nbn.org.uk/api/taxa?q=' + self.leTaxonSearch.text()
            url = url.replace(' ','%20')
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Error", "HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Error", "Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
            return
    
        jsonData = json.loads(data)
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
 
    def WMSFetchDesignation(self):
       
        #Selected designation
        iDesignationCount = 0
        for iDesignation in range(self.twDesignations.topLevelItemCount()):
            twiDesignation = self.twDesignations.topLevelItem(iDesignation)
            if twiDesignation.checkState(0) == Qt.Checked:
                iDesignationCount += 1
                selectedDesignationKey = twiDesignation.text(0)
                strName = twiDesignation.text(0)
                            
        #Check item in treeview is selected
        if iDesignationCount == 0:
            self.iface.messageBar().pushMessage("Info", "First select a designation.", level=QgsMessageBar.INFO)
            return
            
        #selectedDesignationKey = "NOTABLE" # For testing
        
        #Get the map from NBN
        url = 'https://gis.nbn.org.uk/DesignationSpeciesDensity/'
        
        #Designation
        url = url + selectedDesignationKey
        
        self.WMSFetch(url, strName, self.WMSType.designation)
        
    def WMSFetchDataset(self):
       
        #Selected dataset
        iDatasetCount = 0
        for iProvider in range(self.twDatasets.topLevelItemCount()):
            twiProvider = self.twDatasets.topLevelItem(iProvider)
            for iDataset in range(twiProvider.childCount()):
                twiDataset = twiProvider.child(iDataset)
                if twiDataset.checkState(0) == Qt.Checked:
                    iDatasetCount += 1
                    selectedDatasetKey = twiDataset.toolTip(0)
                    strName = twiDataset.text(0)
                            
        #Check item in treeview is selected
        if iDatasetCount == 0:
            self.iface.messageBar().pushMessage("Info", "First select a dataset.", level=QgsMessageBar.INFO)
            return
        elif iDatasetCount > 1:
            self.iface.messageBar().pushMessage("Info", "More than one dataset selected. You can only use one for the dataset species density map.", level=QgsMessageBar.INFO)
            return
            
        #selectedDatasetKey = "GA001349" # For testing
        
        #Get the map from NBN
        url = 'https://gis.nbn.org.uk/DatasetSpeciesDensity/'
        
        #Dataset
        url = url + selectedDatasetKey
        
        self.WMSFetch(url, strName, self.WMSType.dataset)
        
    def WMSFetchSpecies(self):
       
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
            self.iface.messageBar().pushMessage("Info", "First check a taxon code (TVK).", level=QgsMessageBar.INFO)
            return
        
        #selectedTVK = "NHMSYS0000530739" # For testing
        
        #Get the map from NBN
        url = 'https://gis.nbn.org.uk/SingleSpecies/'
        
        #Taxon
        url = url + selectedTVK
        
        #Name
        strName = self.nameFromTVK(selectedTVK)
        
        self.WMSFetch(url, strName, self.WMSType.species)

    def WMSFetch(self, url, strName, wmsType):
        
        bURLextended = False
        
        #Set user login stuff
        if not self.leUsername.text() == "":
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
        if self.cbGridSize.currentIndex() == 5:
            strLayers = "&layers=Grid-100m"
            strName = strName + " NBN 100 m"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType)
        elif self.cbGridSize.currentIndex() == 4:
            strLayers = "&layers=Grid-1km"
            strName = strName + " NBN monad"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType)
        elif self.cbGridSize.currentIndex() == 3:
            strLayers = "&layers=Grid-2km"
            strName = strName + " NBN tetrad"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType)
        elif self.cbGridSize.currentIndex() == 2:
            strLayers = "&layers=Grid-10km"
            strName = strName + " NBN hectad"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType)
        elif self.cbGridSize.currentIndex() == 1:
            strLayers = "&layers=Grid-10km&layers=Grid-2km&layers=Grid-1km&layers=Grid-100m"
            strStyles="&styles=&styles=&styles=&styles="
            strName = strName + " NBN auto"
            self.addWMSRaster(url, strLayers, strStyles, strName, wmsType)
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
        
        self.layers.append(rlayer.id())
        QgsMapLayerRegistry.instance().addMapLayer(rlayer)
        if not wmsType == self.WMSType.species:
            self.iface.legendInterface().setLayerExpanded(rlayer, False)
        self.canvas.refresh()
        return rlayer
            
    def checkTransform(self):
        if self.canvasCrs != self.canvas.mapRenderer().destinationCrs():
            self.canvasCrs = self.canvas.mapRenderer().destinationCrs()
            self.transformCrs = QgsCoordinateTransform(self.canvasCrs, self.osgbCrs)
        
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
        try:
            url = 'https://data.nbn.org.uk/api/taxa/' + tvk
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Error", "HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return ('')
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Error", "Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
            return ('')
    
        jsonData = json.loads(data)
        return (jsonData["name"])
        
    def removeMap(self):
        if len(self.layers) > 0:
            layerID = self.layers[-1]
            try:
                QgsMapLayerRegistry.instance().removeMapLayer(layerID)
            except:
                pass
            self.layers = self.layers[:-1]
            
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
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        login_data = urllib.urlencode({'username' : username, 'password' : password})
        try:
            opener.open('https://data.nbn.org.uk/api/user/login', login_data)
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Error", "NBN Login failed. HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Error", "NBN Login failed. Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
            return
    
        for cookie in cj:
            if cookie.name == 'nbn.token_key':
                self.nbnAthenticationCookie = cookie
                self.currentNBNUser = self.leUsername.text()
                self.lblLoginStatus.setText ("You are logged in as '" + self.currentNBNUser + "'")
        return
        
        
    def logoutNBN(self):
        
        if self.nbnAthenticationCookie is None:
            self.infoMessage("Can't logout because you are not logged in to the NBN")
            return
            
        cj = cookielib.CookieJar()
        cj.set_cookie(self.nbnAthenticationCookie)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        try:
            opener.open('https://data.nbn.org.uk/api/user/logout')
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Error", "HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Error", "Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
            return
            
        self.lblLoginStatus.setText (self.noLoginText)
        self.currentNBNUser = ""
        self.nbnAthenticationCookie = None
