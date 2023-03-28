# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OsgrDialog
                                 A QGIS plugin
 OS grid reference tools
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
from . import ui_osgr
import os.path
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from . import osgr
from . import osgrLayer
from . import drag_box_tool
import re

class OsgrDialog(QWidget, ui_osgr.Ui_osgr):
    
  def __init__(self, iface, dockwidget):
    QWidget.__init__(self)
    ui_osgr.Ui_osgr.__init__(self)
    self.setupUi(self)
    self.canvas = iface.mapCanvas()
    self.iface = iface

    # Get a reference to an osgr object and an osgrLayer object
    self.osgr = osgr.osgr()
    self.osgrLayer = osgrLayer.osgrLayer(iface)
      
    # Set the button graphics
    self.pathPlugin = "%s%s%%s" % ( os.path.dirname( __file__ ), os.path.sep )
    self.butGridTool.setIcon(QIcon( self.pathPlugin % "images/osgr.png" ))
    self.butGridPoly.setIcon(QIcon( self.pathPlugin % "images/osgrPoly.png" ))
    self.butPaste.setIcon(QIcon( self.pathPlugin % "images/osgrPaste.png" ))
    self.butClear.setIcon(QIcon( self.pathPlugin % "images/cross.png" ))
    self.butHelp.setIcon(QIcon( self.pathPlugin % "images/info.png" ))
    self.butGithub.setIcon(QIcon( self.pathPlugin % "images/github.png" ))
    
    # Connect the controls to their events
    self.cbGROnClick.clicked.connect(self.cbGROnClickClicked)
    self.cbGRShowSquare.clicked.connect(self.cbGRShowSquareClicked)
    self.cbGRShowPoint.clicked.connect(self.cbGRShowPointClicked)
    self.cboPrecision.currentIndexChanged.connect(self.cboPrecisionChanged)
    self.butZoom.clicked.connect(self.butZoomClicked)
    self.butPan.clicked.connect(self.butPanClicked)
    self.butGridTool.clicked.connect(self.butGridToolClicked)
    self.butGridPoly.clicked.connect(self.GridPoly)
    self.butClear.clicked.connect(self.ClearGrid)
    self.cbLabel.clicked.connect(self.LabelChecked)
    self.butCancel.clicked.connect(self.cancelGrid)
    self.dsbGridSize.valueChanged.connect(self.setPrecision)
    self.butHelp.clicked.connect(self.helpFile)
    self.butGithub.clicked.connect(self.github)
    self.rbOutCrsBritish.toggled.connect(self.cboPrecisionChanged)
    self.rbOutCrsIrish.toggled.connect(self.cboPrecisionChanged)
    self.rbOutCrsOther.toggled.connect(self.cboPrecisionChanged)
    self.leOSGR.returnPressed.connect(self.butZoomClicked)
    self.butPaste.clicked.connect(self.butPasteClicked)
    
    # Handle canvas events
    self.canvas.mapToolSet.connect(self.mapToolClicked)
    self.canvas.xyCoordinates.connect(self.canvasMouseMove)
    
    # Handle events from the osgrLayer object
    self.osgrLayer.progChange.connect(self.setProgBarValue)
    self.osgrLayer.progMax.connect(self.setProgBarMax)
    self.osgrLayer.gridComplete.connect(self.gridControlsEnable)
    
    # Create the GR click tool based on a QgsMapToolEmitPoint tool
    self.clickTool = QgsMapToolEmitPoint(self.canvas)
    self.clickTool.canvasClicked.connect(self.canvasClicked)
    
    # Create the grid square drag tool based on a custom rectangle tool
    self.dragTool = drag_box_tool.RectangleMapTool(self.canvas, self.iface)
    self.dragTool.boxDragged.connect(self.boxDragged)
    
    # Initialisations
    self.easting = 0
    self.northing = 0
    self.LabelChecked()
    self.grPrecision = 0
    self.grType = "os"
    self.cboPrecisionChanged(0)
    
  def helpFile(self):
        QDesktopServices().openUrl(QUrl("http://www.fscbiodiversity.uk/qgisosgrtool"))

  def github(self):
        QDesktopServices().openUrl(QUrl("https://github.com/FieldStudiesCouncil/QGIS-Biological-Recording-Tools/issues"))
        
  def infoMessage(self, strMessage):
    self.iface.messageBar().pushMessage("Info", strMessage, level=Qgis.Info)

  def warningMessage(self, strMessage):
    self.iface.messageBar().pushMessage("Warning", strMessage, level=Qgis.Warning)

  def logMessage(self, strMessage, level=Qgis.Info):
    QgsMessageLog.logMessage(strMessage, "OSGR Tool", level)
 
  def gridControlsEnable(self):
    self.gridControlsEnableDisable(True)
    
  def gridControlsEnableDisable(self, bool):
    self.butGridPoly.setEnabled(bool)
    self.butGridTool.setEnabled(bool)
    self.butClear.setEnabled(bool)
    self.cbLabel.setEnabled(bool)
    
  def setPrecision(self, value):
    self.precision = value
    self.grPrecision = value
    self.osgrLayer.setPrecision(value)
    self.osgrLayer.setPrecisionText(self.cboPrecision.currentText())
    
  def isUserDefinedGrid(self):
    return (self.dsbGridSize.value() > 0)
  
  def setProgBarValue(self, value):
    self.pbGridSquares.setValue(value)
    
  def setProgBarMax(self, value):
    self.pbGridSquares.setMaximum(value)
  
  def cancelGrid(self):
    self.osgrLayer.cancelGrid()
    
  def LabelChecked(self):
    self.osgrLayer.setShowLabels(self.cbLabel.isChecked())
    
  def ClearGrid(self):
    self.osgrLayer.clear()
    self.canvas.refresh()

  def butGridToolClicked(self, pos):
    # Make the GR tool the current map tool
    if self.butGridTool.isChecked():
      self.canvas.setMapTool(self.dragTool)
    else:
      self.canvas.unsetMapTool(self.dragTool)
      
  def boxDragged(self):
    #The bounds passed into this function are in map projection units - so first thing to do is to convert
    #These to British or Irish grid if one of these selected.
    if self.rbOutCrsBritish.isChecked() and self.canvas.mapSettings().destinationCrs().authid() != "EPSG:27700":
        transGrid = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), QgsCoordinateReferenceSystem("EPSG:27700"), QgsProject.instance())
    elif self.rbOutCrsIrish.isChecked() and self.canvas.mapSettings().destinationCrs().authid() != "EPSG:29903":
        transGrid = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), QgsCoordinateReferenceSystem("EPSG:29903"), QgsProject.instance())
    else:
        transGrid = None

    if transGrid is None:
        xMin = self.dragTool.xMinimum
        yMin = self.dragTool.yMinimum
        xMax = self.dragTool.xMaximum
        yMax = self.dragTool.yMaximum
    else:
        point = QgsPointXY(float(self.dragTool.xMinimum), float(self.dragTool.yMinimum))
        gridPoint = transGrid.transform(point)
        xMin = gridPoint.x()
        yMin = gridPoint.y()
        point = QgsPointXY(float(self.dragTool.xMaximum), float(self.dragTool.yMaximum))
        gridPoint = transGrid.transform(point)
        xMax = gridPoint.x()
        yMax = gridPoint.y()

    self.GenerateSquares(xMin, yMin, xMax, yMax)
    
  def GridPoly(self):
  
    layer = self.iface.activeLayer()

    if layer is None:
        self.iface.messageBar().pushMessage("Info", "No active layer is in layers panel.", level=Qgis.Info)
        return

    if layer.type() == QgsMapLayer.VectorLayer:
        selectedFeatures = layer.selectedFeatures()
        
        if len(selectedFeatures) > 0:

            if self.grType == "os" and layer.crs().authid() != "EPSG:27700":
                trans = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem("EPSG:27700"), QgsProject.instance())
            elif self.grType == "irish" and layer.crs().authid() != "EPSG:29903":
                trans = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem("EPSG:29903"), QgsProject.instance())
            elif self.grType == "other" and layer.crs().authid() != self.canvas.mapSettings().destinationCrs().authid():
                trans = QgsCoordinateTransform(layer.crs(), self.canvas.mapSettings().destinationCrs(), QgsProject.instance())
            else:
                trans = None

            minx = None
            max = None
            miny = None
            maxy = None

            selectedGeometries = []
            for ftrSelected in selectedFeatures:
                geom = ftrSelected.geometry()
                if not trans is None:
                    geom.transform(trans)
                selectedGeometries.append(geom)
                bbox = geom.boundingBox()
                if minx is None:
                    minx = bbox.xMinimum()
                    miny = bbox.yMinimum()
                    maxx = bbox.xMaximum()
                    maxy = bbox.yMaximum()
                else:
                    if bbox.xMinimum() < minx:
                        minx = bbox.xMinimum()
                    if bbox.yMinimum() < miny:
                        miny = bbox.yMinimum()
                    if bbox.xMaximum() > maxx:
                        maxx = bbox.xMaximum()
                    if bbox.yMaximum() > maxy:
                        maxy = bbox.yMaximum()

            self.GenerateSquares(minx, miny, maxx, maxy, selectedGeometries, self.iface.activeLayer().crs())
        else:
            self.iface.messageBar().pushMessage("Info", "There are no features selected in the active layer.", level=Qgis.Info)
    else:
        self.iface.messageBar().pushMessage("Info", "The active layer is not a vector layer.", level=Qgis.Info)
    
  def GenerateSquares(self, xMin, yMin, xMax, yMax, selectedGeometries=[], selectedFeaturesCrs=None):

    #The bounds passed into this function should be expressed in the CRS of grid type - British, Irish or other (map canvas) 
    if selectedFeaturesCrs is not None:
        crsAuthId = selectedFeaturesCrs.authid()
    else:
        crsAuthId = "none"
    self.logMessage(str(xMin) + " " +  str(yMin)+ " " +  str(xMax)+ " " +  str(yMax)+ " " +  str(len(selectedGeometries))+ " " +  crsAuthId)

    if self.precision == 0:
        self.infoMessage("Grid size must be greater than zero")
        return

    llx = (xMin // self.precision) * self.precision
    lly = (yMin // self.precision) * self.precision
    
    iSquares = (((xMax - llx) // self.precision + 1) * ((yMax - lly) // self.precision + 1))
    if iSquares > 1000:

        if self.rbOutCrsOther.isChecked():
            precisionText = str(self.dsbGridSize.value())
        else:
            precisionText = self.cboPrecision.currentText()

        ret = QMessageBox.warning(self, "Warning",
                "Large area specified relative to the precision (" + precisionText + "). This could generate up to " + str(int(iSquares)) + " grid squares which could take some time. Do you want to continue? (You can interrupt with the Cancel button.)",
                QMessageBox.Ok, QMessageBox.Cancel)
        if ret == QMessageBox.Cancel:
            return
    self.gridControlsEnableDisable(False)
    
    self.osgrLayer.GenerateSquares(xMin, yMin, xMax, yMax, selectedGeometries, selectedFeaturesCrs)

  def butPasteClicked(self):
      try:
        txt = QApplication.clipboard().text()
      except:
        txt = ""

      #Replace any non alphanumeric characters with a space
      txt = re.sub('[^0-9a-zA-Z]+', ' ', txt)

      #Split on white space
      grs = txt.split()
      self.logMessage(str(grs))
      self.osgrLayer.GenerateSquaresFromArray(grs)
      
  def butZoomClicked(self):
      self.locateOnGR(True)

  def butPanClicked(self):
      self.locateOnGR(False)

  def locateOnGR(self, zoom):

    res = self.osgr.enFromGR(self.leOSGR.text())
    
    if res[0] == 0:
        self.iface.messageBar().pushMessage("Warning", res[3], level=Qgis.Warning)
    else:
        precision = res[2]
        x0 = (res[0] - precision / 1.8)
        x1 = (res[0] + precision / 1.8)
        y0 = (res[1] - precision / 1.8)
        y1 = (res[1] + precision / 1.8)
        
        ll = QgsPointXY(x0, y0)
        ur = QgsPointXY(x1, y1)
        rect = QgsRectangle(ll, ur)
        centre = QgsPointXY(res[0], res[1])

        # Transform geometry if map canvas CRS doesn't match GR
        if self.rbOutCrsBritish.isChecked() and self.canvas.mapSettings().destinationCrs().authid() != "EPSG:27700":
            trans = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:27700"), self.canvas.mapSettings().destinationCrs(), QgsProject.instance())
        elif self.rbOutCrsIrish.isChecked() and self.canvas.mapSettings().destinationCrs().authid() != "EPSG:29903":
            trans = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:29903"), self.canvas.mapSettings().destinationCrs(), QgsProject.instance())
        else:
            trans = None

        if trans is not None:
            rect = trans.transformBoundingBox(rect)
        
        setzoom = self.iface.mapCanvas().scale()
        self.canvas.setExtent(rect)
        if not zoom:
            self.iface.mapCanvas().zoomScale(setzoom)
        self.canvas.refresh()
        
        if precision == 1:
            self.cboPrecision.setCurrentIndex(0)
        elif precision == 10:
            self.cboPrecision.setCurrentIndex(1)
        elif precision == 100:
            self.cboPrecision.setCurrentIndex(2)
        elif precision == 1000:
            self.cboPrecision.setCurrentIndex(3)
        elif precision == 2000:
            self.cboPrecision.setCurrentIndex(4)
        elif precision == 5000:
            self.cboPrecision.setCurrentIndex(5)
        elif precision == 10000:
            self.cboPrecision.setCurrentIndex(6)
        elif precision == 100000:
            self.cboPrecision.setCurrentIndex(7)
            
        self.displayOSGR(centre)
   
  def cboPrecisionChanged(self, int):
    # Set precision and colour for grid square
    if self.rbOutCrsBritish.isChecked() or self.rbOutCrsIrish.isChecked():
        if self.cboPrecision.currentIndex() == 0:
            precision = 1
            self.grColour = QColor(0,0,0)
        elif self.cboPrecision.currentIndex() == 1:
            precision = 10
            self.grColour = QColor(255,0,255)
        elif self.cboPrecision.currentIndex() == 2:
            precision = 100
            self.grColour = QColor(255,0,0)
        elif self.cboPrecision.currentIndex() == 3:
            precision = 1000
            self.grColour = QColor(0,255,255)
        elif self.cboPrecision.currentIndex() == 4:
            precision = 2000
            self.grColour = QColor(0,255,0)
        elif self.cboPrecision.currentIndex() == 5:
            precision = 5000
            self.grColour = QColor(255,255,0)
        elif self.cboPrecision.currentIndex() == 6:
            precision = 10000
            self.grColour = QColor(128,128,218)
        elif self.cboPrecision.currentIndex() == 7:
            precision = 100000
            self.grColour = QColor(0,0,255)

        if self.rbOutCrsBritish.isChecked():
            self.grType = "os"
        elif self.rbOutCrsIrish.isChecked():
            self.grType = "irish"

        self.cboPrecision.setEnabled(True)
        self.dsbGridSize.setEnabled(False)
        self.dsbGridSize.setValue(0)

    elif self.rbOutCrsOther.isChecked():
        precision = self.dsbGridSize.value()
        self.grColour = QColor(255,0,255)
        self.grType = "other"
        self.cboPrecision.setEnabled(False)
        self.dsbGridSize.setEnabled(True)
    
    self.osgrLayer.setGrType(self.grType)
    self.setPrecision(precision)
    self.displayOSGR(QgsPoint(self.easting,self.northing))

  def cbGROnClickClicked(self):
    # Make the GR tool the current map tool
    self.canvas.setMapTool(self.clickTool)
    self.clearMapGraphics(True, True)
    
  def cbGRShowSquareClicked(self):
    self.clearMapGraphics(True, False)

  def cbGRShowPointClicked(self):
    self.clearMapGraphics(False, True)
   
  def clearMapGraphics(self, bSquare, bPoint):
    # Delete any rubberband graphics
    if bSquare:
        try:
            self.canvas.scene().removeItem(self.rbGridSquare)
        except:
            pass

    if bPoint:
        try:
            self.canvas.scene().removeItem(self.rbGridPoint)
        except:
            pass
    
  def mapToolClicked(self, tool):
    # We get here whenever the mapTool changes - useful for un-setting custom mapTool buttons
    if (tool != self.clickTool):
        self.cbGROnClick.setChecked(False)
        self.cbGRShowSquare.setChecked(False)
        self.cbGROnClick.setChecked(False)
        #pass
    if (tool != self.dragTool):
        self.butGridTool.setChecked(False)
        #self.butGridTool.setIcon(QIcon( self.pathPlugin % "images/osgr.png" ))
        
  def canvasMouseMove(self, point):
    try:
        if self.cbGROnClick.isChecked() == False:
            self.displayOSGR(point)
    except:
        #Catches an error on map canvas event handler that can happen if the tool unloaded?
        pass
        
  def displayOSGR(self, point):

    #Transform the map canvas points if maps canvas is not set to British or Irish grid
    if self.grType == "os" and self.canvas.mapSettings().destinationCrs().authid() != "EPSG:27700":
        transGrid = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), QgsCoordinateReferenceSystem("EPSG:27700"), QgsProject.instance())
    elif self.grType == "irish" and self.canvas.mapSettings().destinationCrs().authid() != "EPSG:29903":
        transGrid = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), QgsCoordinateReferenceSystem("EPSG:29903"), QgsProject.instance())
    else:
        transGrid = None

    if transGrid is not None:
        try:
            transPoint = transGrid.transform(point)
        except:
            self.leOSGR.setText("")
            self.clearMapGraphics(True, True)
            return
    else:
        transPoint = point
   
    #Save the current point
    self.easting = transPoint.x()
    self.northing = transPoint.y()
    
    gr = self.osgr.grFromEN(transPoint.x(),transPoint.y(), self.grPrecision, self.grType)
    if gr != "na":
        self.leOSGR.setText(gr)
    else:
        self.leOSGR.setText("")
            
    #Show the grid square and point if appropriate 
    self.clearMapGraphics(True, True)
       
    if (self.cbGRShowSquare.isChecked() and self.grPrecision > 0) or self.cbGRShowPoint.isChecked():
        x0 = (transPoint.x()//self.grPrecision) * self.grPrecision
        y0 = (transPoint.y()//self.grPrecision) * self.grPrecision
        centrePoint =  QgsGeometry.fromPointXY(QgsPointXY(x0 + self.grPrecision/2, y0 + self.grPrecision/2))
        points = [QgsPoint(x0,y0), QgsPoint(x0,y0 + self.grPrecision), QgsPoint(x0 + self.grPrecision, y0 + self.grPrecision), QgsPoint(x0 + self.grPrecision,y0), QgsPoint(x0,y0)]
        square = QgsGeometry.fromPolyline(points)
        
        #Transform the transformed geom back to canvas geom if maps canvas is not set to British or Irish grid
        if self.grType == "os" and self.canvas.mapSettings().destinationCrs().authid() != "EPSG:27700":
            transCanvas = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:27700"), self.canvas.mapSettings().destinationCrs(), QgsProject.instance())
        elif self.grType == "irish" and self.canvas.mapSettings().destinationCrs().authid() != "EPSG:29903":
            transCanvas = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:29903"), self.canvas.mapSettings().destinationCrs(), QgsProject.instance())
        else:
            transCanvas = None

        if transCanvas is not None:
            square.transform(transCanvas)
            centrePoint.transform(transCanvas)

        if self.cbGRShowPoint.isChecked():
            rPoint = QgsRubberBand(self.canvas)
            rPoint.setToGeometry(centrePoint, None)
            rPoint.setColor(self.grColour)
            self.rbGridPoint = rPoint

        if self.cbGRShowSquare.isChecked() and self.grPrecision > 0:
            rSquare = QgsRubberBand(self.canvas)
            rSquare.setToGeometry(square, None)
            rSquare.setColor(self.grColour)
            rSquare.setWidth(2)
            self.rbGridSquare = rSquare
        
  def canvasClicked(self, point, button):
    self.displayOSGR(point)
    
  def __unload(self):
    self.clearMapGraphics(True, True)