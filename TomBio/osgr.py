# -*- coding: utf-8 -*-
"""
/***************************************************************************
 osgr
        A class for manipulating OSGB36 grid refs
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

class osgr:

    def __init__(self):

        # Initialise the OS 100 k prefixes list
        os100kPrefixes = []
        os100kPrefixes.append(("SV",0, 0))
        os100kPrefixes.append(("SW",1, 0))
        os100kPrefixes.append(("SX",2, 0))
        os100kPrefixes.append(("SY",3, 0))
        os100kPrefixes.append(("SZ",4, 0))
        os100kPrefixes.append(("TV",5, 0))
        os100kPrefixes.append(("SR",1, 1))
        os100kPrefixes.append(("SS",2, 1))
        os100kPrefixes.append(("ST",3, 1))
        os100kPrefixes.append(("SU",4, 1))
        os100kPrefixes.append(("TQ",5, 1))
        os100kPrefixes.append(("TR",6, 1))
        os100kPrefixes.append(("SM",1, 2))
        os100kPrefixes.append(("SN",2, 2))
        os100kPrefixes.append(("SO",3, 2))
        os100kPrefixes.append(("SP",4, 2))
        os100kPrefixes.append(("TL",5, 2))
        os100kPrefixes.append(("TM",6, 2))
        os100kPrefixes.append(("SH",2, 3))
        os100kPrefixes.append(("SJ",3, 3))
        os100kPrefixes.append(("SK",4, 3))
        os100kPrefixes.append(("TF",5, 3))
        os100kPrefixes.append(("TG",6, 3))
        os100kPrefixes.append(("SC",2, 4))
        os100kPrefixes.append(("SD",3, 4))
        os100kPrefixes.append(("SE",4, 4))
        os100kPrefixes.append(("TA",5, 4))
        os100kPrefixes.append(("NW",1, 5))
        os100kPrefixes.append(("NX",2, 5))
        os100kPrefixes.append(("NY",3, 5))
        os100kPrefixes.append(("NZ",4, 5))
        os100kPrefixes.append(("OV",5, 5))
        os100kPrefixes.append(("NR",1, 6))
        os100kPrefixes.append(("NS",2, 6))
        os100kPrefixes.append(("NT",3, 6))
        os100kPrefixes.append(("NU",4, 6))
        os100kPrefixes.append(("NL",0, 7))
        os100kPrefixes.append(("NM",1, 7))
        os100kPrefixes.append(("NN",2, 7))
        os100kPrefixes.append(("NO",3, 7))
        os100kPrefixes.append(("HW",1, 10))
        os100kPrefixes.append(("HX",2, 10))
        os100kPrefixes.append(("HY",3, 10))
        os100kPrefixes.append(("HZ",4, 10))
        os100kPrefixes.append(("NF",0, 8))
        os100kPrefixes.append(("NG",1, 8))
        os100kPrefixes.append(("NH",2, 8))
        os100kPrefixes.append(("NJ",3, 8))
        os100kPrefixes.append(("NK",4, 8))
        os100kPrefixes.append(("NA",0, 9))
        os100kPrefixes.append(("NB",1, 9))
        os100kPrefixes.append(("NC",2, 9))
        os100kPrefixes.append(("ND",3, 9))
        os100kPrefixes.append(("HT",3, 11))
        os100kPrefixes.append(("HU",4, 11))
        os100kPrefixes.append(("HP",4, 12))
        self.os100kPrefixes = os100kPrefixes
        
        # Initialise the tetrad suffix list
        osTetradSuffixes = []
        osTetradSuffixes.append(("A",0, 0))
        osTetradSuffixes.append(("B",0, 1))
        osTetradSuffixes.append(("C",0, 2))
        osTetradSuffixes.append(("D",0, 3))
        osTetradSuffixes.append(("E",0, 4))
        osTetradSuffixes.append(("F",1, 0))
        osTetradSuffixes.append(("G",1, 1))
        osTetradSuffixes.append(("H",1, 2))
        osTetradSuffixes.append(("I",1, 3))
        osTetradSuffixes.append(("J",1, 4))
        osTetradSuffixes.append(("K",2, 0))
        osTetradSuffixes.append(("L",2, 1))
        osTetradSuffixes.append(("M",2, 2))
        osTetradSuffixes.append(("N",2, 3))
        osTetradSuffixes.append(("P",2, 4))
        osTetradSuffixes.append(("Q",3, 0))
        osTetradSuffixes.append(("R",3, 1))
        osTetradSuffixes.append(("S",3, 2))
        osTetradSuffixes.append(("T",3, 3))
        osTetradSuffixes.append(("U",3, 4))
        osTetradSuffixes.append(("V",4, 0))
        osTetradSuffixes.append(("W",4, 1))
        osTetradSuffixes.append(("X",4, 2))
        osTetradSuffixes.append(("Y",4, 3))
        osTetradSuffixes.append(("Z",4, 4))
        self.osTetradSuffixes = osTetradSuffixes
        
        # Initialise the quadrant suffix list
        osQuadrantSuffixes = []
        osQuadrantSuffixes.append(("SW",0, 0))
        osQuadrantSuffixes.append(("NW",0, 1))
        osQuadrantSuffixes.append(("SE",1, 0))
        osQuadrantSuffixes.append(("NE",1, 1))
        self.osQuadrantSuffixes = osQuadrantSuffixes
    
    def getTetradSuffix(self, easting, northing):
        rem = int(easting % 10000)
        indexEast = rem // 2000
        rem = int(northing % 10000)
        indexNorth = rem // 2000
        
        for t in self.osTetradSuffixes:
            if (t[1] == indexEast) & (t[2] == indexNorth):
                return(t[0])
    
    def getQuadrantSuffix(self, easting, northing):
        rem = int(easting % 10000)
        indexEast = rem // 5000
        rem = int(northing % 10000)
        indexNorth = rem // 5000
    
        for t in self.osQuadrantSuffixes:
            if (t[1] == indexEast) & (t[2] == indexNorth):
                return(t[0])
        
    def enFromGR(self, grLocate):
        retCheck = self.checkGR(grLocate)
        
        if retCheck[0] == 0:
            return (0,0,0,retCheck[1])
            
        for t in self.os100kPrefixes:
            if (t[0] == grLocate[0:2].upper()):
                east100 = t[1]
                north100 = t[2]
                break
            
        precision = retCheck[0]
            
        factEasting = 0
        factNorthing = 0
            
        if precision == 10000:
            factEasting = int(grLocate[2:3])
            factNorthing = int(grLocate[3:4])
        elif precision == 5000:
            factEasting = int(grLocate[2:3]) * 2
            factNorthing = int(grLocate[3:4]) * 2
            for t in self.osQuadrantSuffixes:
                if grLocate[4:6].upper() == t[0]:
                    factEasting = factEasting + t[1]
                    factNorthing = factNorthing + t[2]
                    break
        elif precision == 2000:
            factEasting = int(grLocate[2:3]) * 5
            factNorthing = int(grLocate[3:4]) * 5
            for t in self.osTetradSuffixes:
                if grLocate[4:5].upper() == t[0]:
                    factEasting = factEasting + t[1]
                    factNorthing = factNorthing + t[2]
                    break
        elif precision == 1000:
            factEasting = int(grLocate[2:4])
            factNorthing = int(grLocate[4:6])
        elif precision == 100:
            factEasting = int(grLocate[2:5])
            factNorthing = int(grLocate[5:8])
        elif precision == 10:
            factEasting = int(grLocate[2:6])
            factNorthing = int(grLocate[6:10])
        elif precision == 1:
            factEasting = int(grLocate[2:7])
            factNorthing = int(grLocate[7:12])
            
        factEasting = factEasting + 0.5
        factNorthing = factNorthing + 0.5
        
        easting = east100 * 100000 + precision * factEasting
        northing = north100 * 100000 + precision * factNorthing
            
        return (easting, northing, precision, retCheck[1])

    def geomFromGR(self, gr, type):
        loc = self.enFromGR(gr)
        precision = loc[2]
        x = loc[0] - (precision / 2)
        y = loc[1] - (precision / 2)
        
        if x == 0:
            return None
        
        if type == "point":
            return QgsGeometry.fromPoint(QgsPoint(x + (precision/2), y + (precision/2)))
        elif type == "square":
            points = [[QgsPoint(x,y), QgsPoint(x,y + precision), QgsPoint(x + precision,y + precision), QgsPoint(x + precision,y)]]
            return QgsGeometry.fromPolygon(points)
        else:
            # Circle
            return self.circleGeom(loc[0], loc[1], precision / 2)
            
    def circleGeom(self, j, k, r):
        cumulativeRad = 0
        deltaDeg = 10
        deltaRad = deltaDeg * math.pi / 180
        points = []
        while cumulativeRad < (2 * math.pi): #360 * pi / 180
            cumulativeRad = cumulativeRad + deltaRad
            x1 = j + r * math.cos(cumulativeRad)
            y1 = k + r * math.sin(cumulativeRad)
            points.append(QgsPoint(x1,y1))
            
        return QgsGeometry.fromPolygon([points])
            
    def checkGR(self, grLocate):
    
        if grLocate.__len__() < 2:
            return (0, "Invalid grid reference - must be at least two characters")
            
        prefixFound = False
        for t in self.os100kPrefixes:
            if (t[0] == grLocate[0:2].upper()):
                prefixFound = True
                break
        if prefixFound == False:
            return (0, "Invalid 100 km two-letter prefix")
            
        re100kmGR = re.compile('^[a-zA-Z][a-zA-Z]$')
        reHectadGR = re.compile('^[a-zA-Z][a-zA-Z][0-9][0-9]$')
        reQuadrantGR = re.compile('^[a-zA-Z][a-zA-Z][0-9][0-9][a-zA-Z][a-zA-Z]$') #re.compile('^[a-zA-Z][a-zA-Z][0-9][0-9](((NW|NE)|SW)|SE)$')
        reTetradGR= re.compile('^[a-zA-Z][a-zA-Z][0-9][0-9][a-zA-Z]$') #re.compile('^[a-zA-Z][a-zA-Z][0-9][0-9][a-np-zA-NP-Z]$')
        reMonadGR = re.compile('^[a-zA-Z][a-zA-Z][0-9][0-9][0-9][0-9]$')
        reSixFigGR = re.compile('^[a-zA-Z][a-zA-Z][0-9][0-9][0-9][0-9][0-9][0-9]$')
        reEightFigGR = re.compile('^[a-zA-Z][a-zA-Z][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$')
        reTenFigGR = re.compile('^[a-zA-Z][a-zA-Z][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$')
        
        if re100kmGR.match(grLocate):
            return (100000, "100 km gr")
            
        if reHectadGR.match(grLocate):
            return (10000, "hectad")
            
        if reQuadrantGR.match(grLocate):
            suf = grLocate[4:6].upper()
            if (suf != "NW" and suf != "NE" and suf != "SW" and suf != "SE"):
                return (0, "Invalid quadrant suffix - must be 'NW', 'NE', 'SW' or 'SE'.")
            else:
                return (5000, "quadrant")
            
        if reTetradGR.match(grLocate):
            if (grLocate[4:5].upper() == "O"):
                return (0, "Invalid tetrad suffix - cannot be 'O'.")
            else:
                return (2000, "tetrad")
            
        if reMonadGR.match(grLocate):
            return (1000, "monad")
            
        if reSixFigGR.match(grLocate):
            return (100, "6 fig")
            
        if reEightFigGR.match(grLocate):
            return (10, "8 fig")
            
        if reTenFigGR.match(grLocate):
            return (1, "10 fig")
            
        return (0, "Invalid grid reference")
    
    
    def grFromEN(self, easting, northing, precision):

        # For any passed arguments that cannot be returned as a value
        # grid reference from this function, return nothing.
        
        # From the passed easting and northing, extract the 100 k
        # integers that need to be replaced in the gr by the prefix.
    
        try:
            east100 = int(easting // 100000)
            north100 = int(northing // 100000)
        except:
            return "error"
    
        prefix = ""
        suffix = ""
        
        for t in self.os100kPrefixes:
            if (t[1] == east100) & (t[2] == north100):
                prefix = t[0]
                break
                
        if prefix == "":
            return ""
            
        if precision == 1:
            intDigits = 5
        elif precision == 10:
            intDigits = 4
        elif precision == 100:
            intDigits = 3
        elif precision == 1000:
            intDigits = 2
        elif precision == 2000:
            intDigits = 1
            suffix = self.getTetradSuffix(easting, northing)
        elif precision == 5000:
            intDigits = 1
            suffix = self.getQuadrantSuffix(easting, northing)
        elif precision == 10000:
            intDigits = 1
        elif precision == 100000:
            intDigits = 0
        else:
            # Not a valid precision for a grid reference
            # so return sgring with 'na'.
            return "na"
            
        strEast = str(int(easting)).rjust(6,'0')
        strEast = strEast[str(east100).__len__():str(east100).__len__() + intDigits]
        strNorth = str(int(northing)).rjust(6,'0') 
        strNorth = strNorth[str(north100).__len__():str(north100).__len__() + intDigits]
                   
        return prefix + strEast + strNorth + suffix
        
    def convertGr(self, grIn, toPrecision):
        
        ret = self.checkGR(grIn)
        fromPrecision = ret[0]
        
        if toPrecision < fromPrecision:
            return ("", "Output grid precision exceeds precision of grid reference " + grIn + ".")
        
        if toPrecision == 5000 and fromPrecision == 2000:
            return ("", "Record with grid reference " + grIn + "omitted because tetrads cannot always be unambiguously assigned to a quadrant.")
        
        easting = self.enFromGR(grIn)[0]
        northing = self.enFromGR(grIn)[1]
        
        grOut = self.grFromEN(easting, northing, toPrecision)
        
        #if grOut == "TV55":
        #    return ("", grIn + ", easting: " + str(easting) + ", northing: " + str(northing))
            
        return (grOut, "")


    