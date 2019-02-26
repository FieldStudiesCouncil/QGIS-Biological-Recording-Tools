# -*- coding: utf-8 -*-
"""
/***************************************************************************
BiorecDialog
                                 A QGIS plugin
 FSC QGIS plugin for biological recorders
                             -------------------
        begin                : 2014-02-17
        copyright            : (C) 2014 by Rich Burkmar, Field Studies Council
        email                : richardb@field-studies-council.org
 ***************************************************************************

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""


import os
import ntpath
import csv
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from qgis import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from . import ui_biorec
from . import filedialog
from . import bioreclayer
from . import envmanager
from datetime import datetime
from PyQt5 import QtSql
import re, platform
from .ui_R6 import Ui_R6
from .ui_R6Credentials import Ui_R6Credentials
from qgis.PyQt import QtGui

if platform.system() == 'Windows':
    import winreg

class BiorecDialog(QWidget, ui_biorec.Ui_Biorec):
    def __init__(self, iface, dockwidget):
        QWidget.__init__(self)
        ui_biorec.Ui_Biorec.__init__(self)
        self.setupUi(self)
        self.canvas = iface.mapCanvas()
        self.iface = iface

        #self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        #self.pathPlugin = os.path.dirname( __file__ ) 
        
        #self.model = QStandardItemModel(self)
        #self.tvRecords.setModel(self.model)
        
        self.butBrowse.clicked.connect(self.browseDatasource)
        #self.butGetR6.clicked.connect(self.ChkR6Setup)
        self.butMap.clicked.connect(self.MapRecords)
        self.butShowAll.clicked.connect(self.showAll)
        self.butHideAll.clicked.connect(self.hideAll)
        self.butGenTree.clicked.connect(self.listTaxa)
        self.butSaveImage.clicked.connect(self.batchGeneration)
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
        self.butGithub.clicked.connect(self.github)
        self.fcbTaxonCol.fieldChanged.connect(self.enableDisableTaxa)
        self.cboMapType.currentIndexChanged.connect(self.checkMapType)
        self.mlcbSourceLayer.layerChanged.connect(self.layerSelected)
        self.fcbGridRefCol.fieldChanged.connect(self.enableDisableGridRef)
        self.fcbXCol.fieldChanged.connect(self.enableDisableXY)
        self.fcbYCol.fieldChanged.connect(self.enableDisableXY)
        #self.cbMatchCRS.stateChanged.connect(self.matchCRSClick)
        self.pswInputCRS.crsChanged.connect(self.inputCrsSelected)
        self.cboOutputFormat.currentIndexChanged.connect(self.outputFormatChanged)
        self.rbOutCrsBritish.toggled.connect(self.outCrsRadio)
        self.rbOutCrsIrish.toggled.connect(self.outCrsRadio)
        self.rbOutCrsOther.toggled.connect(self.outCrsRadio)
        self.rbOutCrsInput.toggled.connect(self.outCrsRadio)
        
        # Load the environment stuff
        self.env = envmanager.envManager()
        
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

        self.leImageFolder.setText(self.env.getEnvValue("biorec.r6SQLServerUserName"))
        self.r6Credentials = {
                "server": self.env.getEnvValue("biorec.r6SQLServer"), 
                "user": self.env.getEnvValue("biorec.r6SQLServerUserName"), 
                "pword": self.env.getEnvValue("biorec.r6SQLServerPassword")
            }
        
        # Set button graphics
        self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        self.butMap.setIcon(QIcon( self.pathPlugin % "images/maptaxa.png" ))
        self.butRemoveMap.setIcon(QIcon( self.pathPlugin % "images/removelayer.png" ))
        self.butRemoveMaps.setIcon(QIcon( self.pathPlugin % "images/removelayers.png" ))
        self.butHelp.setIcon(QIcon( self.pathPlugin % "images/info.png" ))
        self.butGithub.setIcon(QIcon( self.pathPlugin % "images/github.png" ))
        self.butSaveImage.setIcon(QIcon( self.pathPlugin % "images/saveimage.png" ))
        self.butShowAll.setIcon(QIcon( self.pathPlugin % "images/layershow.png" ))
        self.butHideAll.setIcon(QIcon( self.pathPlugin % "images/layerhide.png" ))

        #Inits
        self.blockGR = False
        self.blockXY = False
        self.dsbGridSize.setEnabled(False)
        self.lastWaitMessage = None
        self.rbOutCrsBritish.setChecked(True)
        self.outCrsRadio()
        
        self.isNBNCSV = None
        
        self.pswInputCRS.setOptionVisible(self.pswInputCRS.CrsNotSet,True)
        self.pswInputCRS.setNotSetText("CRS not set")

        self.pswOutputCRS.setOptionVisible(self.pswOutputCRS.CrsNotSet,True)
        self.pswOutputCRS.setNotSetText("CRS not set")
        
        self.mlcbSourceLayer.setFilters( QgsMapLayerProxyModel.PointLayer | QgsMapLayerProxyModel.NoGeometry )
        self.mlcbTaxonMetaDataLayer.setFilters( QgsMapLayerProxyModel.NoGeometry )

         # Set scientific names checkbox if set in environment
        if self.env.getEnvValue("biorec.scientificnames") == "True":
            self.cbIsScientific.setChecked(True)
        else:
            self.cbIsScientific.setChecked(False)

        #Programmatic selection of fields not currently working properly so can't set the filters
        #self.fcbGridRefCol.setFilters( QgsFieldProxyModel.String )
        #self.fcbXCol.setFilters( QgsFieldProxyModel.Numeric )
        #self.fcbYCol.setFilters( QgsFieldProxyModel.Numeric )

        #self.fcbGridRefCol.setAllowEmptyFieldName(True)
        #self.fcbXCol.setAllowEmptyFieldName(True)
        #self.fcbYCol.setAllowEmptyFieldName(True)

        self.layerSelected()
        
    def checkMapType(self):
        if self.cboMapType.currentText().startswith("User-defined"):
           self.dsbGridSize.setEnabled(True)
        else:
           self.dsbGridSize.setValue(0)
           self.dsbGridSize.setEnabled(False)

    def getR6Credentials(self):
        dlg = R6CredentialsDialog(self.r6Credentials)
        dlg.exec_()
        okayed = dlg.okayed
        if okayed:
            self.r6Credentials = dlg.credentials
        dlg.close()
        #print(self.r6Credentials)
        return okayed

    def ChkR6Setup(self):
        
        dbOpen = False
        db = QtSql.QSqlDatabase.addDatabase('QODBC')

        if platform.system() == 'Windows':
            try:
                #r6Key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Dropbox', 0, #For testing on non-R6 machine
                r6Key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Dorset Software', 0,
                                      (winreg.KEY_WOW64_64KEY + winreg.KEY_READ))
            except:
                #There was some sort of error trying to retrieve the R6 registry key
                r6Key = None
   
            if r6Key:
                #Registry R6 keys found, retrieve servername and user it to build trusted connection string
                subname = winreg.EnumKey(r6Key, 0)
                subkey = winreg.OpenKey(r6Key, subname, 0, (winreg.KEY_WOW64_64KEY + winreg.KEY_READ))
                #self.r6Credentials["server"] = winreg.QueryValueEx(subkey, "Version")[0] #For testing on non-R6 machine
                self.r6Credentials["server"] = winreg.QueryValueEx(subkey, "Server Name")[0]
                con_str = "DRIVER={{SQL Server}};SERVER={0};DATABASE=NBNData;Trusted_Connection=yes;".format('{' + self.r6Credentials["server"] + '}')
                #Attempt to open DB with trusted connection string
                self.waitMessage("Connecting to DB", "attempting to connect to R6 DB with trusted connection...")
                db.setDatabaseName(con_str)
                self.waitMessage()
                if db.open():
                    dbOpen = True

            if not dbOpen:
                #Prompt user for R6 servername (already initialised if r6Key found), username and password
                if self.getR6Credentials():
                    con_str = 'DRIVER={{SQL Server}};SERVER={0};Database=NBNData;UID={1};PWD={2};'.format('{' + self.r6Credentials["server"] + '}',self.r6Credentials["user"],self.r6Credentials["pword"])
                    #Attempt connection with supplied credentials
                    self.waitMessage("Connecting to DB", "attempting to connect to R6 DB with supplied credentials...")
                    db.setDatabaseName(con_str)
                    self.waitMessage()
                    if db.open():
                        dbOpen = True
                    else:
                        self.errorMessage("Couldn't connect with those credentials")
        else:
            self.errorMessage("R6 only runs on Windows platform")

        if dbOpen:
            #Open dialog for user to generate CSV memory layer from SQL query
            r6dlg = R6Dialog()
            r6dlg.exec_()

            if r6dlg.csvLayer:
                self.mlcbSourceLayer.setLayer(r6dlg.csvLayer)

            if r6dlg.message:
                self.infoMessage(r6dlg.message)

            r6dlg.close()
            db.close()

            #if R6Dialog.fn !='None':
            #    nbnFile = False
            #    self.loadCsv(R6Dialog.fn, nbnFile)
            #    db.close()
            #    R6Dialog.fn = 'None'

    def outputFormatChanged(self):
        format = self.cboOutputFormat.currentText()
        if (format == "GeoJSON") or (format == "Shapefile"):
            self.qgsOutputCRS.setEnabled(True)
        else:
            self.qgsOutputCRS.setEnabled(False)
        
    def showEvent(self, ev):
        # Load the environment stuff
        self.env = envmanager.envManager()
        self.leImageFolder.setText(self.env.getEnvValue("biorec.atlasimagefolder"))
        return QWidget.showEvent(self, ev)

    def logMessage(self, strMessage, level=Qgis.Info):
        QgsMessageLog.logMessage(strMessage, "Biological Records Tool", level)
    
    def infoMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Info", strMessage, level=Qgis.Info)
        
    def warningMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Warning", strMessage, level=Qgis.Warning)

    def errorMessage(self, strMessage):
        self.iface.messageBar().pushMessage("Error", strMessage, level=Qgis.Critical)
        
    def waitMessage(self, str1="", str2=""):
        
        try:
            #This fails if self.lastWaitMessage already deleted so needs to be caught
            iface.messageBar().popWidget(self.lastWaitMessage)
        except:
            pass

        if str1 != "":
            widget = iface.messageBar().createMessage(str1, str2)
            self.lastWaitMessage = iface.messageBar().pushWidget(widget, Qgis.Info)
            qApp.processEvents()
         
    def helpFile(self):

        #if self.guiFile is None:
        #    self.guiFile = filedialog.FileDialog(self.iface, self.infoFile)
        
        #self.guiFile.setVisible(True)    

        QDesktopServices().openUrl(QUrl("http://www.fscbiodiversity.uk/qgisbiorecstool"))

    def github(self):
        QDesktopServices().openUrl(QUrl("https://github.com/FieldStudiesCouncil/QGIS-Biological-Recording-Tools/issues"))

    def outCrsRadio(self):
        if self.rbOutCrsBritish.isChecked():
            self.pswOutputCRS.setEnabled(False)
            self.pswOutputCRS.setCrs(QgsCoordinateReferenceSystem("EPSG:27700"))

        elif self.rbOutCrsIrish.isChecked():
            self.pswOutputCRS.setEnabled(False)
            self.pswOutputCRS.setCrs(QgsCoordinateReferenceSystem("EPSG:29903"))

        elif self.rbOutCrsInput.isChecked():
            self.pswOutputCRS.setEnabled(False)
            self.pswOutputCRS.setCrs(self.pswInputCRS.crs())

        elif self.rbOutCrsOther.isChecked():
            self.pswOutputCRS.setEnabled(True)
            self.pswOutputCRS.setCrs(QgsCoordinateReferenceSystem(None))
                
    def enableDisableGridRef(self):

        if self.blockGR:
            return

        self.blockGR = True

        if self.csvLayer != None:

            if self.csvLayer.geometryType() == 3 or self.csvLayer.geometryType() == 4:                
                #QGis.GeometryType.NoGeometry = 4
                #QGis.GeometryType.UnknownGeometry = 3

                self.fcbGridRefCol.setEnabled(True)
                self.lblGridRefCol.setEnabled(True)
                self.fcbXCol.setEnabled(True)
                self.lblXCol.setEnabled(True)
                self.fcbYCol.setEnabled(True)
                self.lblYCol.setEnabled(True)

                if self.fcbGridRefCol.currentField() != "" and not self.blockXY:

                    if self.fcbXCol.currentField() != "":
                        self.fcbXCol.setField("not set")
                    if self.fcbYCol.currentField() != "":
                        self.fcbYCol.setField("not set")

                if self.fcbGridRefCol.currentField() != "":

                    #When grid references are used for input, Input CRS is not set
                    self.pswInputCRS.setCrs(QgsCoordinateReferenceSystem(None))
                    self.pswInputCRS.setEnabled(False)

                    #self.pswInputCRS.setCrs(QgsCoordinateReferenceSystem("EPSG:27700"))
                    #self.pswOutputCRS.setEnabled(False)
                    #self.pswOutputCRS.setCrs(QgsCoordinateReferenceSystem("EPSG:27700"))
            
                    if self.cboMapType.currentText().startswith("User-defined"):
                        self.cboMapType.setCurrentIndex(0)      

                else:
                    self.pswInputCRS.setEnabled(True)
                    #self.pswOutputCRS.setEnabled(not self.cbMatchCRS.isChecked())
                    self.pswOutputCRS.setEnabled(not self.rbOutCrsInput.isChecked())
                    
                bClear = False
            else:
                self.pswInputCRS.setEnabled(False)
                bClear = True
        else:
            bClear = True
        
        if bClear:
            if self.fcbGridRefCol.currentField() != "":
                self.fcbGridRefCol.setField("not set")
            if self.fcbXCol.currentField() != "":
                self.fcbXCol.setField("not set")
            if self.fcbYCol.currentField() != "":
                self.fcbYCol.setField("not set")
            self.fcbGridRefCol.setEnabled(False)
            self.lblGridRefCol.setEnabled(False)
            self.fcbXCol.setEnabled(False)
            self.lblXCol.setEnabled(False)
            self.fcbYCol.setEnabled(False)
            self.lblYCol.setEnabled(False)
     
        self.blockGR = False
        
    def enableDisableXY(self):

        if self.blockXY:
            return

        self.blockXY = True
        
        if (self.fcbXCol.currentField() != "" or self.fcbYCol.currentField() != "") and not self.blockGR:
            if self.fcbGridRefCol.currentField() != "":
                self.fcbGridRefCol.setField("not set")

        self.enableDisableGridRef()
        
        self.blockXY = False
            
    def enableDisableTaxa(self):
    
        if self.fcbTaxonCol.currentIndex() == 0:
            self.fcbGroupingCol.setCurrentIndex(0)
            self.fcbGroupingCol.setEnabled(False)
            self.lblGroupingCol.setEnabled(False)
            self.cbIsScientific.setChecked(False)
            self.cbIsScientific.setEnabled(False)     
        else:
            self.fcbGroupingCol.setEnabled(True)
            self.cbIsScientific.setEnabled(True)
            self.lblGroupingCol.setEnabled(True)
            
    def inputCrsSelected(self, crs):
    
        #if self.cbMatchCRS.isChecked():
        if self.rbOutCrsInput.isChecked():
            self.pswOutputCRS.setCrs(self.pswInputCRS.crs())
        
    def browseImageFolder(self):
    
        #Reload env
        self.env.loadEnvironment()
        
        dlg = QFileDialog
        
        if os.path.exists(self.leImageFolder.text()):
            strInitPath = self.leImageFolder.text()
        else:
            strInitPath = ""
            
        folderName = dlg.getExistingDirectory(self, "Browse for image folder", strInitPath)
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
        fileName = dlg.getOpenFileName(self, "Browse for style file", strInitPath, "QML Style Files (*.qml)")[0]
        if fileName:
            self.leStyleFile.setText(fileName)
            self.leStyleFile.setToolTip(fileName)
            
    def browseDatasource(self):

        datasource = self.cboDatasource.currentText()
        #if (datasource == "Create source from CSV file") or (format == "Shapefile"):
        if (datasource == "Create source from CSV file"):
            self.setCSV(None)
        elif (datasource == "Create source from R6 database"):
            self.ChkR6Setup()

    def setCSV(self, nbnFile):
        
        #Reload env
        self.env.loadEnvironment()
        
        if os.path.exists(self.env.getEnvValue("biorec.csvfolder")):
            strInitPath = self.env.getEnvValue("biorec.csvfolder")
        else:
            strInitPath = ""
            
        if nbnFile is None:
            dlg = QFileDialog
            fileName = dlg.getOpenFileName(self, "Browse for biological record file", strInitPath, "Record Files (*.csv)")[0]
            #According to the documentation, this should return a string, but it returns a tuple of this form:
            #('C:/Users/richardb/Documents/Work/GIS/Biological Records etc/Andy Musgrove Yorkshire BirdTrack records.csv', 'Record Files (*.csv)'
            #or, if cancelled, ('', '').
        else:
            fileName = nbnFile
            
        self.logMessage("File: >>" + fileName + "<<")
        
        if fileName != "":
            # Load the CSV and set controls
            self.loadCsv(fileName, (not nbnFile is None))
          
    def initTreeView(self):

        #Initialise the tree model
        modelTree = QStandardItemModel()
        modelTree.itemChanged.connect(self.tvBoxChecked)
        self.tvTaxa.setModel(modelTree)
        self.modelTree = modelTree

    def listTaxa(self, suppressMessage=False):
       
        #Init the tree view
        self.initTreeView()
        
        if self.csvLayer is None:
            return

        if self.fcbTaxonCol.currentIndex() < 1:
            if not suppressMessage:
                self.infoMessage("No taxon column selected")
            return
            
        iColGrouping = self.fcbGroupingCol.currentIndex() - 1
        iColTaxon = self.fcbTaxonCol.currentIndex() - 1
        bScientific = self.cbIsScientific.isChecked()
        
        if iColTaxon == -1:
            return
            
        self.waitMessage("Building taxon tree", "can take a minute or so for very large files...")
        
        tree = {}
        iter = self.csvLayer.getFeatures()

        for feature in iter:
       
            if iColGrouping > -1:

                try:
                    group = feature.attributes()[iColGrouping].strip()
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
                taxon = feature.attributes()[iColTaxon].strip()
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

        #Build tree from nested lists (which are sorted on the fly)
        #The technique for sorting dicts came from https://stackoverflow.com/questions/11089655/sorting-dictionary-python-3
        for l1 in {k: tree[k] for k in sorted(tree)}:
            itemL1 = QStandardItem(l1)
            itemL1.setCheckable(True)
            self.modelTree.appendRow(itemL1)
            
            dictL2 = tree[l1]
            for l2 in {k: dictL2[k] for k in sorted(dictL2)}:
                itemL2 = QStandardItem(l2)
                itemL2.setCheckable(True)
                itemL1.appendRow(itemL2)
                
                dictL3 = dictL2[l2]
                for l3 in {k: dictL3[k] for k in sorted(dictL3)}:
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
                
    def loadCsv(self, fileName, isNBNCSV):
    
        self.isNBNCSV = isNBNCSV
        
        #Reload the environment
        self.env.loadEnvironment()
        
        #Load as a CSV
        uri = "file:///" + fileName + "?delimiter=%s" % (",")
        
        self.waitMessage("Loading", fileName)
        try:
            lyr =  QgsVectorLayer(uri, os.path.basename(fileName), "delimitedtext")
            #Add to registry
            QgsProject.instance().addMapLayer(lyr)
        except:
            lyr = None
            
        self.waitMessage()
        
        if lyr == None:
            self.warningMessage("Couldn't open CSV file: '%s'" % (fileName))
        else:
            #Set in layer selection list.
            self.mlcbSourceLayer.setLayer(lyr)
            
    def layerSelected(self):

        if self.csvLayer != self.mlcbSourceLayer.currentLayer():

            # Clear taxon tree
            self.initTreeView()

            self.csvLayer = self.mlcbSourceLayer.currentLayer()
            
            if self.csvLayer != None:
                self.pswInputCRS.setCrs(self.csvLayer.crs())
                #if self.cbMatchCRS.isChecked():
                if self.rbOutCrsInput.isChecked():
                    self.pswOutputCRS.setCrs(self.pswInputCRS.crs())
            
            #Need to enable field selectors in order to set values
            self.fcbGridRefCol.setEnabled(True)
            self.lblGridRefCol.setEnabled(True)
            self.fcbXCol.setEnabled(True)
            self.lblXCol.setEnabled(True)
            self.fcbYCol.setEnabled(True)
            self.lblYCol.setEnabled(True)
            self.fcbGridRefCol.setLayer(self.csvLayer)
            self.fcbXCol.setLayer(self.csvLayer)
            self.fcbYCol.setLayer(self.csvLayer)
            self.fcbAbundanceCol.setLayer(self.csvLayer)
            self.fcbGroupingCol.setLayer(self.csvLayer)
            self.fcbTaxonCol.setLayer(self.csvLayer)
            self.fcbDateCol.setLayer(self.csvLayer)
            self.fcbDate2Col.setLayer(self.csvLayer)

            if self.csvLayer != None:
                #Initialise the tree model
                self.initTreeView()

                # Set default value for GridRef column
                if self.isNBNCSV:
                    index = 1
                    for field in self.csvLayer.dataProvider().fields():
                        if field.name() == "OSGR":
                            self.fcbGridRefCol.setField(field.name())
                            break
                        index += 1
                else:
                    for colGridRef in self.env.getEnvValues("biorec.gridrefcol"):
                        index = 1
                        for field in self.csvLayer.dataProvider().fields():
                            if field.name() == colGridRef:
                                self.fcbGridRefCol.setField(field.name())
                                break
                            index += 1

                if self.fcbGridRefCol.currentField() == "":
                    # Set default value for X column
                    for colX in self.env.getEnvValues("biorec.xcol"):
                        index = 1
                        for field in self.csvLayer.dataProvider().fields():
                            if field.name() == colX:
                                self.fcbXCol.setField(field.name())
                                break
                            index += 1
                        
                    # Set default value for Y column
                    for colY in self.env.getEnvValues("biorec.ycol"):
                        index = 1
                        for field in self.csvLayer.dataProvider().fields():
                            if field.name() == colY:#
                                self.fcbYCol.setField(field.name())
                                break
                            index += 1

                # Set default value for Taxon column
                if self.isNBNCSV:
                    index = 1
                    for field in self.csvLayer.dataProvider().fields():
                        if field.name() == "Matched Scientific Name":
                            self.fcbTaxonCol.setCurrentIndex(index)
                            self.fcbTaxonCol.setCurrentIndex(index)
                            break
                        index += 1
                else:
                    for colTaxon in self.env.getEnvValues("biorec.taxoncol"):
                        index = 1
                        for field in self.csvLayer.dataProvider().fields():
                            if field.name() == colTaxon:
                                self.fcbTaxonCol.setCurrentIndex(index)
                                break
                            index += 1
                        
                # Set default value for Grouping column
                for colGrouping in self.env.getEnvValues("biorec.groupingcol"):
                    index = 1
                    for field in self.csvLayer.dataProvider().fields():
                        if field.name() == colGrouping:
                            self.fcbGroupingCol.setCurrentIndex(index)
                            break
                        index += 1
                        
                # Set default value for Abundance column
                for colAbundance in self.env.getEnvValues("biorec.abundancecol"):
                    index = 1
                    for field in self.csvLayer.dataProvider().fields():
                        if field.name() == colAbundance:
                            self.fcbAbundanceCol.setCurrentIndex(index)
                            break
                        index += 1

                # Set default value for start date column
                for colDate in self.env.getEnvValues("biorec.datestartcol"):
                    self.logMessage("start date col:" + colDate)
                    index = 1
                    for field in self.csvLayer.dataProvider().fields():
                        self.logMessage("csv field:" + field.name())
                        if field.name() == colDate:
                            self.fcbDateCol.setCurrentIndex(index)
                            break
                        index += 1

                # Set default value for end date column
                for colDate in self.env.getEnvValues("biorec.dateendcol"):
                    self.logMessage("end date col:" + colDate)
                    index = 1
                    for field in self.csvLayer.dataProvider().fields():
                        if field.name() == colDate:
                            self.fcbDate2Col.setCurrentIndex(index)
                            break
                        index += 1

                #If the maketree environment variable is set, then
                #automatically create tree
                #Take this out because it can really slow things down when layers
                #automatically selected from drop-down.
                #if self.env.getEnvValue("biorec.maketree") == "True":
                    #self.listTaxa(True) 
            
            self.enableDisableTaxa()
            self.enableDisableGridRef()
            self.enableDisableXY()

            if self.cbLoadTaxa.isChecked():
                self.listTaxa(False)
                self.checkAll()
            
    def MapRecords(self):
              
        # Before creating new layers, for current list of layers, remove any from the list which are not 
        # listed in map registry. This accounts for people removing layers direct from registry.
        tmpLayers = []
        for layer in self.layers:
            try:
                regLayer = QgsProject.instance().mapLayer(layer.getVectorLayer().id())
                layerFound = True
            except:
                layerFound = False
            
            if layerFound:
                tmpLayers.append(layer)
                
        self.layers = list(tmpLayers)
        
        # Initialise progress bar
        self.progBatch.setValue(0)

        # Return if no output CRS
        if self.pswOutputCRS.crs().authid() == "":
            self.iface.messageBar().pushMessage("Info", "You must specify an output CRS", level=Qgis.Info)
            return

        # Return if grid ref field set and user-defined grid is set
        if self.fcbGridRefCol.currentField() != "" and self.cboMapType.currentText().startswith("User-defined"):
            self.infoMessage("Can't set a user-defined grid size when using grid references as input")
            return

        # Return if output is records as grid squares but grid ref column not set
        if self.cboMapType.currentText() == "Records as grid squares" and self.fcbGridRefCol.currentField() == "":       
            self.infoMessage("'Records as grid squares' only available for input as grid references")
            return
        
        # Return if no grid reference or X & Y fields selected - but only for layers without geometry
        if self.csvLayer.geometryType() == 3 or self.csvLayer.geometryType() == 4:
            #QGis.GeometryType.NoGeometry = 4
            #QGis.GeometryType.UnknownGeometry = 3
            
            self.fcbGridRefCol.currentField() == ""
            
            if self.fcbGridRefCol.currentField() == "" and (self.fcbXCol.currentField() == "" or self.fcbYCol.currentField() == ""):
                self.iface.messageBar().pushMessage("Info", "You must select either a Grid Ref column or both X and Y columns for CSV layers", level=Qgis.Info)
                return
            
        # Return if Grid ref selected with user-defined grid
        if self.fcbGridRefCol.currentField() != "" and self.cboMapType.currentText().startswith("User-defined"):
            self.iface.messageBar().pushMessage("Info", "You cannot specify a user-defined grid with input of grid references", level=Qgis.Info)
            return
           
        
        # Return if X & Y selected but no input CRS
        if self.fcbXCol.currentField() != "" and self.pswInputCRS.crs().authid() == "":
            self.iface.messageBar().pushMessage("Info", "You must specify an input CRS if specifying X and Y columns", level=Qgis.Info)
            return
            
        # Return if X & Y selected but no output CRS
        if self.fcbXCol.currentField() != "" and self.pswOutputCRS.crs().authid() == "":
            self.iface.messageBar().pushMessage("Info", "You must specify an output CRS if specifying X and Y columns", level=Qgis.Info)
            return
            
        # Return if user-defined atlas selected, but no grid size
        if self.cboMapType.currentText().startswith("User-defined") and self.dsbGridSize.value() == 0:
            self.iface.messageBar().pushMessage("Info", "You must specify a grid size if specifying a user-defined atlas", level=Qgis.Info)
            return

        # Return if a grid option selected, but the output CRS is not Irish or British Grid (unless input is grid references)
        if self.fcbGridRefCol.currentField() == "" and not self.cboMapType.currentText().startswith("User-defined") and not self.cboMapType.currentText() == "Records as points":
            if self.pswOutputCRS.crs().authid() != "EPSG:27700" and self.pswOutputCRS.crs().authid() != "EPSG:29903":
                self.infoMessage("Only points or user-defined grid can be use for output CRS that is not either Irish or British Grid (EPSG:29903 or EPSG:2770) where input is not grid references")
                return
        
        # Make a list of all the selected taxa
        selectedTaxa = []
      
        if not self.tvTaxa.model() is None:
            for i in range(self.tvTaxa.model().rowCount()):
                selectedTaxa.extend(self.getCheckedTaxa(self.tvTaxa.model().item(i,0)))
            
        if len(selectedTaxa) == 0 and self.fcbTaxonCol.currentIndex() > 0:
            self.iface.messageBar().pushMessage("Info", "No taxa selected.", level=Qgis.Info)
            return
            
        if self.cboBatchMode.currentIndex() == 0 or self.fcbTaxonCol.currentIndex() == 0:
            self.progBatch.setValue(0)
            self.progBatch.setMaximum(100)  #bioreclayer increments progress in percentage points
            self.createMapLayer(selectedTaxa)
            self.progBatch.setValue(0)
        else:
            self.progBatch.setMaximum(len(selectedTaxa) * 100)
            i = 0
            self.folderError = False
            self.imageError = False
            for taxa in selectedTaxa:
                if not self.cancelBatchMap:
                    self.progBatch.setValue(i * 100) #bioreclayer increments progress in percentage points
                    i=i+1
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

        QgsProject.instance().addMapLayers(layerIDs)
        
        #try:
        #    QgsProject.instance().addMapLayers(layerIDs)
        #except:
        #    self.iface.messageBar().pushMessage("Error", "Problem adding layers. Clear bio.rec layers with 'remove all map layers' button and try again.", level=Qgis.Critical)
            
        # Make sure none of the layers expanded
        for layer in self.layers:
            ##????????????????? Is this working?????
            layer.setExpanded(False)
    
    def batchGeneration(self):
        #Check that there are temp layers to work with
        if len(self.layers) == 0:
            self.infoMessage("There are no temporary biorec layers to work with.")
            return
        #Check that an output folder is specified
        imgFolder = self.leImageFolder.text()
        if not os.path.exists(imgFolder):
            if not self.folderError:
                self.iface.messageBar().pushMessage("Error", "Output folder '%s' does not exist." % (imgFolder), level=Qgis.Warning)
                return   
        format = self.cboOutputFormat.currentText()
        if (format == "GeoJSON") or (format == "Shapefile"):
            self.batchLayer(format)
        elif (format == "Image"):
            self.batchImageGenerate()
        elif (format == "Composer image") or (format == "Composer PDF"):
            self.batchPrintComposer()
           
    def batchPrintComposer(self):
        
        #Ensure that a layout desinger (and only one) is open
        iLayouDesigners = len(iface.openLayoutDesigners())
        if iLayouDesigners == 0:
            self.warningMessage("Cannot connect to a layout. Make sure that the print layout (composer) you want to use is open.")
            return
        if iLayouDesigners > 1:
            self.warningMessage("You have more than one layout open. Make sure that only one print layout (composer) is open.")
            return

        if len(self.layers) == 0:
            return
            
        self.progBatch.setValue(0)
        self.progBatch.setMaximum(len(self.layers))

        tempLayers = []
        for layer in self.layers:
            tempLayers.append(layer.vl)
            
        displayedLayers = self.canvas.mapSettings().layers()
        backdropLayers = [item for item in displayedLayers if item not in tempLayers]

        settings = self.canvas.mapSettings()
        i=0

        format = self.cboOutputFormat.currentText()

        for layer in self.layers:
            if not self.cancelBatchMap:
                self.waitMessage("Creating " + format + " for " + layer.getName())
                i=i+1
                self.progBatch.setValue(i)
                layersRender = [layer.vl] + backdropLayers
                self.saveComposerImage(layer.getName(), layersRender)
                qApp.processEvents()
                self.waitMessage()

        self.progBatch.setValue(0)
        self.cancelBatchMap = False

    def batchPrintComposerOld(self):
        
        #Generate image from print composer
        
        #Get the first active composer
        #Could not find a way to list the composers currently associated with the project by name
        try:
            c = self.iface.activeComposers()[0].composition()
        except:
            self.warningMessage("Cannot connect to a print composer. Make sure that a print composer is available.")
            return
            
        #Check that only one temp layer is visible
        iVisibleLayers = 0
        for tmplyr in self.layers:
            lyr = tmplyr.getVectorLayer()
            #if self.iface.legendInterface().isLayerVisible(lyr):
            if QgsProject.instance().layerTreeRoot().findLayer(lyr.id()).isVisible():
        
                iVisibleLayers += 1
        
        if iVisibleLayers != 1:
            self.warningMessage("You must have one, and only one, temp layer visible. You have %s visible layers." % (str(iVisibleLayers)))
            return
            
        #Set the output folder
        imgFolder = self.leImageFolder.text()

        #Get the current visible layer 
        iLyr = 0
        for tmplyr in self.layers:
            lyr = tmplyr.getVectorLayer()
            iLyr+=1
            #if self.iface.legendInterface().isLayerVisible(lyr):
            if QgsProject.instance().layerTreeRoot().findLayer(lyr.id()).isVisible():
                currentLayer = lyr
                break

        validName = self.makeValidFilename(currentLayer.name())
        #Remove 'TEMP ' from start of name.
        validName = validName[5:]
        outputFileName = imgFolder + os.path.sep + validName

               
        #Get the taxon name from the layer
        nameReplace = currentLayer.name()[5:]
        suffixes = ["10 km atlas", "5 km atlas", "2 km atlas", "1 km atlas", "100 m atlas", "10 m atlas"]
        for suffix in suffixes:
            if nameReplace.find(suffix) > -1:
                nameReplace = nameReplace[0:nameReplace.find(suffix)-1]
                
        #For each text item, replace the tokens, e.g. #name#, with corresponding text. 

        #Get all text items from the layout.
        #Item.scene() ensures that the item is being used (not deleted)
        textItems = [item for item in c.items() if item.type() == QgsComposerItem.ComposerLabel and item.scene()]

        #Save the original text item values so that they can be reset afterwards
        originalText=[]
        for textItem in textItems:
            originalText.append(textItem.text())

        #Now replace the #name# tokens with the 'nameReplace' text derived from
        #the layer name - usually based on the taxon name.
        for textItem in textItems:
            textItem.setText(textItem.text().replace('#name#', nameReplace))
            c.refreshItems()

        #If TaxonMetaDataLayer has been set and checkbox set to use it, then set a filter to select
        #only the rows (should be only one) that match the current taxon (derived from layer name).
        #Then for each field in the TaxonMetaDataLayer, check to see if each of the fields in the
        #TaxaonMetaDataLayer has been used as a token in any checkboxes and, if so, replace the token
        #for the value of that field for the species at hand.
        if self.cbTaxonMetaData.isChecked() and self.mlcbTaxonMetaDataLayer.currentLayer() is not None:
            metaLayer = self.mlcbTaxonMetaDataLayer.currentLayer()
            #The regular expression (~ comparison) allows for leading and trailing white space on the taxa
            strFilter = '"%s" ~ \' *%s *\'' % ("Taxon", nameReplace)
            #self.infoMessage(strFilter)
            request = QgsFeatureRequest().setFilterExpression(strFilter)
            iField = 0
            for field in metaLayer.dataProvider().fields():
                strVal = ''
                iter = metaLayer.getFeatures(request)
                for feature in iter: #Should only be one (or zero) features
                    try:
                        strVal = feature.attributes()[iField].strip()
                    except:
                        strVal = ''
                for textItem in textItems:
                    if '#' + field.name() + '#' in textItem.text():
                        textItem.setText(textItem.text().replace('#' + field.name() + '#', strVal))
                    c.refreshItems()
                iField += 1

        #Save image from print composer
        self.waitMessage("Generating output", "Creating output for " + nameReplace)
        if self.cboOutputFormat.currentText() == "Composer image":
            image = c.printPageAsRaster(0)
            image.save(outputFileName + ".png")
        else:
            c.exportAsPDF(outputFileName + ".pdf")
        self.waitMessage()
        
        #Reset the print composer's label items text to the original values
        iTextItem = 0
        for textItem in textItems:
            textItem.setText(originalText[iTextItem])
            c.refreshItems()
            iTextItem += 1
        
        #Uncheck this layer and check the next one
        #iface.legendInterface().setLayerVisible(currentLayer, False)
        QgsProject.instance().layerTreeRoot().findLayer(currentLayer.id()).setItemVisibilityChecked(False)

        if iLyr < len(self.layers):
            nextLyr = self.layers[iLyr].getVectorLayer()
        else:
            nextLyr = self.layers[0].getVectorLayer()
            
        #iface.legendInterface().setLayerVisible(nextLyr, True)
        QgsProject.instance().layerTreeRoot().findLayer(nextLyr.id()).setItemVisibilityChecked(True)
        
    def batchLayer(self, format):
    
        #Check that an output CRS has been set
        if self.qgsOutputCRS.crs().authid() == "":
            self.warningMessage("You must first specify a valid output CRS")
            return
            
        self.progBatch.setValue(0)
        self.progBatch.setMaximum(len(self.layers))
        
        i=0
        for layer in self.layers:
            if not self.cancelBatchMap:
                self.waitMessage("Saving layer " + layer.getName() + " as " + format)
                i=i+1
                self.progBatch.setValue(i)
                self.saveTempToLayer(layer, format)
                self.waitMessage()

        self.progBatch.setValue(0)
        self.cancelBatchMap = False
        
    def batchImageGenerate(self):
          
        if len(self.layers) == 0:
            return
            
        self.progBatch.setValue(0)
        self.progBatch.setMaximum(len(self.layers))

        tempLayers = []
        for layer in self.layers:
            tempLayers.append(layer.vl)
            
        displayedLayers = self.canvas.mapSettings().layers()
        backdropLayers = [item for item in displayedLayers if item not in tempLayers]

        settings = self.canvas.mapSettings()
        i=0
        for layer in self.layers:
            if not self.cancelBatchMap:
                self.waitMessage("Creating map image for " + layer.getName())
                i=i+1
                self.progBatch.setValue(i)
                layersRender = [layer.vl] + backdropLayers
                settings.setLayers(layersRender)
                job = QgsMapRendererParallelJob(settings)
                job.start()
                job.waitForFinished()
                image = job.renderedImage()
                self.saveMapImage(image, layer.getName())
                qApp.processEvents()
                self.waitMessage()

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
            self.canvas.refresh()
            
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
        QgsProject.instance().removeMapLayers(layerIDs)
        self.progBatch.setValue(0)
        self.canvas.refresh()
        
    #def removeAllLayers(self):
    #    QgsProject.instance().removeAllMapLayers()
        
    def cancelBatch(self):
        self.cancelBatchMap = True
   
    def createMapLayer(self, selectedTaxa):
        
        # Initialsie the map layer
        layer = bioreclayer.biorecLayer(self.iface, self.csvLayer, self.pteLog, self.progBatch)

        layer.setTaxa(selectedTaxa)
        layer.setColTaxa(self.fcbTaxonCol.currentIndex() - 1)
        layer.setColAb(self.fcbAbundanceCol.currentIndex() - 1)

        layer.setColGr(self.fcbGridRefCol.currentIndex() -1)
        layer.setColX(self.fcbXCol.currentIndex() -1)
        layer.setColY(self.fcbYCol.currentIndex() -1)

        layer.setColDate(self.fcbDateCol.currentIndex() -1)
        layer.setColDate2(self.fcbDate2Col.currentIndex() -1)
        
        layer.setTransparency(self.hsLayerTransparency.value())

        layer.setCrs(self.pswInputCRS.crs().authid(), self.pswOutputCRS.crs().authid())
        layer.setGridSize(self.dsbGridSize.value())
        
        # Name the layer
        if len(selectedTaxa) == 1:
            layerName = selectedTaxa[0]
        else:
            layerName = self.csvLayer.name()
            
        if layerName.lower().endswith(".csv"):
            layerName = layerName[:-4]
            
        mapType = self.cboMapType.currentText()
        if '(' in mapType:
            layerName = layerName + " " + mapType[:mapType.index('(')-1 ]
   
        # Prepend map layer name with 'TEMP'
        layerName = "TEMP " + layerName
        layer.setName(layerName)
        
        # Create the map layer
        styleFile = None
        if self.cbApplyStyle.isChecked():
 
            if self.cboMapType.currentIndex() == 0:
                self.iface.messageBar().pushMessage("Warning", "Applied style file to points layer. Points will not be visible if no style for points defined.", level=Qgis.Warning)
                
            if os.path.exists( self.leStyleFile.text()):
                styleFile = self.leStyleFile.text()
                
        self.waitMessage("Making map layer", layerName)
        layer.createMapLayer(self.cboMapType.currentText(), self.cboSymbol.currentText(), styleFile)  
        self.waitMessage()
        
        self.layers.append(layer)
        
    def saveTempToLayer(self, layer, format):

        imgFolder = self.leImageFolder.text()
        outCRS = QgsCoordinateReferenceSystem(self.qgsOutputCRS.crs().authid())
        
        validName = self.makeValidFilename(layer.getName())
        #Remove 'TEMP ' from start of name.
        validName = validName[5:]
        filePath = imgFolder + os.path.sep + validName
            
        if format == "GeoJSON":
            formatArg =  "GeoJSON"
        elif format == "Shapefile":
            formatArg =  "ESRI Shapefile"
                
        error = QgsVectorFileWriter.writeAsVectorFormat(layer.getVectorLayer(), filePath, "utf-8", outCRS, formatArg)

        #self.logMessage("error - " + str(error))
        #self.logMessage("NoError - " + str(QgsVectorFileWriter.NoError))

        if error[0] != QgsVectorFileWriter.NoError:
            self.iface.messageBar().pushMessage("Error", "Layer generation error: %s" % (error), level=Qgis.Warning)
            return

        #If saving a shapefile, also save the style as the default style
        if format == "Shapefile":
            ret = layer.vl.saveNamedStyle(filePath + ".qml")
            #self.logMessage("return = " + str(ret))
                
    def saveMapImage(self, image, name):
        
        imgFolder = self.leImageFolder.text()
        validName = self.makeValidFilename(name)
        #Remove 'TEMP ' from start of name.
        validName = validName[5:]
            
        try:
            #Uncomment the following line to restore saveMapImage
            image.save(imgFolder + os.path.sep + validName + ".png")
        except:
            if not self.imageError:
                e = sys.exc_info()[0]
                self.iface.messageBar().pushMessage("Error", "Image generation error: %s" % (e), level=Qgis.Warning)
                self.imageError = True

    def saveComposerImage(self, name, layers):

        l = iface.openLayoutDesigners()[0].layout()
        
        imgFolder = self.leImageFolder.text()
        validName = self.makeValidFilename(name)
        #Remove 'TEMP ' from start of name.
        validName = validName[5:]
        outputFileName = imgFolder + os.path.sep + validName
               
        #Get the taxon name from the layer
        nameReplace = validName
        suffixes = ["10 km atlas", "5 km atlas", "2 km atlas", "1 km atlas", "100 m atlas", "10 m atlas"]
        for suffix in suffixes:
            if nameReplace.find(suffix) > -1:
                nameReplace = nameReplace[0:nameReplace.find(suffix)-1]

        #For each text item, replace the tokens, e.g. #name#, with corresponding text. 

        #Get all text items from the layout.
        #Item.scene() ensures that the item is being used (not deleted)
        textItems = [item for item in l.items() if type(item).__name__ == "QgsLayoutItemLabel" and item.scene()]

        #Save the original text item values so that they can be reset afterwards
        originalText=[]
        for textItem in textItems:
            #self.logMessage("storing label " + textItem.text())
            originalText.append(textItem.text())

        #Now replace the #name# tokens with the 'nameReplace' text derived from
        #the layer name - usually based on the taxon name.
        for textItem in textItems:
            textItem.setText(textItem.text().replace('#name#', nameReplace))
            l.refresh()

        #If TaxonMetaDataLayer has been set and checkbox set to use it, then set a filter to select
        #only the rows (should be only one) that match the current taxon (derived from layer name).
        #Then for each field in the TaxonMetaDataLayer, check to see if each of the fields in the
        #TaxaonMetaDataLayer has been used as a token in any checkboxes and, if so, replace the token
        #for the value of that field for the species at hand.
        if self.cbTaxonMetaData.isChecked() and self.mlcbTaxonMetaDataLayer.currentLayer() is not None:
            metaLayer = self.mlcbTaxonMetaDataLayer.currentLayer()
            #The regular expression (~ comparison) allows for leading and trailing white space on the taxa
            strFilter = '"%s" ~ \' *%s *\'' % ("Taxon", nameReplace)
            #self.logMessage("Taxon " + nameReplace)
            #self.logMessage("Filter " + strFilter)
            request = QgsFeatureRequest().setFilterExpression(strFilter)
            iField = 0
            for field in metaLayer.dataProvider().fields():
                #self.logMessage("Field " + field.name())
                strVal = ''
                iter = metaLayer.getFeatures(request)
                for feature in iter: #Should only be one (or zero) features
                    #self.logMessage("Feature found")
                    try:
                        strVal = str(feature.attributes()[iField]).strip()
                        if strVal == 'NULL':
                            strVal = ''
                    except:
                        strVal = ''
                        #e = sys.exc_info()[0]
                        #self.logMessage("Error: %s" % (e))
                for textItem in textItems:
                    if '#' + field.name() + '#' in textItem.text():
                        textItem.setText(textItem.text().replace('#' + field.name() + '#', strVal))
                l.refresh()
                iField += 1

        try:
            [item for item in l.items() if type(item).__name__ == "QgsLayoutItemMap"][0].setLayers(layers)

            le = QgsLayoutExporter(l)
            #self.logMessage(str(datetime.now().time()))
            format = self.cboOutputFormat.currentText()
            if format == "Composer image": 
                #Much slower than PDF generation for some reason
                s = QgsLayoutExporter.ImageExportSettings()
                le.exportToImage(imgFolder + os.path.sep + validName + ".png", s)
            else: #format == "Composer PDF":
                s = QgsLayoutExporter.PdfExportSettings()
                le.exportToPdf(imgFolder + os.path.sep + validName + ".pdf", s)
            #self.logMessage(str(datetime.now().time()))
        except:
            if not self.imageError:
                e = sys.exc_info()[0]
                self.iface.messageBar().pushMessage("Error", "Image generation error: %s" % (e), level=Qgis.Warning)
                self.imageError = True    
                
        #Reset the print composer's label items text to the original values
        iTextItem = 0
        for textItem in textItems:
            #self.logMessage("resetting labels " + originalText[iTextItem])
            textItem.setText(originalText[iTextItem])
            iTextItem += 1
        l.refresh()
            
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
    
class R6CredentialsDialog(QDialog):
    def __init__(self, initCredentials):
        super(R6CredentialsDialog, self).__init__()
        self.ui = Ui_R6Credentials()
        self.ui.setupUi(self)
        scriptDir = os.path.dirname(os.path.realpath(__file__))
        self.setWindowIcon(QtGui.QIcon(scriptDir + os.path.sep + 'images/R6.ico'))

        self.ui.bbDialogButtons.accepted.connect(self.okayed)
        self.ui.bbDialogButtons.rejected.connect(self.cancelled)
        self.ui.leR6Server.textChanged.connect(self.textChanged)
        self.ui.leR6User.textChanged.connect(self.textChanged)
        self.ui.leR6Password.textChanged.connect(self.textChanged)
        self.credentials = {"server": "", "user": "", "pword": ""}
        self.initialiseCredentials(initCredentials)
        self.okayed = False

    def initialiseCredentials(self, initCredentials):
        self.ui.leR6Server.setText(initCredentials["server"])
        self.ui.leR6User.setText(initCredentials["user"])
        self.ui.leR6Password.setText(initCredentials["pword"])
        self.textChanged()

    def textChanged(self):
        if self.ui.leR6Server.text().strip() and self.ui.leR6User.text().strip() and self.ui.leR6Password.text().strip():

            self.ui.bbDialogButtons.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.ui.bbDialogButtons.button(QDialogButtonBox.Ok).setEnabled(False)

    def okayed(self):
        self.setReturnValues(True)

    def cancelled(self):
        self.setReturnValues(False)

    def setReturnValues(self, okayed):
        self.okayed = okayed
        if okayed:
            self.credentials["server"] = self.ui.leR6Server.text()
            self.credentials["user"] = self.ui.leR6User.text()
            self.credentials["pword"] = self.ui.leR6Password.text()

class R6Dialog(QDialog):
    def __init__(self):
        super(R6Dialog, self).__init__()
        self.ui = Ui_R6()
        self.ui.setupUi(self)
        scriptDir = os.path.dirname(os.path.realpath(__file__))
        self.setWindowIcon(QtGui.QIcon(scriptDir + os.path.sep + 'images/R6.ico'))
        self.ui.leR6SpToMatch.setFocus()
        self.ui.butCancel.clicked.connect(self.cancel_dialog)
        self.ui.butR6Match.clicked.connect(self.R6Match)
        self.ui.butGetR6Data.clicked.connect(self.getR6Data)
        self.ui.lblBusy.setVisible(False)

        self.csvLayer = None
        self.message = None

        self.ui.lblBusy.setVisible(False)
        
    def R6Match(self):

        self.ui.leR6SpToMatch.setFocus()
        strSpeciesName = self.ui.leR6SpToMatch.text()
        if strSpeciesName == '':
            self.close()
            return
        self.ui.cmbSpToMap.setEnabled(True)
        self.ui.lbR6Select.setEnabled(True)

        strSpeciesName = str(re.sub(r'([^\s\w\-\']|_)+', '',
                                    strSpeciesName))  ##strip all non alphanumeric except spaces, - and ' from input
        strSpeciesName = strSpeciesName.replace("'", "''")## double up single quote if in species name
        args = "'%" + strSpeciesName + "%'"
        sql = (
                    " SELECT distinct TAXON.ITEM_NAME, NAMESERVER.RECOMMENDED_TAXON_VERSION_KEY, NAMESERVER.RECOMMENDED_TAXON_LIST_ITEM_KEY, TAXON_LIST.ITEM_NAME AS SourceList"
                    " FROM  NAMESERVER INNER JOIN"
                    " TAXON_VERSION ON NAMESERVER.INPUT_TAXON_VERSION_KEY = TAXON_VERSION.TAXON_VERSION_KEY INNER JOIN"
                    " TAXON ON TAXON_VERSION.TAXON_KEY = TAXON.TAXON_KEY INNER JOIN"
                    " TAXON_LIST_ITEM ON NAMESERVER.RECOMMENDED_TAXON_LIST_ITEM_KEY = TAXON_LIST_ITEM.TAXON_LIST_ITEM_KEY INNER JOIN"
                    " TAXON_LIST_VERSION ON TAXON_LIST_ITEM.TAXON_LIST_VERSION_KEY = TAXON_LIST_VERSION.TAXON_LIST_VERSION_KEY INNER JOIN"
                    " TAXON_LIST ON TAXON_LIST_VERSION.TAXON_LIST_KEY = TAXON_LIST.TAXON_LIST_KEY"
                    " WHERE (TAXON.ITEM_NAME LIKE %s);" % args
                    )
        query = QtSql.QSqlQuery(sql)
        list1 = []
        self.list2=[]
        while query.next():
            list1.append(query.value(0) + query.value(3))
            self.list2.append(query.value(2))  # 2=TLIK,1=TVK

        if len(list1) == 0:
            list1 = ["No Match"]
            self.list2 = ["No Match"]
        else:
            self.ui.cbIncSpBelow.setEnabled(True)
            self.ui.butGetR6Data.setEnabled(True)

        self.ui.cmbSpToMap.clear()
        self.ui.cmbSpToMap.addItems(list1)

    #@pyqtSlot()
    def getR6Data(self):

        self.ui.lblBusy.setVisible(True)
        qApp.processEvents() 

        index = self.ui.cmbSpToMap.currentIndex()
        tlik = "'"+str(self.list2[index])+"'"
        justtaxon = "'1'"

        if self.ui.cbIncSpBelow.isChecked():
            justtaxon = "'2'"
        sql = ("set nocount on; DECLARE @TKey1 varchar(16)={0}; "
               "DECLARE @TKey varchar(16); "
                "DECLARE @choice varchar(1)={1}; "
               "SET @TKey=(SELECT TAXON_VERSION_KEY FROM TAXON_LIST_ITEM where Taxon_List_Item_Key=@TKey1); "
               "CREATE TABLE #TaxaList(Taxon_Version_Key CHAR(16) COLLATE Database_Default PRIMARY KEY); "
               "CREATE TABLE #TLIK (TLIK CHAR(16) COLLATE Database_Default PRIMARY KEY); "
               "IF @choice='2' "
               "INSERT INTO #TLIK VALUES (@TKey1) "
               "WHILE @choice=2 BEGIN "
               "INSERT INTO #TLIK "
               "SELECT T.Preferred_name "
               "FROM TAXON_LIST_ITEM T "
               "INNER JOIN #TLIK Tinc on T.Parent=TInc.TLIK "
               "LEFT JOIN #TLIK Texc ON Texc.TLIK=T.Preferred_name "
               "WHERE Texc.TLIK IS NULL "
               "IF @@ROWCOUNT=0 "
               "BREAK "
               "END "
               "IF @choice='2' "
               "insert into #TaxaList (Taxon_Version_Key) "
               "SELECT TAXON_LIST_ITEM.TAXON_VERSION_KEY "
               "FROM TAXON_LIST_ITEM INNER JOIN "
               "[#TLIK] ON TAXON_LIST_ITEM.TAXON_LIST_ITEM_KEY = [#TLIK].TLIK "
               "ELSE "
               "INSERT INTO #TaxaList VALUES (@TKey) "
               "SELECT DISTINCT [#TaxaList].Taxon_Version_Key, NAMESERVER.RECOMMENDED_TAXON_VERSION_KEY "
               "INTO [#TaxaListPN] "
               "FROM NAMESERVER INNER JOIN "
               "[#TaxaList] ON NAMESERVER.INPUT_TAXON_VERSION_KEY = [#TaxaList].Taxon_Version_Key "
               "SELECT DISTINCT "
               "INDEX_TAXON_NAME_1.COMMON_NAME AS CommonName, INDEX_TAXON_NAME_1.PREFERRED_NAME AS ScientificName, TAXON_GROUP.TAXON_GROUP_NAME AS TaxonGroup, isnull(LOCATION.FILE_CODE,'') AS FileCode, isnull(LOCATION_NAME.ITEM_NAME,'') AS SampleLocation, isnull(SAMPLE.LOCATION_NAME,'') AS LocationName, dbo.LCReturnVagueDateShort(SAMPLE.VAGUE_DATE_START, SAMPLE.VAGUE_DATE_END, SAMPLE.VAGUE_DATE_TYPE) AS RecDate, "
               "SAMPLE.SPATIAL_REF AS GridRef, isnull(SAMPLE_TYPE.SHORT_NAME,'') AS RecMethod, isnull(RECORD_TYPE.SHORT_NAME,'') AS RecType, isnull(dbo.LCFormatAbundanceData(TAXON_OCCURRENCE.TAXON_OCCURRENCE_KEY),'') AS Abundance, TAXON_OCCURRENCE.CONFIDENTIAL AS Confid, TAXON_OCCURRENCE.TAXON_OCCURRENCE_KEY AS TaxOcc,  TAXON_LIST_ITEM_1.TAXON_VERSION_KEY AS TVK, dbo.LCReturnDate(dbo.SAMPLE.VAGUE_DATE_END, dbo.SAMPLE.VAGUE_DATE_TYPE, 'Y') AS RecYear, "
                "dbo.LCReturnDate(SAMPLE.VAGUE_DATE_START, 'D', 'F') as StartDate, dbo.LCReturnDate(SAMPLE.VAGUE_DATE_END, 'D', 'F') as EndDate, SAMPLE.VAGUE_DATE_TYPE as DateType "
               "FROM TAXON_VERSION INNER JOIN "
               "SAMPLE_TYPE INNER JOIN "
               "SAMPLE LEFT OUTER JOIN "
               "LOCATION_NAME ON SAMPLE.LOCATION_KEY = LOCATION_NAME.LOCATION_KEY ON SAMPLE_TYPE.SAMPLE_TYPE_KEY = SAMPLE.SAMPLE_TYPE_KEY INNER JOIN "
               "TAXON_OCCURRENCE ON SAMPLE.SAMPLE_KEY = TAXON_OCCURRENCE.SAMPLE_KEY INNER JOIN "
               "TAXON_DETERMINATION INNER JOIN "
               "INDEX_TAXON_NAME ON TAXON_DETERMINATION.TAXON_LIST_ITEM_KEY = INDEX_TAXON_NAME.TAXON_LIST_ITEM_KEY ON TAXON_OCCURRENCE.TAXON_OCCURRENCE_KEY = TAXON_DETERMINATION.TAXON_OCCURRENCE_KEY INNER JOIN "
               "SURVEY_EVENT ON SAMPLE.SURVEY_EVENT_KEY = SURVEY_EVENT.SURVEY_EVENT_KEY INNER JOIN "
               "SURVEY ON SURVEY_EVENT.SURVEY_KEY = SURVEY.SURVEY_KEY INNER JOIN "
               "RECORD_TYPE ON TAXON_OCCURRENCE.RECORD_TYPE_KEY = RECORD_TYPE.RECORD_TYPE_KEY INNER JOIN "
               "TAXON_LIST_ITEM ON TAXON_DETERMINATION.TAXON_LIST_ITEM_KEY = TAXON_LIST_ITEM.TAXON_LIST_ITEM_KEY ON TAXON_VERSION.TAXON_VERSION_KEY = TAXON_LIST_ITEM.TAXON_VERSION_KEY INNER JOIN "
               "INDEX_TAXON_NAME AS INDEX_TAXON_NAME_1 ON INDEX_TAXON_NAME.RECOMMENDED_TAXON_LIST_ITEM_KEY = INDEX_TAXON_NAME_1.TAXON_LIST_ITEM_KEY INNER JOIN "
               "TAXON_LIST_ITEM AS TAXON_LIST_ITEM_1 ON INDEX_TAXON_NAME_1.RECOMMENDED_TAXON_LIST_ITEM_KEY = TAXON_LIST_ITEM_1.TAXON_LIST_ITEM_KEY INNER JOIN "
               "[#TaxaListPN] ON TAXON_LIST_ITEM_1.TAXON_VERSION_KEY = [#TaxaListPN].Taxon_Version_Key LEFT OUTER JOIN "
               "DETERMINATION_TYPE ON TAXON_DETERMINATION.DETERMINATION_TYPE_KEY = DETERMINATION_TYPE.DETERMINATION_TYPE_KEY LEFT OUTER JOIN "
               "LOCATION ON SAMPLE.LOCATION_KEY = LOCATION.LOCATION_KEY LEFT OUTER JOIN "
               "TAXON_GROUP ON TAXON_VERSION.OUTPUT_GROUP_KEY = TAXON_GROUP.TAXON_GROUP_KEY "
               "WHERE (TAXON_OCCURRENCE.ZERO_ABUNDANCE = 0) AND (TAXON_OCCURRENCE.VERIFIED <> 1) AND (TAXON_DETERMINATION.PREFERRED = 1) AND "
               "(LOCATION_NAME.PREFERRED = 1 OR LOCATION_NAME.PREFERRED IS NULL) AND "
               "(DETERMINATION_TYPE.SHORT_NAME <> 'Considered Incorrect') AND (DETERMINATION_TYPE.SHORT_NAME <> 'Incorrect') "
               "AND (DETERMINATION_TYPE.SHORT_NAME <> 'Invalid') AND "
               "(DETERMINATION_TYPE.SHORT_NAME <> 'Requires Confirmation')".format(tlik,justtaxon)
               )
        query = QtSql.QSqlQuery(sql)
        colcount = query.record().count()
        exportQSqlQueryModel = QtSql.QSqlQueryModel()
        exportQSqlQueryModel.setQuery(query)
        column_names = []
        #print(exportQSqlQueryModel.rowCount(), 'here')

        for column in range(exportQSqlQueryModel.columnCount()):
            column_names.append(str(exportQSqlQueryModel.headerData(column, QtCore.Qt.Horizontal)))
        #print(column_names)
        
        list_of_rows = []
        while query.next():
            list_of_cells = []
            i = 0
            while i <= colcount:
                list_of_cells.append(query.value(i))
                i += 1
            list_of_rows.append(list_of_cells)

        if len(list_of_rows) > 0:
            #Create CSV memory layer
            csvMemoryLayer = QgsVectorLayer('None', 'R6 ' + self.ui.cmbSpToMap.currentText(), 'memory')
            QgsProject.instance().addMapLayer(csvMemoryLayer)
            dataProvider = csvMemoryLayer.dataProvider()
            
            csvMemoryLayer.startEditing()
            for x in range(colcount):
                if query.record().field(x).type() == 10:
                    dataProvider.addAttributes([QgsField(query.record().fieldName(x), QVariant.String)])
                else: #==3
                    dataProvider.addAttributes([QgsField(query.record().fieldName(x), QVariant.Int)])
            csvMemoryLayer.commitChanges()

            ##Create CSV file.
            #homepath = os.path.expanduser('~')
            #fileName = QFileDialog.getSaveFileName(self, "Save file", homepath, "CSV files (*.csv)|*.csv")
            #try:
            #    out_file = open(fileName[0], 'w',newline='')
            #except:
            #    self.close()
            #    return
            #writer = csv.writer(out_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            #writer.writerow(column_names)

            fets=[] #Array to store features added to CSV memory layer
            for x in list_of_rows:
                #writer.writerow(x)
                fet = QgsFeature()
                fet.setAttributes(x[:-1]) #For some reason row x has an extra value of None at the end so trim this off (otherwise feature addition fails)
                fets.append(fet)

            #out_file.close()
            csvMemoryLayer.startEditing()
            csvMemoryLayer.addFeatures(fets)
            csvMemoryLayer.commitChanges()

            self.csvLayer = csvMemoryLayer
        else:
            self.message = "No records in R6 for that species"

        self.accept()

    def cancel_dialog(self):
        self.reject()