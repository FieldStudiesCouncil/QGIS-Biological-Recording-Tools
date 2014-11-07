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
from bioreclayer import *
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
        
        self.butBrowse.clicked.connect(self.BrowseForCsv)
        
        self.model = QStandardItemModel(self)
        self.tvRecords.setModel(self.model)
        
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
        self.cboTaxonCol.currentIndexChanged.connect(self.enableDisable)
        self.cboBatchMode.currentIndexChanged.connect(self.enableDisable)
        
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
        
    def enableDisable(self):
    
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
           
        if self.cboBatchMode.currentIndex() == 0:
            pass
        else:
            pass
            
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
            
    def BrowseForCsv(self):
        
        #Reload env
        self.env.loadEnvironment()
        
        if os.path.exists(self.env.getEnvValue("biorec.csvfolder")):
            strInitPath = self.env.getEnvValue("biorec.csvfolder")
        else:
            strInitPath = ""
            
        dlg = QFileDialog
        fileName = dlg.getOpenFileName(self, "Browse for biological record file", strInitPath, "Record Files (*.csv)")
        if fileName:
            #Initialise the tree model
            self.initTreeView()
        
            # Clear all current values
            self.model.clear()
            self.cboGridRefCol.clear()
            self.cboTaxonCol.clear()
            self.cboGroupingCol.clear()
            self.cboAbundanceCol.clear()
            
            # Load the CSV and set controls
            self.leFilename.setText(os.path.basename(fileName))
            self.leFilename.setToolTip(fileName)
            self.loadCsv(fileName)
            
            #self.iface.messageBar().pushMessage("Info", "csv loaded.", level=QgsMessageBar.INFO)
            
    def initTreeView(self):
    
        #Initialise the tree model
        modelTree = QStandardItemModel()
        modelTree.itemChanged.connect(self.tvBoxChecked)
        self.tvTaxa.setModel(modelTree)
        self.modelTree = modelTree
            
    def listTaxa(self):
       
        #Init the tree view
        self.initTreeView()
        
        if self.cboTaxonCol.currentIndex() == 0:
            self.iface.messageBar().pushMessage("Info", "No taxon column selected.", level=QgsMessageBar.INFO)
            return
        iColGrouping = self.cboGroupingCol.currentIndex() - 1
        iColTaxon = self.cboTaxonCol.currentIndex() - 1
        bScientific = self.cbIsScientific.isChecked()
        
        if iColTaxon < 0:
            return
        
        tree = {}
        
        for i in range(self.model.rowCount()):
                    
            if iColGrouping > 0:
                group = self.model.item(i, iColGrouping).text()
                #self.pteLog.appendPlainText("add candidate " + group)
                if group not in tree.keys():
                    tree[group] = {}
                parent = tree[group]         
            else:
                parent = tree
                
            taxon = self.model.item(i, iColTaxon).text()
            
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
            
    def loadCsv(self, fileName):
    
        #Reload the envrionment
        self.env.loadEnvironment()
        
        with open(fileName, "rb") as fileInput:
            firstRow = True
            for row in csv.reader(fileInput):
                if  firstRow:
                    self.cboGridRefCol.addItems([""] + row)
                    self.model.setHorizontalHeaderLabels(row)
                    #for i in range(len(row)):
                        #self.model.setHorizontalHeaderItem(i, QStandardItem(row[i]))
                    self.cboTaxonCol.addItems([""] + row)
                    self.cboGroupingCol.addItems([""] + row)
                    self.cboAbundanceCol.addItems([""] + row)
                    firstRow = False
                    
                    # Set default value for GridRef column
                    for colGridRef in self.env.getEnvValues("biorec.gridrefcol"):
                        index = 1
                        for col in row:
                            if col == colGridRef:
                                self.cboGridRefCol.setCurrentIndex(index)
                                break
                            index += 1
                            
                    # Set default value for Taxon column
                    for colTaxon in self.env.getEnvValues("biorec.taxoncol"):
                        index = 1
                        for col in row:
                            if col == colTaxon:
                                self.cboTaxonCol.setCurrentIndex(index)
                                break
                            index += 1
                            
                    # Set default value for Grouping column
                    for colGrouping in self.env.getEnvValues("biorec.groupingcol"):
                        index = 1
                        for col in row:
                            if col == colGrouping:
                                self.cboGroupingCol.setCurrentIndex(index)
                                break
                            index += 1
                            
                    # Set default value for Abundance column
                    for colAbundance in self.env.getEnvValues("biorec.abundancecol"):
                        index = 1
                        for col in row:
                            if col == colAbundance:
                                self.cboAbundanceCol.setCurrentIndex(index)
                                break
                            index += 1
                            
                    # Set scientific names checkbox if set in environment
                    if self.env.getEnvValue("biorec.scientificnames") == "True":
                        self.cbIsScientific.setChecked(True)
                    else:
                        self.cbIsScientific.setChecked(False)
                            
                else:
                    items = [
                        QStandardItem(field)
                        for field in row
                    ]
                    self.model.appendRow(items)
                    
        self.enableDisable()
        
        #If the maketree environment variable is set, then
        #automatically create tree
        
        if self.env.getEnvValue("biorec.maketree") == "True":
            self.listTaxa() 
        
    def MapRecords(self):
        
        self.progBatch.setValue(0)
        
        # Return if no grid reference field selected
        if self.cboGridRefCol.currentIndex() == 0:
            self.iface.messageBar().pushMessage("Info", "No grid reference column selected.", level=QgsMessageBar.INFO)
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
                    #qApp.processEvents()
                    
            self.progBatch.setValue(0)
            self.cancelBatchMap = False
       
    def batchImageGenerate(self):
          
        if len(self.layers) == 0:
            return
            
        self.progBatch.setValue(0)
        self.progBatch.setMaximum(len(self.layers))
        
        # Make all the layers invisible
        # Setting layer visibility to false does not work
        # it needs to be done by leaving displayed and setting transparency
        # So layers need to already set to visible otherwise they will not
        # appear in image.
        
        for layer in self.layers:
            if not self.cancelBatchMap:
                if self.qgisVersion == ">2":
                    layer.setTransparency(100)
                else:
                    layer.setVisibility(False)
                    
        # In turn set each layer to transparency defined on interface'
        # generate image, and then make invisible again
        #self.iface.mainWindow().statusBar().showMessage("Generating batch images graphics")
        i=0
        for layer in self.layers:
            if not self.cancelBatchMap:
                i=i+1
                self.progBatch.setValue(i)
                #layer.setVisibility(True)
                if self.qgisVersion == ">2":
                    layer.setTransparency(self.hsLayerTransparency.value())
                else:
                    layer.setVisibility(True)
                    
                self.createMapImage(layer)
                #layer.setVisibility(False)
                
                #layer.setVisibility(True)
                if self.qgisVersion == ">2":
                    layer.setTransparency(100)
                else:
                    layer.setVisibility(False)
                #qApp.processEvents()

        # Set all layers to the transparency set by the user
        for layer in self.layers:
            if self.qgisVersion == ">2":
                layer.setTransparency(self.hsLayerTransparency.value())
            else:
                layer.setVisibility(True)
        
        self.progBatch.setValue(0)
        self.cancelBatchMap = False
        
    def showAll(self):
        self.allShowHide(True)
        
    def hideAll(self):
        self.allShowHide(False)
        
    def allShowHide(self, bShow):
          
        if len(self.layers) == 0:
            return
            
        self.progBatch.setValue(0)
        self.progBatch.setMaximum(len(self.layers))
        
        i=0
        for layer in self.layers:
            if not self.cancelBatchMap:
                i=i+1
                self.progBatch.setValue(i)
                layer.setVisibility(bShow)
                #qApp.processEvents()
        
        self.progBatch.setValue(0)
        self.cancelBatchMap = False
        
    def removeMap(self):
        if len(self.layers) > 0:
            layer = self.layers[-1]
            layer.removeFromMap()
            self.layers = self.layers[:-1]
            
    def removeMaps(self):
        if len(self.layers) == 0:
            return
            
        self.progBatch.setValue(0)
        self.progBatch.setMaximum(len(self.layers))
        
        i=0
        for layer in self.layers:
            if not self.cancelBatchMap:
                i=i+1
                self.progBatch.setValue(i)
                layer.removeFromMap()
                #qApp.processEvents()
        
        self.progBatch.setValue(0)
        self.layers = []
        self.cancelBatchMap = False
        
    def cancelBatch(self):
        self.cancelBatchMap = True
       
    def createMapLayer(self, selectedTaxa):
        
        # Initialsie the map layer
        layer = biorecLayer(self.iface, self.cboGridRefCol.currentIndex() - 1, self.cboAbundanceCol.currentIndex() - 1, self.model, self.pteLog) 
        layer.setTaxa(selectedTaxa)
        layer.setColTaxa(self.cboTaxonCol.currentIndex() - 1)
        layer.setTransparency(self.hsLayerTransparency.value())
        
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
            if os.path.exists( self.leStyleFile.text()):
                styleFile = self.leStyleFile.text()
        layer.createMapLayer(self.cboMapType.currentText(), self.cboSymbol.currentText(), styleFile)
        layer.setTransparency(self.hsLayerTransparency.value())
        layer.setExpanded(False)
                           
        self.layers.append(layer)
       
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
                if self.qgisVersion == ">2":
                    pixmap = QPixmap(self.canvas.mapSettings().outputSize().width(), 
                        self.canvas.mapSettings().outputSize().height())
                    self.canvas.saveAsImage(imgFile, pixmap)
                else:
                    self.canvas.saveAsImage(imgFile)
                
                # Don't need the registration file, so delete it
                os.remove(imgFolder + "\\" + validName + ".pngw")
            except:
                if not self.imageError:
                    e = sys.exc_info()[0]
                    self.iface.messageBar().pushMessage("Error", "Image generation error: %s" % e, level=QgsMessageBar.WARNING)
                    self.imageError = True
    
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
    
    
        