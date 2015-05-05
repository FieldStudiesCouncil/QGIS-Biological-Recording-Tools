# -*- coding: utf-8 -*-
"""
/***************************************************************************
BiorecDialog
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

from ui_biorec import Ui_Biorec
import os
import csv
import sys
from filedialog import FileDialog
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from bioreclayer2 import *
from envmanager import *


class BiorecDialog(QWidget, Ui_Biorec):
    def __init__(self, iface, dockwidget):
        QWidget.__init__(self)
        Ui_Biorec.__init__(self)
        self.setupUi(self)
        self.canvas = iface.mapCanvas()
        self.iface = iface

        #self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        self.pathPlugin = os.path.dirname( __file__ ) 
        
        self.model = QStandardItemModel(self)
        self.tvRecords.setModel(self.model)
        
        self.butBrowse.clicked.connect(self.browseCSV)
        self.butMap.clicked.connect(self.MapRecords)
        self.butShowAll.clicked.connect(self.showAll)
        self.butHideAll.clicked.connect(self.hideAll)
        self.butGenTree.clicked.connect(self.listTaxa)
        self.butSaveImage.clicked.connect(self.batchImageGenerate)
        self.butRemoveMap.clicked.connect(self.removeMap)
        self.butRemoveMaps.clicked.connect(self.removeMaps)
        self.butExpand.clicked.connect(self.expandAll)
        self.butContract.clicked.connect(self.collapseAll)
        self.butCheckAll.clicked.connect(self.checkAll)
        self.butUncheckAll.clicked.connect(self.uncheckAll)
        self.pbBrowseImageFolder.clicked.connect(self.browseImageFolder)
        self.pbBrowseStyleFile.clicked.connect(self.browseStyleFile)
        self.pbCancel.clicked.connect(self.cancelBatch)
        self.butHelp.clicked.connect(self.helpFile)
        self.cboTaxonCol.currentIndexChanged.connect(self.enableDisableTaxa)
        self.cboGridRefCol.currentIndexChanged.connect(self.enableDisableGridRef)
        self.cboXCol.currentIndexChanged.connect(self.enableDisableXY)
        self.cboYCol.currentIndexChanged.connect(self.enableDisableXY)
        self.pbInputCRS.clicked.connect(self.selectInputCRS)
        self.pbOutputCRS.clicked.connect(self.selectOutputCRS)
        self.cboMapType.currentIndexChanged.connect(self.checkMapType)
        self.cbMatchCRS.stateChanged.connect(self.matchCRSClick)
        
        # Load the environment stuff
        self.env = envManager()
        
        # Globals
        self.propogateDown = True
        self.propogateUp = True
        self.layers = []
        self.stepLayerIndex = -1
        self.folderError = False
        self.imageError = False
        self.cancelBatchMap = False
        self.guiFile = None
        self.infoFile = os.path.join(os.path.dirname( __file__ ), "infoBioRecTool.txt")
        self.csvLayer = None
        
        # Set button graphics
        self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        self.butMap.setIcon(QIcon( self.pathPlugin % "images/maptaxa.png" ))
        self.butRemoveMap.setIcon(QIcon( self.pathPlugin % "images/removelayer.png" ))
        self.butRemoveMaps.setIcon(QIcon( self.pathPlugin % "images/removelayers.png" ))
        self.butHelp.setIcon(QIcon( self.pathPlugin % "images/bang.png" ))
        self.butSaveImage.setIcon(QIcon( self.pathPlugin % "images/saveimage.png" ))
        self.butShowAll.setIcon(QIcon( self.pathPlugin % "images/layershow.png" ))
        self.butHideAll.setIcon(QIcon( self.pathPlugin % "images/layerhide.png" ))
        
        # Defaults
        self.leImageFolder.setText(self.env.getEnvValue("biorec.atlasimagefolder"))
        
        if self.testImageCreation():
            #self.iface.messageBar().pushMessage("Info", "2.4 or above", level=QgsMessageBar.INFO)
            self.qgisVersion = ">2"
        else:
            #self.iface.messageBar().pushMessage("Info", "2.0", level=QgsMessageBar.INFO)
            self.qgisVersion = "2"

        #Inits
        self.blockGR = False
        self.blockXY = False
        self.dsbGridSize.setEnabled(False)
        self.lblInputCRS.setText("")
        self.lblOutputCRS.setText("")
        self.lastWaitMessage = None
        self.cbMatchCRS.setChecked(True)
    
    def infoMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Info", strMessage, level=QgsMessageBar.INFO)
        
    def warningMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Warning", strMessage, level=QgsMessageBar.WARNING)
        
    def waitMessage(self, str1="", str2=""):
       
        if str1 <> "":
            widget = iface.messageBar().createMessage(str1, str2)
            self.lastWaitMessage = iface.messageBar().pushWidget(widget, QgsMessageBar.WARNING)
            qApp.processEvents() 
        else:
            iface.messageBar().popWidget(self.lastWaitMessage)
        
    def testImageCreation(self):
        
        try:
            imgPath = self.pathPlugin % "/test"
            pixmap = QPixmap(self.canvas.mapSettings().outputSize().width(), 
                self.canvas.mapSettings().outputSize().height())
            self.canvas.saveAsImage(imgPath + ".png", pixmap)
           
            os.remove(imgPath + ".png")
            os.remove(imgPath + ".pngw")
            return True
        except:
            return False
 
    def helpFile(self):
        if self.guiFile is None:
            self.guiFile = FileDialog(self.iface, self.infoFile)
        
        self.guiFile.setVisible(True)    
        
    def checkMapType(self):
    
        if self.cboMapType.currentText().startswith("User-defined"):
            if self.cboGridRefCol.currentIndex() > 0:
                self.infoMessage("Can't set a user-defined grid size when using OS grid references as input")
                self.cboMapType.setCurrentIndex(0)
            else:
                self.dsbGridSize.setEnabled(True)
        else:
            self.dsbGridSize.setValue(0)
            self.dsbGridSize.setEnabled(False)
            
        if not self.cboMapType.currentText().startswith("User-defined") and not self.cboMapType.currentText() == "Records as points":
        
            if self.lblInputCRS.text() != "EPSG:27700":
                self.infoMessage("Only points or user-defined grid for input data that are not OSGB (EPSG:27700)")
                self.cboMapType.setCurrentIndex(0)
            
        if self.cboMapType.currentText() == "Records as grid squares" and self.cboGridRefCol.currentIndex() == 0:
            
            self.infoMessage("'Records as grid squares' only available for input as OS grid references")
            self.cboMapType.setCurrentIndex(0)
            
    def enableDisableGridRef(self):
    
        self.blockGR = True
        
        if self.cboGridRefCol.currentIndex() > 0 and not self.blockXY:
            self.cboXCol.setCurrentIndex(0)
            self.cboYCol.setCurrentIndex(0)
            
        if self.cboGridRefCol.currentIndex() > 0:
            self.pbInputCRS.setEnabled(False)
            self.lblInputCRS.setText("EPSG:27700")
            self.pbOutputCRS.setEnabled(False)
            self.lblOutputCRS.setText("EPSG:27700")
            
            if self.cboMapType.currentText().startswith("User-defined"):
                self.cboMapType.setCurrentIndex(0)
        else:
            self.pbInputCRS.setEnabled(True)
            self.pbOutputCRS.setEnabled(not self.cbMatchCRS.isChecked())
     
        self.checkMapType()
        
        self.blockGR = False
        
    def enableDisableXY(self):
    
        self.blockXY = True
        
        if (self.cboXCol.currentIndex() > 0 or self.cboYCol.currentIndex() > 0) and not self.blockGR:
            self.cboGridRefCol.setCurrentIndex(0)
            
        self.checkMapType()
        
        self.blockXY = False

    def matchCRSClick(self):
       
        if self.cboGridRefCol.currentIndex() > 0:
            self.pbOutputCRS.setEnabled(False)
        else:
            self.pbOutputCRS.setEnabled(not self.cbMatchCRS.isChecked())
            
        if self.cbMatchCRS.isChecked():
            self.lblOutputCRS.setText(self.lblInputCRS.text())
            
    def enableDisableTaxa(self):
    
        if self.cboTaxonCol.currentIndex() == 0:
            self.cboGroupingCol.setCurrentIndex(0)
            self.cboGroupingCol.setEnabled(False)
            self.cbIsScientific.setChecked(False)
            self.cbIsScientific.setEnabled(False)
            self.lblGroupingCol.setEnabled(False)
        else:
            self.cboGroupingCol.setEnabled(True)
            self.cbIsScientific.setEnabled(True)
            self.lblGroupingCol.setEnabled(True)
            
    def selectInputCRS(self):
    
        crs = self.selectCRS()
        if not crs == None:
            self.lblInputCRS.setText(crs)
            
            if self.cbMatchCRS.isChecked():
                self.lblOutputCRS.setText(crs)
            
        self.checkMapType()
            
    def selectOutputCRS(self):
    
        crs = self.selectCRS()
        if not crs == None:
            self.lblOutputCRS.setText(crs)
            
    def selectCRS(self):
    
        crsSelector = QgsGenericProjectionSelector()
        crsSelector.exec_()
        if crsSelector.selectedCrsId() == 0:
            return None
        else:
            return str(crsSelector.selectedAuthId())
            
    def browseImageFolder(self):
    
        #Reload env
        self.env.loadEnvironment()
        
        dlg = QFileDialog
        
        if os.path.exists(self.leImageFolder.text()):
            strInitPath = self.leImageFolder.text()
        else:
            strInitPath = ""
            
        folderName = dlg.getExistingDirectory(self, "Browse for image folder", self.leImageFolder.text())
        if folderName:
            self.leImageFolder.setText(folderName)
            self.leImageFolder.setToolTip(folderName)
            
    def browseStyleFile(self):
    
        #Reload env
        self.env.loadEnvironment()
        
        if os.path.exists(self.env.getEnvValue("biorec.stylefilefolder")):
            strInitPath = self.env.getEnvValue("biorec.stylefilefolder")
        else:
            strInitPath = ""
            
        dlg = QFileDialog
        fileName = dlg.getOpenFileName(self, "Browse for style file", strInitPath, "QML Style Files (*.qml)")
        if fileName:
            self.leStyleFile.setText(fileName)
            self.leStyleFile.setToolTip(fileName)
            
    def browseCSV(self):
    
        self.setCSV(None)
        
    def setCSV(self, nbnFile):
        
        #Reload env
        self.env.loadEnvironment()
        
        if os.path.exists(self.env.getEnvValue("biorec.csvfolder")):
            strInitPath = self.env.getEnvValue("biorec.csvfolder")
        else:
            strInitPath = ""
            
        if nbnFile is None:
            dlg = QFileDialog
            fileName = dlg.getOpenFileName(self, "Browse for biological record file", strInitPath, "Record Files (*.csv)")
        else:
            fileName = nbnFile
            
        #self.infoMessage("File: " + fileName)

        if fileName:
                 
            #Initialise the tree model
            self.initTreeView()
        
            # Clear all current values
            self.model.clear()
            self.cboGridRefCol.clear()
            self.cboXCol.clear()
            self.cboYCol.clear()
            self.cboTaxonCol.clear()
            self.cboGroupingCol.clear()
            self.cboAbundanceCol.clear()
            
            # Load the CSV and set controls
            self.leFilename.setText(os.path.basename(fileName))
            self.leFilename.setToolTip(fileName)
            self.loadCsv(fileName, (not nbnFile is None))
            
            #self.iface.messageBar().pushMessage("Info", "csv loaded.", level=QgsMessageBar.INFO)
            
    def initTreeView(self):
    
        #Initialise the tree model
        modelTree = QStandardItemModel()
        modelTree.itemChanged.connect(self.tvBoxChecked)
        self.tvTaxa.setModel(modelTree)
        self.modelTree = modelTree
            
    def listTaxa(self, suppressMessage=False):
       
        #Init the tree view
        self.initTreeView()
        
        if self.cboTaxonCol.currentIndex() == 0:
            if not suppressMessage:
                self.infoMessage("No taxon column selected")
            return
            
        iColGrouping = self.cboGroupingCol.currentIndex() - 1
        iColTaxon = self.cboTaxonCol.currentIndex() - 1
        bScientific = self.cbIsScientific.isChecked()
        
        if iColTaxon == -1:
            return
            
        self.waitMessage("Building taxon tree", "can take a minute or so for very large files...")
        
        tree = {}
        iter = self.csvLayer.getFeatures()
        for feature in iter:
        
            if iColGrouping > -1:

                try:
                    group = str(feature.attributes()[iColGrouping])
                except:
                    group = "invalid"
                    
                #self.pteLog.appendPlainText("add candidate " + group)
                if group not in tree.keys():
                    tree[group] = {}
                
                try:
                    parent = tree[group]
                except:
                    self.pteLog.appendPlainText("Grouping error " + str(group))
            else:
                parent = tree
            
            try:
                taxon = str(feature.attributes()[iColTaxon])
            except:
                taxon = "invalid"
                
            if bScientific:
                splitTaxon = taxon.split(" ")
                genus = splitTaxon[0]
            
                if genus not in parent.keys():
                    parent[genus] = {}
                parent = parent[genus]
                
            if taxon not in parent.keys():
                parent[taxon] = {}
        
        # Build tree from nested lists (which are sorted on the fly)
        for l1 in sorted(tree.iterkeys()):
            itemL1 = QStandardItem(l1)
            itemL1.setCheckable(True)
            self.modelTree.appendRow(itemL1)
            
            dictL2 = tree[l1]
            for l2 in sorted(dictL2.iterkeys()):
                itemL2 = QStandardItem(l2)
                itemL2.setCheckable(True)
                itemL1.appendRow(itemL2)
                
                dictL3 = dictL2[l2]
                for l3 in sorted(dictL3.iterkeys()):
                    itemL3 = QStandardItem(l3)
                    itemL3.setCheckable(True)
                    itemL2.appendRow(itemL3)
                    
        self.tvTaxa.header().close()
        
        self.waitMessage()
        
    def tvBoxChecked(self, item):
        self.propogateUp = False
        self.setChildrenItems(item, item.checkState())
        self.propogateUp = True
        if item.checkState() == False:
            self.propogateDown = False
            self.uncheckParents(item)
            self.propogateDown = True
            
    def uncheckParents(self, item):
        if not self.propogateUp:
            return
        if item.parent() is None:
            return
        item.parent().setCheckState(False)
        self.uncheckParents(item.parent())

    def setChildrenItems(self, item, checked):
        if not self.propogateDown:
            return 
        for i in range (item.rowCount()):
            #self.pteLog.appendPlainText("Will click " + item.child(i,0).text())
            item.child(i,0).setCheckState(checked)
            self.setChildrenItems(item.child(i,0), checked)
            
    def expandAll(self):
        self.tvTaxa.expandAll()
        
    def collapseAll(self):
        self.tvTaxa.collapseAll()
        
    def checkAll(self):
        if self.tvTaxa.model() is None:
            return
        for i in range(self.tvTaxa.model().rowCount()):
            self.tvTaxa.model().item(i,0).setCheckState(Qt.Checked)
            self.setChildrenItems(self.tvTaxa.model().item(i,0), Qt.Checked)
            
    def uncheckAll(self):
        if self.tvTaxa.model() is None:
            return
        for i in range(self.tvTaxa.model().rowCount()):
            self.tvTaxa.model().item(i,0).setCheckState(Qt.Unchecked)
            self.setChildrenItems(self.tvTaxa.model().item(i,0), Qt.Unchecked)
              
    def addItemToFieldLists(self, item):
        self.cboGridRefCol.addItem(item)
        self.cboXCol.addItem(item)
        self.cboYCol.addItem(item)
        self.cboTaxonCol.addItem(item)
        self.cboGroupingCol.addItem(item)
        self.cboAbundanceCol.addItem(item)
        
    def loadCsv(self, fileName, isNBNCSV):
    
        #Reload the environment
        self.env.loadEnvironment()
        
        #Load as a CSV
        uri = "file:///" + fileName + "?delimiter=%s" % (",")
        
        self.waitMessage("Loading", fileName)
        try:
            self.csvLayer = QgsVectorLayer(uri, "biorecCSV", "delimitedtext")
        except:
            self.csvLayer = None
        self.waitMessage()
        
        if self.csvLayer == None:
            self.warningMessage("Couldn't open CSV file: '%s'" % (fileName))
        else:
            #Add the fields to the relevant drop-down lists
            self.addItemToFieldLists("")
            for field in self.csvLayer.dataProvider().fields():
                self.addItemToFieldLists(field.name())
            
            # Set default value for GridRef column
            if isNBNCSV:
                index = 1
                for field in self.csvLayer.dataProvider().fields():
                    if field.name() == "location":
                        self.cboGridRefCol.setCurrentIndex(index)
                        break
                    index += 1
            else:
                for colGridRef in self.env.getEnvValues("biorec.gridrefcol"):
                    index = 1
                    for field in self.csvLayer.dataProvider().fields():
                        if field.name() == colGridRef:
                            self.cboGridRefCol.setCurrentIndex(index)
                            break
                        index += 1
                    
            # Set default value for X column
            for colX in self.env.getEnvValues("biorec.xcol"):
                index = 1
                for field in self.csvLayer.dataProvider().fields():
                    if field.name() == colX:
                        self.cboXCol.setCurrentIndex(index)
                        break
                    index += 1
                    
            # Set default value for Y column
            for colY in self.env.getEnvValues("biorec.ycol"):
                index = 1
                for field in self.csvLayer.dataProvider().fields():
                    if field.name() == colY:
                        self.cboYCol.setCurrentIndex(index)
                        break
                    index += 1
                    
            # Set default value for Taxon column
            if isNBNCSV:
                index = 1
                for field in self.csvLayer.dataProvider().fields():
                    if field.name() == "pTaxonName":
                        self.cboTaxonCol.setCurrentIndex(index)
                        break
                    index += 1
            else:
                for colTaxon in self.env.getEnvValues("biorec.taxoncol"):
                    index = 1
                    for field in self.csvLayer.dataProvider().fields():
                        if field.name() == colTaxon:
                            self.cboTaxonCol.setCurrentIndex(index)
                            break
                        index += 1
                    
            # Set default value for Grouping column
            for colGrouping in self.env.getEnvValues("biorec.groupingcol"):
                index = 1
                for field in self.csvLayer.dataProvider().fields():
                    if field.name() == colGrouping:
                        self.cboGroupingCol.setCurrentIndex(index)
                        break
                    index += 1
                    
            # Set default value for Abundance column
            for colAbundance in self.env.getEnvValues("biorec.abundancecol"):
                index = 1
                for field in self.csvLayer.dataProvider().fields():
                    if field.name() == colAbundance:
                        self.cboAbundanceCol.setCurrentIndex(index)
                        break
                    index += 1
            
            # Set scientific names checkbox if set in environment
            if self.env.getEnvValue("biorec.scientificnames") == "True":
                self.cbIsScientific.setChecked(True)
            else:
                self.cbIsScientific.setChecked(False)      
                
            # Make first few records available for user to inspect
            fields = []
            for field in self.csvLayer.dataProvider().fields():
                fields.append(field.name())
            self.model.setHorizontalHeaderLabels(fields)
           
            rowCount = 0
            iter = self.csvLayer.getFeatures()
            for feature in iter:
                rowCount += 1
                
                if rowCount > 10:
                    #Only output the first ten rows
                    break
                else:
                    #Output a row
                    items = []
                    for field in feature.attributes():
                        try:
                            items.append(QStandardItem(str(field)))
                        except:
                            items.append(QStandardItem(""))
                    """
                    items = [
                        QStandardItem(str(field))
                        for field in feature.attributes()
                    ]
                    """
                    self.model.appendRow(items)
            
        self.enableDisableTaxa()
        self.enableDisableGridRef()
        self.enableDisableXY()
        
        #If the maketree environment variable is set, then
        #automatically create tree
        if self.env.getEnvValue("biorec.maketree") == "True":
            self.listTaxa(True) 
        
    def MapRecords(self):
              
        self.progBatch.setValue(0)
        
        # Return if no grid reference or X & Y fields selected
        if self.cboGridRefCol.currentIndex() == 0 and (self.cboXCol.currentIndex() == 0 or self.cboYCol.currentIndex() == 0):
            self.iface.messageBar().pushMessage("Info", "You must select either an OS grid ref column or both X and Y columns", level=QgsMessageBar.INFO)
            return
            
        # Return if Grid ref selected with user-defined grid
        if self.cboGridRefCol.currentIndex() > 0 and self.cboMapType.currentText().startswith("User-defined"):
            self.iface.messageBar().pushMessage("Info", "You cannot specify a user-defined grid with input of OS grid references", level=QgsMessageBar.INFO)
            return
            
        # Return if X & Y selected but no input CRS
        if self.cboXCol.currentIndex() > 0 and self.lblInputCRS.text() == "":
            self.iface.messageBar().pushMessage("Info", "You must specify an input CRS if specifying X and Y columns", level=QgsMessageBar.INFO)
            return
            
        # Return if X & Y selected but no output CRS
        if self.cboXCol.currentIndex() > 0 and self.lblOutputCRS.text() == "":
            self.iface.messageBar().pushMessage("Info", "You must specify an output CRS if specifying X and Y columns", level=QgsMessageBar.INFO)
            return
            
        # Return if user-defined atlas selected, but no grid size
        if self.cboMapType.currentText().startswith("User-defined") and self.dsbGridSize.value() == 0:
            self.iface.messageBar().pushMessage("Info", "You must specify a grid size if specifying a user-defined atlas", level=QgsMessageBar.INFO)
            return
        
        # Return X & Y input selected, but not records as points or user-defined grid selected
        if self.cboXCol.currentIndex() > 0 and self.lblInputCRS.text() != "EPSG:27700":
            if not self.cboMapType.currentText().startswith("User-defined") and not self.cboMapType.currentText()== ("Records as points"):
                self.iface.messageBar().pushMessage("Info", "For CRS other than OSGB, you must create records as points or a user-defined atlas",level=QgsMessageBar.INFO)
                return
        
        # Make a list of all the selected taxa
        selectedTaxa = []
      
        if not self.tvTaxa.model() is None:
            for i in range(self.tvTaxa.model().rowCount()):
                selectedTaxa.extend(self.getCheckedTaxa(self.tvTaxa.model().item(i,0)))
            
        if len(selectedTaxa) == 0 and self.cboTaxonCol.currentIndex() > 0:
            self.iface.messageBar().pushMessage("Info", "No taxa selected.", level=QgsMessageBar.INFO)
            return
            
        if self.cboBatchMode.currentIndex() == 0 or self.cboTaxonCol.currentIndex() == 0:
            self.createMapLayer(selectedTaxa)
        else:
            self.progBatch.setMaximum(len(selectedTaxa))
            i = 0
            self.folderError = False
            self.imageError = False
            for taxa in selectedTaxa:
                if not self.cancelBatchMap:
                    i=i+1
                    self.progBatch.setValue(i)
                    self.createMapLayer([taxa])
                    #This is needed to allow interruptions. Now safe to use
                    #because layers not actually added to map until after all created.
                    qApp.processEvents() 
                   
            self.progBatch.setValue(0)
            self.cancelBatchMap = False
            
        # Add all layers to the map in a single step
        layerIDs = []
        for layer in self.layers:
            layerIDs.append(layer.getVectorLayer())

        try:
            QgsMapLayerRegistry.instance().addMapLayers(layerIDs)
        except Exception, e:
            #self.iface.messageBar().pushMessage("Error", "Error adding layers to map: %s" % e, level=QgsMessageBar.CRITICAL)
            self.iface.messageBar().pushMessage("Error", "Problem adding layers. Clear bio.rec layers with 'remove all map layers' button and try again.", level=QgsMessageBar.CRITICAL)
            
        # Make sure none of the layers expanded
        for layer in self.layers:
            layer.setExpanded(False)
    
    def batchImageGenerate(self):
          
        if len(self.layers) == 0:
            return
            
        self.progBatch.setValue(0)
        self.progBatch.setMaximum(len(self.layers))
        
        """
        if self.hideAll():
            i=0
            for layer in self.layers:
                if not self.cancelBatchMap:
                    i=i+1
                    self.progBatch.setValue(i)
                    layer.setVisibility(True)
                    self.createComposerImage(layer)
                    layer.setVisibility(False)
                
        self.progBatch.setValue(0)
        self.cancelBatchMap = False          
        return
        """
        
        if self.qgisVersion == ">2":
            # Version 2.4 and above
            layerIDs = []
            for layer in self.layers:
                layerIDs.append(layer.getID())
                
            displayedLayerIDs = self.canvas.mapSettings().layers()
            backdropLayerIDs = [item for item in displayedLayerIDs if item not in layerIDs]
            settings = self.canvas.mapSettings()
            i=0
            for layer in self.layers:
                if not self.cancelBatchMap:
                    i=i+1
                    self.progBatch.setValue(i)
                    layersRender = [layer.getID()] + backdropLayerIDs
                    settings.setLayers(layersRender)
                    job = QgsMapRendererParallelJob(settings)
                    job.start()
                    job.waitForFinished()
                    image = job.renderedImage()
                    self.saveMapImage(image, layer.getName())
                    qApp.processEvents()

        else:
            # Version 2.0
            # Make all the layers invisible
            # In turn set each layer to visible
            # generate image, and then make invisible again
            if self.hideAll():
                i=0
                for layer in self.layers:
                    if not self.cancelBatchMap:
                        i=i+1
                        self.progBatch.setValue(i)
                        layer.setVisibility(True)
                        self.createMapImage(layer)
                        layer.setVisibility(False)
                        #qApp.processEvents()
        
        self.progBatch.setValue(0)
        self.cancelBatchMap = False
        
    def showAll(self):
        return self.allShowHide(True)
        
    def hideAll(self):
        return self.allShowHide(False)
        
    def allShowHide(self, bShow):
          
        if len(self.layers) == 0:
            return
            
        self.canvas.setRenderFlag(False)
        
        self.progBatch.setValue(0)
        self.progBatch.setMaximum(len(self.layers))
        
        i=0
        for layer in self.layers:
            if not self.cancelBatchMap:
                i=i+1
                self.progBatch.setValue(i)
                layer.setVisibility(bShow)
                qApp.processEvents()
        
        self.progBatch.setValue(0)
        retValue = (not self.cancelBatchMap)
        self.cancelBatchMap = False
        self.canvas.setRenderFlag(True)
        
        return retValue
        
    def removeMap(self):
        if len(self.layers) > 0:
            layer = self.layers[-1]
            layer.removeFromMap()
            layer = None
            self.layers = self.layers[:-1]
            
    def removeMaps(self):
        if len(self.layers) == 0:
            return
            
        self.progBatch.setValue(0)
        self.progBatch.setMaximum(len(self.layers))
        
        i=0
        layerIDs = []
        for layer in self.layers:
            i=i+1
            self.progBatch.setValue(i)
            layerIDs.append(layer.getID())
            layer = None
            
        self.layers = []
        QgsMapLayerRegistry.instance().removeMapLayers(layerIDs)
        self.progBatch.setValue(0)
        
    #def removeAllLayers(self):
    #    QgsMapLayerRegistry.instance().removeAllMapLayers()
        
    def cancelBatch(self):
        self.cancelBatchMap = True
       
    def createMapLayer(self, selectedTaxa):
        
        # Initialsie the map layer
        layer = biorecLayer2(self.iface, self.csvLayer, self.pteLog) 
        layer.setTaxa(selectedTaxa)
        layer.setColTaxa(self.cboTaxonCol.currentIndex() - 1)
        layer.setColAb(self.cboAbundanceCol.currentIndex() - 1)
        layer.setColGr(self.cboGridRefCol.currentIndex() - 1)
        layer.setColX(self.cboXCol.currentIndex() - 1)
        layer.setColY(self.cboYCol.currentIndex() - 1)
        layer.setTransparency(self.hsLayerTransparency.value())
        layer.setCrs(self.lblInputCRS.text(), self.lblOutputCRS.text())
        layer.setGridSize(self.dsbGridSize.value())
        
        # Name the layer
        if len(selectedTaxa) == 1:
            layerName = selectedTaxa[0]
        else:
            layerName = self.leFilename.text()[:-4]
            
        mapType = self.cboMapType.currentText()
        if '(' in mapType:
            layerName = layerName + " " + mapType[:mapType.index('(')-1 ]
   
        layer.setName(layerName)
        
        # Create the map layer
        styleFile = None
        if self.cbApplyStyle.isChecked():
 
            if self.cboMapType.currentIndex() == 0:
                self.iface.messageBar().pushMessage("Warning", "Applied style file to points layer. Points will not be visible if no style for points defined.", level=QgsMessageBar.WARNING)
                
            if os.path.exists( self.leStyleFile.text()):
                styleFile = self.leStyleFile.text()
                
        self.waitMessage("Making map layer", layerName)
        layer.createMapLayer(self.cboMapType.currentText(), self.cboSymbol.currentText(), styleFile)  
        self.waitMessage()
        
        self.layers.append(layer)
        
    def saveMapImage(self, image, name):
        
        imgFolder = self.leImageFolder.text()
        
        if not os.path.exists(imgFolder):
            if not self.folderError:
                self.iface.messageBar().pushMessage("Error", "Image folder '%s' does not exist." % imgFolder, level=QgsMessageBar.WARNING)
                self.folderError = True
        else:
            validName = self.makeValidFilename(name)
            try:
                image.save(imgFolder + "\\" + validName + ".png")
            except:
                if not self.imageError:
                    e = sys.exc_info()[0]
                    self.iface.messageBar().pushMessage("Error", "Image generation error: %s" % e, level=QgsMessageBar.WARNING)
                    self.imageError = True
                           
    def createMapImage(self, layer):
    
        imgFolder = self.leImageFolder.text()
        
        if not os.path.exists(imgFolder):
            if not self.folderError:
                self.iface.messageBar().pushMessage("Error", "Image folder '%s' does not exist." % imgFolder, level=QgsMessageBar.WARNING)
                self.folderError = True
        else:
            validName = self.makeValidFilename(layer.getName())
            imgFile = imgFolder + "\\" + validName + ".png"
            
            try:
                self.canvas.saveAsImage(imgFile) 
                # Don't need the registration file, so delete it
                os.remove(imgFolder + "\\" + validName + ".pngw")
            except:
                if not self.imageError:
                    e = sys.exc_info()[0]
                    self.iface.messageBar().pushMessage("Error", "Image generation error: %s" % e, level=QgsMessageBar.WARNING)
                    self.imageError = True
                
    def createComposerImage(self, layer):
    
        imgFolder = self.leImageFolder.text()
        
        if not os.path.exists(imgFolder):
            if not self.folderError:
                self.iface.messageBar().pushMessage("Error", "Image folder '%s' does not exist." % imgFolder, level=QgsMessageBar.WARNING)
                self.folderError = True
        else:
            validName = self.makeValidFilename(layer.getName())
            imgFile = imgFolder + "\\" + validName + ".png"
            
            #try:
            if len(self.iface.activeComposers()) > 0:
            
                c = self.iface.activeComposers()[0].composition()
                #c.refreshItems()
                dpi = c.printResolution()
                dpmm = dpi / 25.4
                width = int(dpmm * c.paperWidth())
                height = int(dpmm * c.paperHeight())

                # create output image and initialize it
                imageC = QImage(QSize(width, height), QImage.Format_ARGB32)
                imageC.setDotsPerMeterX(dpmm * 1000)
                imageC.setDotsPerMeterY(dpmm * 1000)
                imageC.fill(0)

                # render the composition
                imagePainter = QPainter(imageC)
                sourceArea = QRectF(0, 0, c.paperWidth(), c.paperHeight())
                targetArea = QRectF(0, 0, width, height)
                c.render(imagePainter, targetArea, sourceArea)
                imagePainter.end()

                imageC.save(imgFolder + "\\" + validName + "-composer.png")
            """
            except:
                if not self.imageError:
                    e = sys.exc_info()[0]
                    self.iface.messageBar().pushMessage("Error", "Composer image generation error: %s" % e, level=QgsMessageBar.WARNING)
                    self.imageError = True
            """
            
    def makeValidFilename(self, filename):
        newFilename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        return newFilename
        
    def getCheckedTaxa(self, item):
        selectedTaxa = []
    
        if item.checkState() == Qt.Checked and not item.hasChildren():
            selectedTaxa.append(item.text())

        for i in range (item.rowCount()):
            selectedTaxa.extend(self.getCheckedTaxa(item.child(i,0)))
            
        return selectedTaxa
    
    
        