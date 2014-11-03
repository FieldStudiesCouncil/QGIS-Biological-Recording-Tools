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
import urllib
import urllib2
import cookielib
import json 
import hashlib, uuid

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
        self.butWMSFetch.clicked.connect(self.WMSFetch)
        self.butTaxonSearch.clicked.connect(self.TaxonSearch)
        self.butClearLast.clicked.connect(self.removeMap)
        self.butClear.clicked.connect(self.removeMaps)
        self.pbLogin.clicked.connect(self.loginNBN)
        self.pbLogout.clicked.connect(self.logoutNBN)
        
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
        self.butWMSFetch.setIcon(QIcon( self.pathPlugin % "images/nbn.png" ))
        self.butTaxonSearch.setIcon(QIcon( self.pathPlugin % "images/speciesinventory.png" ))
        self.twTaxa.setHeaderLabel("Matching taxa")
        self.noLoginText = "Not logged in to NBN. Default NBN access will apply."
        self.lblLoginStatus.setText (self.noLoginText)
        self.currentNBNUser = ""
        self.nbnAthenticationCookie = None
        
        # NBN login not currently available
        self.lblLoginStatus.setText ("NBN login for WMS is not yet available from QGIS.")
        #self.pbLogin.setEnabled(False)
        #self.pbLogout.setEnabled(False)
        self.tabWidget.widget(1).setEnabled(False)
        
    def TaxonSearch(self):
    
        if self.leTaxonSearch.text() == "":
            self.iface.messageBar().pushMessage("No search term specified.", level=QgsMessageBar.INFO)
            return
        try:
            url = 'https://data.nbn.org.uk/api/search/taxa?q=' + self.leTaxonSearch.text()
            url = url.replace(' ','%20')
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Info", "HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Info", "Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
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
                twiPTVK.setIcon(0, QIcon( self.pathPlugin % "images/Taxon20x16.png" ))
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
                   
    def WMSFetch(self):
        #strLayers = 'Vice-counties' #'Vice-counties/Grid-2km'
        #strLayers = 'OS-Scale-Dependent'
        #urlWithParams = 'url=https://gis.nbn.org.uk/SingleSpecies/NBNSYS0000005629&layers=' + strLayers + '&styles=&format=image/gif&crs=EPSG:27700'
        #Vice-counties
        #Grid-2km
        #OS-Scale-Dependent
        #http://developer.yahoo.com/python/python-rest.html
        
        #Check item in treeview is selected
        if len(self.twTaxa.selectedItems()) == 0:
            self.iface.messageBar().pushMessage("Info", "First select a taxon code (TVK).", level=QgsMessageBar.INFO)
            return
            
        #Get selected preferred TVK from tree view
        selectedTVK = self.twTaxa.selectedItems()[0].text(0)
        if selectedTVK is None:
            return
       
        #Get the map from NBN
        url = 'url=https://gis.nbn.org.uk/SingleSpecies/'
        
        #Taxon
        url = url + selectedTVK 
        
        url = url + "&username=burkmarr&userkey=c19e94acc9fba33cb279ed8267f1982d"
        
        #Set user login stuff
        if not self.leUsername.text() == "":
            url = url + "&username=" + self.leUsername.text()
            #url = url + "&userkey=" + self.nbnAthenticationCookie.value
            hashed_password = hashlib.md5(self.lePassword.text()).hexdigest()
            url = url + "&userkey=" + hashed_password
            #self.iface.messageBar().pushMessage("Info", "Hash is: " + hashed_password, level=QgsMessageBar.INFO)
            
        #Set layer stuff
        strStyles="&styles="
        if self.rb100m.isChecked():
            strLayers = "&layers=Grid-100m"
            strName = " NBN 100 m"
        elif self.rb1km.isChecked():
            strLayers = "&layers=Grid-1km"
            strName = " NBN monad"
        elif self.rb2km.isChecked():
            strLayers = "&layers=Grid-2km"
            strName = " NBN tetrad"
        elif self.rb10km.isChecked():
            strLayers = "&layers=Grid-10km"
            strName = " NBN hectad"
        else:
            strLayers = "&layers=Grid-10km&layers=Grid-2km&layers=Grid-1km&layers=Grid-100m"
            strStyles="&styles=&styles=&styles=&styles="
            strName = " NBN auto"
            
        url = url + strLayers + strStyles + "&format=image/png&crs=EPSG:27700" #falls over without the styles argument
        
        url = url.replace(' ','%20')
        #self.iface.messageBar().pushMessage("Info", "Query - " + url, level=QgsMessageBar.INFO)
        
        rlayer = QgsRasterLayer(url, 'layer', 'wms')
        
        if not rlayer.isValid():
            self.iface.messageBar().pushMessage("Info", "Layer failed to load!", level=QgsMessageBar.CRITICAL)
        else:
            rlayer.setLayerName(self.nameFromTVK(selectedTVK) + strName)
            opacity = (100-self.hsTransparency.value()) * 0.01
            rlayer.renderer().setOpacity(opacity)
            regLayer = QgsMapLayerRegistry.instance().addMapLayer(rlayer)
            self.layers.append(rlayer.id())
            self.canvas.refresh()
        
        # If he
        if strName == " NBN auto":
            #self.canvas.extentsChanged.emit() #Doesn't seem to invoke the web service, perhaps because the extents haven't actually changed
            rectExtent = self.canvas.extent()
            self.canvas.setExtent(QgsRectangle())
            self.canvas.refresh()
            self.canvas.setExtent(rectExtent)
            self.canvas.refresh()
    
    def checkTransform(self):
        if self.canvasCrs != self.canvas.mapRenderer().destinationCrs():
            self.canvasCrs = self.canvas.mapRenderer().destinationCrs()
            self.transformCrs = QgsCoordinateTransform(self.canvasCrs, self.osgbCrs)
        
    def mapExtentsChanged(self):
   
        #Needs converting to work with any coordinate system
        rectExtent = self.canvas.extent()
        self.checkTransform()
        if self.canvasCrs != self.osgbCrs:
            mapWidth = self.transformCrs.transformBoundingBox(rectExtent).width()
        else:
            mapWidth = rectExtent.width()
        
        #self.iface.messageBar().pushMessage("Info", "Signal emitted", level=QgsMessageBar.INFO)
        
        for layerID in self.layers:
            rlayer = None
            try:
                rlayer = QgsMapLayerRegistry.instance().mapLayer(layerID)
            except:
                pass
                
            if not rlayer is None:
            
                #self.iface.messageBar().pushMessage("Info", "Width: " + rlayer.name(), level=QgsMessageBar.INFO)
                if rlayer.name().endswith("NBN auto"):
            
                    if mapWidth < 15000:
                        rlayer.setSubLayerVisibility("Grid-10km", False)
                        rlayer.setSubLayerVisibility("Grid-2km", False)
                        rlayer.setSubLayerVisibility("Grid-1km", False)
                        rlayer.setSubLayerVisibility("Grid-100m", True)
                    elif mapWidth < 100000:
                        rlayer.setSubLayerVisibility("Grid-10km", False)
                        rlayer.setSubLayerVisibility("Grid-2km", False)
                        rlayer.setSubLayerVisibility("Grid-1km", True)
                        rlayer.setSubLayerVisibility("Grid-100m", False)
                    elif mapWidth < 250000:
                        rlayer.setSubLayerVisibility("Grid-10km", False)
                        rlayer.setSubLayerVisibility("Grid-2km", True)
                        rlayer.setSubLayerVisibility("Grid-1km", False)
                        rlayer.setSubLayerVisibility("Grid-100m", False)
                    else:
                        rlayer.setSubLayerVisibility("Grid-10km", True)
                        rlayer.setSubLayerVisibility("Grid-2km", False)
                        rlayer.setSubLayerVisibility("Grid-1km", False)
                        rlayer.setSubLayerVisibility("Grid-100m", False)
            
            
    def nameFromTVK(self, tvk):
       
        #Get the preferred taxon name for the TVK
        try:
            url = 'https://data.nbn.org.uk/api/taxa/' + tvk
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Info", "HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return ('')
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Info", "Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
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
 
        return
        
        if not self.nbnAthenticationCookie is None:
            self.iface.messageBar().pushMessage("Info", "You are already logged in to the NBN as '" + self.currentNBNUser + "'.", level=QgsMessageBar.WARNING)
            return
            
        #response = requests.post('https://data.nbn.org.uk/api/user/login', files=dict(username='burkmarr', password='vespula'))
        #self.iface.messageBar().pushMessage("Info", "Response from NBN login: " + response.status_code, level=QgsMessageBar.INFO)
        
        username = self.leUsername.text()
        password = self.lePassword.text()
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        login_data = urllib.urlencode({'username' : username, 'password' : password})
        try:
            opener.open('https://data.nbn.org.uk/api/user/login', login_data)
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Info", "HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Info", "Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
            return
            
        #self.iface.messageBar().pushMessage("Info", "NBN login success", level=QgsMessageBar.INFO)
        
        #resp = opener.open('http://www.example.com/hiddenpage.php')
        #print resp.read()

        for cookie in cj:
            if cookie.name == 'nbn.token_key':
                self.nbnAthenticationCookie = cookie
                self.currentNBNUser = self.leUsername.text()
                self.lblLoginStatus.setText ("You are logged in as '" + self.currentNBNUser + "'")
        return
        
        
    def logoutNBN(self):
 
        return
        
        if self.nbnAthenticationCookie is None:
            self.iface.messageBar().pushMessage("Info", "Can't logout because you are not logged in to the NBN.", level=QgsMessageBar.WARNING)
            return
            
        cj = cookielib.CookieJar()
        cj.set_cookie(self.nbnAthenticationCookie)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        try:
            opener.open('https://data.nbn.org.uk/api/user/logout')
        except urllib2.HTTPError, e:
            self.iface.messageBar().pushMessage("Info", "HTTP error: %d" % e.code, level=QgsMessageBar.CRITICAL)
            return
        except urllib2.URLError, e:
            self.iface.messageBar().pushMessage("Info", "Network error: %s" % e.reason.args[1], level=QgsMessageBar.CRITICAL)
            return
            
        self.lblLoginStatus.setText (self.noLoginText)
        self.currentNBNUser = ""
        self.nbnAthenticationCookie = None
