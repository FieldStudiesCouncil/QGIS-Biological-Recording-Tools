# -*- coding: utf-8 -*-
"""
/***************************************************************************
MapmashupDialog
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

from . import ui_mapmashup
import os.path
import glob
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from . import envmanager
from shutil import *
from . import dropImageLineEdit
import tempfile

#from PIL import *

class MapmashupDialog(QWidget, ui_mapmashup.Ui_Mapmashup):
    def __init__(self, iface, dockwidget):
        QWidget.__init__(self)
        ui_mapmashup.Ui_Mapmashup.__init__(self)
        self.setupUi(self)
        self.canvas = iface.mapCanvas()
        self.iface = iface
    
        self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
        
        self.butLoadImage.clicked.connect(self.fromClipboard)
        self.butLoadImageFile.clicked.connect(self.loadImageFile)
        self.butLoadImageBrowse.clicked.connect(self.loadImageFileBrowse)
        self.butBrowseImg.clicked.connect(self.BrowseImageFolder)
        self.butBrowseReg.clicked.connect(self.BrowseRegistrationFolder)
        self.leRegistrationFolder.textChanged.connect(self.listRegistrations)
        self.butRefresh.clicked.connect(self.listRegistrations)
        self.butClearLast.clicked.connect(self.removeMap)
        self.butClear.clicked.connect(self.removeMaps)
        self.pbBrowseStyleFile.clicked.connect(self.browseStyleFile)
        self.butHelp.clicked.connect(self.helpFile)
        self.butGithub.clicked.connect(self.github)
        
        #http://stackoverflow.com/questions/20834064/how-to-create-qpixmap-with-dragimagebits-from-my-browser
        #Replace the leImageFolder line edit with the custom one that handles image drops
        self.hlImageFolder.removeWidget(self.leImageFolder)
        self.hlImageFolder.removeWidget(self.butBrowseImg)
        self.leImageFolder.close()
        self.leImageFolder = dropImageLineEdit.DragLineEdit(self)
        self.hlImageFolder.addWidget(self.leImageFolder)
        self.hlImageFolder.addWidget(self.butBrowseImg)
        self.hlImageFolder.update()
        self.leImageFolder.imageDropped.connect(self.mapImageDropped)
      
        # Load the environment stuff
        self.env = envmanager.envManager()
        
        # Inits
        self.layers = []
        self.tempFiles = []
        self.butLoadImage.setIcon(QIcon( self.pathPlugin % "images/mashup.png" ))
        self.butLoadImageFile.setIcon(QIcon( self.pathPlugin % "images/mashup2.png" ))
        self.butLoadImageBrowse.setIcon(QIcon( self.pathPlugin % "images/mashup3.png" ))
        self.butClearLast.setIcon(QIcon( self.pathPlugin % "images/removelayer.png" ))
        self.butClear.setIcon(QIcon( self.pathPlugin % "images/removelayers.png" ))
        self.butHelp.setIcon(QIcon( self.pathPlugin % "images/info.png" ))
        self.butGithub.setIcon(QIcon( self.pathPlugin % "images/github.png" ))
    
    def helpFile(self):
        QDesktopServices().openUrl(QUrl("http://www.fscbiodiversity.uk/qgismashuptool"))

    def github(self):
        QDesktopServices().openUrl(QUrl("https://github.com/burkmarr/QGIS-Biological-Recording-Tools/issues"))
        
    def showEvent(self, ev):
        # Load the environment stuff
        self.env = envmanager.envManager()
        self.leImageFolder.setText(self.env.getEnvValue("mapmashup.imgfolder"))
        self.leRegistrationFolder.setText(self.env.getEnvValue("mapmashup.regfolder"))
        return QWidget.showEvent(self, ev)    
        
    def _glob(self, path, *exts):
        """
        Glob for multiple file extensions
    
        Parameters
        ----------
        path : str
            A file name without extension, or directory name
        exts : tuple
            File extensions to glob for
    
        Returns
        -------
        files : list
            list of files matching extensions in exts in path
    
        """
        path = os.path.join(path, "*") if os.path.isdir(path) else path + "*"
        return [f for files in [glob.glob(path + ext) for ext in exts] for f in files]
    
    def browseStyleFile(self):
    
        #Reload env
        self.env.loadEnvironment()
        
        if os.path.exists(self.env.getEnvValue("mapmashup.stylefilefolder")):
            strInitPath = self.env.getEnvValue("mapmashup.stylefilefolder")
        else:
            strInitPath = ""
            
        dlg = QFileDialog
        fileName = dlg.getOpenFileName(self, "Browse for style file", strInitPath, "QML Style Files (*.qml)")[0]
        if fileName:
            self.leStyleFile.setText(fileName)
            self.leStyleFile.setToolTip(fileName)
                
    def mapImageDropped(self, image):
        #image is a QtGui.QImage object
        self.loadImage(image)
        
    def loadImageFile(self):
        self.loadImage()
        
    def loadImageFileBrowse(self):
    
        #Reload env
        self.env.loadEnvironment()
        
        dirImages = self.leImageFolder.text()
        #Check if image folder exists
        if not os.path.isdir(dirImages):
            dirImages = ""
    
        dlg = QFileDialog
        fileName = dlg.getOpenFileName(self, "Browse for image file", dirImages, "All Files (*.*)")[0]
        if fileName:
            self.loadImage(None, fileName)
        
    def loadImage(self, image=None, imageFile=None):
   
        #Is a registration file selected?
        if self.cboRegistrations.count() == 0:
            self.iface.messageBar().pushMessage("Info", "No registration file selected.", level=Qgis.Info)
            return
            
        dirImages = self.leImageFolder.text()
        #Check if image folder exists
        if not os.path.isdir(dirImages):
            self.iface.messageBar().pushMessage("Info", "The specified image folder - '" + dirImages + "' - cannot be found.", level=Qgis.Info)
            return
    
        #Create temporary image filename 
        f = tempfile.NamedTemporaryFile(dir=dirImages)
        imageTemp = f.name + ".png"
        f.close()
            
        if not image is None:
            # Copy clipboard image to temp file
            image.save(imageTemp)
        elif not imageFile is None:
            # Copy the passed image to temp file
            copyfile(imageFile, imageTemp)
        else:
            # Get most recent image in image folder and copy to temp file
            imageFiles = self._glob(dirImages, ".gif", ".png", "jpg", ".tif", ".bmp", "jpeg", ".tiff")
            if len(imageFiles) == 0:
                self.iface.messageBar().pushMessage("Info", "No images found in folder '" + dirImages + "'.", level=Qgis.Info)
                return
                
            recentImage = max(imageFiles, key=os.path.getmtime)
            if recentImage == "":
                return
            copyfile(recentImage, imageTemp)
        
        # Copy the wld file to image folder and give it the same name as the image
        regFileOut = imageTemp[:-4] + ".wld"
        regFile = os.path.join(self.leRegistrationFolder.text() , self.cboRegistrations.currentText() + ".wld")
        copyfile(regFile, regFileOut)
        
        # Load the raster
        if self.leName.text() != "":
            layerName = self.leName.text() + " " + self.cboRegistrations.currentText()
        else:
            layerName = self.cboRegistrations.currentText()
            
        rlayer = QgsRasterLayer(imageTemp, layerName)
        
        # General transparency
        opacity = (100-self.hsTransparency.value()) * 0.01
        rlayer.renderer().setOpacity(opacity)
        
        # Pixel transparency
        if self.cbTransparentColour.isChecked():
            #color = self.butTransparentColour.palette().color(QPalette.Background)
            color = self.mcbTransparentColour.color()
            rlayer.renderer().rasterTransparency().initializeTransparentPixelList(color.red(), color.green(), color.blue())

        # Style file
        styleFile = None
        if self.cbApplyStyle.isChecked():
            if os.path.exists( self.leStyleFile.text()):
                styleFile = self.leStyleFile.text()
                rlayer.loadNamedStyle(self.leStyleFile.text())
         
        # Add to map
        regLayer = QgsProject.instance().addMapLayer(rlayer)
        
        # Store ID and temp file
        self.layers.append(rlayer.id())
        self.tempFiles.append(imageTemp)

    def BrowseImageFolder(self):
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.Directory)
        dlg.setOption(QFileDialog.ShowDirsOnly, True)
        if os.path.exists(self.env.getEnvValue("mapmashup.imgfolder")):
            dlg.setDirectory(self.env.getEnvValue("mapmashup.imgfolder"))      
        folderName = dlg.exec_()
        if folderName:
            for folderImage in dlg.selectedFiles():
                self.leImageFolder.setText(folderImage)
                break
            
    def BrowseRegistrationFolder(self):
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.Directory)
        dlg.setOption(QFileDialog.ShowDirsOnly, True)
        if os.path.exists(self.env.getEnvValue("mapmashup.regfolder")):
            dlg.setDirectory(self.env.getEnvValue("mapmashup.regfolder"))     
            
        folderName = dlg.exec_()
        if folderName:
            for folderImage in dlg.selectedFiles():
                self.leRegistrationFolder.setText(folderImage)
                break
        
    def listRegistrations(self):
        
        dirReg = self.leRegistrationFolder.text() + "/*.wld"
        self.cboRegistrations.clear()
        for fileReg in glob.glob(dirReg):
            self.cboRegistrations.addItem(os.path.basename(fileReg)[:-4])
            
    def removeMap(self):
        if len(self.layers) > 0:
            layerID = self.layers[-1]
            try:
                QgsProject.instance().removeMapLayer(layerID)
            except:
                pass
            self.layers = self.layers[:-1]
            
            tempPng = self.tempFiles[-1]
            tempWld = tempPng[:-4] + ".wld"
            try:
                os.remove(tempPng)
            except:
                #self.iface.messageBar().pushMessage("Warning", "Can't delete " + tmpPng, level=Qgis.Warning)
                pass
            try:
                os.remove(tempWld)
            except:
                pass
            self.tempFiles = self.tempFiles[:-1]
            self.canvas.refresh()
            
    def removeMaps(self):
        for layerID in self.layers:
            try:
                QgsProject.instance().removeMapLayer(layerID)
            except:
                pass
        self.layers = []
        
        for tempPng in self.tempFiles:
            tempWld = tempPng[:-4] + ".wld"
            try:
                os.remove(tempPng)
            except:
                #self.iface.messageBar().pushMessage("Warning", "Can't delete " + tmpPng, level=Qgis.Warning)
                pass
            try:
                os.remove(tempWld)
            except:
                pass
        self.tempFiles = []
        self.canvas.refresh()
    
    def fromClipboard(self):
      
        try:
            img = QApplication.clipboard().image()
        except:
            img = None
            
        if img.isNull():
            self.iface.messageBar().pushMessage("Info", "No image in clipboard", level=Qgis.Info)
            return
           
        self.loadImage(img)
        