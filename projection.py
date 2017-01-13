# -*- coding: utf-8 -*-
"""
/***************************************************************************
 osgr
        A class for reprojecting geometry etc
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
import math
import re
from qgis.core import *
from qgis.gui import *
from qgis.utils import *

class projection:

    def __init__(self, crsInput, crsCanvas):

        self.transformCrs = QgsCoordinateTransform(crsInput, crsCanvas)
        
    def xyToPoint(self, x, y):
    
        try:
            point = QgsPoint(x, y)
        except:
            point = None
            
        if not point is None:
            try:
                canvasPoint = self.transformCrs.transform(point)
            except:
                e = sys.exc_info()[0]
                return [None, "Transformation error: %s" % e]
                
            return [QgsGeometry.fromPoint(canvasPoint), ""]
        else:
            return [None, "Couldn't create points from input coordinates"]
            
    def xyToGridGeom(self, xOriginal, yOriginal, gridPrecision, type):
           
        # First convert the input x and y to the map canvas x and y
        xIn = None
        yIn = None
        x = None
        y = None
        err = ""
                
        if not xOriginal == None and not yOriginal == None:
            try:
                point = QgsPoint(float(xOriginal), float(yOriginal))
            except:
                point = None
                err = "There was a problem with the x, y coordinates. x = " + str(xOriginal) + " and y = " + str(yOriginal) + "."
                
            if point != None:
                try:
                    canvasPoint = self.transformCrs.transform(point)
                except:
                    canvasPoint = None
                    e = sys.exc_info()[0]
                    err = "Transformation error: %s" % e
            else:
                canvasPoint = None
      
            if canvasPoint == None:
                err = "There was a problem transforming the x, y coordinates. x = " + str(xOriginal) + " and y = " + str(yOriginal) + "."
            else:
                xIn = canvasPoint.x()
                yIn = canvasPoint.y()
                
        # Get the x and y of the bottom left of the grid square
        if xIn != None and yIn != None:
            try:
                x = (xIn // gridPrecision) * gridPrecision
                y = (yIn // gridPrecision) * gridPrecision
                err = ""
            except:
                x = None
                y = None
                err = "There was a problem deriving the grid square coordinates."
                   
        # The working grid reference is derived from the bottom left of grid square
        
        if x != None and y != None:
            gr = str(x) + "#" + str(y)
        else:
            gr = ""
            
        if x == None or y == None:
            geom = None
        elif type == "point":
            geom =  QgsGeometry.fromPoint(QgsPoint(x + (gridPrecision/2), y + (gridPrecision/2)))
        elif type == "square":
            points = [[QgsPoint(x,y), QgsPoint(x,y + gridPrecision), QgsPoint(x + gridPrecision,y + gridPrecision), QgsPoint(x + gridPrecision,y)]]
            geom = QgsGeometry.fromPolygon(points)
        else:
            # Circle
            r = gridPrecision / 2
            j = x + r
            k = y + r
            cumulativeRad = 0
            deltaDeg = 10
            deltaRad = deltaDeg * math.pi / 180
            points = []
            while cumulativeRad < (2 * math.pi): #360 * pi / 180
                cumulativeRad = cumulativeRad + deltaRad
                x1 = j + r * math.cos(cumulativeRad)
                y1 = k + r * math.sin(cumulativeRad)
                points.append(QgsPoint(x1,y1))
            geom = QgsGeometry.fromPolygon([points])
            
        return [gr, geom, err]
        
     
        


    