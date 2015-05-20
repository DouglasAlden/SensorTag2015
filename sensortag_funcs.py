#!/usr/bin/python
#
# Copyright 2013 Michael Saunby
# Copyright 2013-2014 Thomas Ackermann
# Copyright 2015 Douglas Alden
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

#
# All these algorithms are borrowed from 
# http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
# which most likely took it from the datasheet. 
#
# Revisions:
# 19 May 2015 - Douglas Alden
#   Revised for humidity and added lux for SensorTag 2.0
import math

tosigned = lambda n: float(n-0x10000) if n>0x7fff else float(n)
tosignedbyte = lambda n: float(n-0x100) if n>0x7f else float(n)

# TI TMP007
# http://www.ti.com/product/tmp007
# Infrared Thermopile Contactless Temperature Sensor
# Need to determine correct algorithm for TMP007, original
# code was for the TMP006
#def calcTmp(ambT, objT):
#    ambT = tosigned(ambT)
#    objT = tosigned(objT)
#    m_tmpAmb = ( ambT >> 2 ) * 0.03125
#    Vobj2 = objT / 4
#    Vobj2 = Vobj2 * 0.03125
    # Tdie2 = m_tmpAmb + 273.15
    # S0 = 5.593E-14            # Calibration factor
    # a1 = 1.75E-3
    # a2 = -1.678E-5
    # b0 = -2.94E-5
    # b1 = -5.7E-7
    # b2 = 4.63E-9
    # c2 = 13.4
    # Tref = 298.15
    # S = S0*(1+a1*(Tdie2 - Tref)+a2*pow((Tdie2 - Tref),2))
    # Vos = b0 + b1*(Tdie2 - Tref) + b2*pow((Tdie2 - Tref),2)
    # fObj = (Vobj2 - Vos) + c2*pow((Vobj2 - Vos),2)
    # tObj = pow(pow(Tdie2,4) + (fObj/S),.25)
    # tObj = (tObj - 273.15)
    # return (m_tmpAmb, tObj)

# TI HDC1000
# http://www.ti.com/lit/ds/symlink/hdc1000.pdf
# Page 14
def calcHum(rawT, rawH):
    # -- calculate temperature [deg C] --
    t = (rawT * 165.0) / 65535.0 - 40.0
    # -- calculate relative humidity [%RH] --
    rh =  (rawH * 100) / 65535.0
    return (t, rh)

# TI OPT3001
# http://www.ti.com/product/opt3001
# From Sensor.java in TI's Android repository
#http://git.ti.com/sensortag-android/sensortag-android/blobs/master/src/com/example/ti/ble/sensortag/Sensor.java
def calcLux(rawLux):
    # -- calculate lux --
    mantissa = rawLux & 0x0FFF
    exponent = (rawLux >> 12) & 0xF
    magnitude = math.pow(2.0, exponent)
    lux = mantissa * magnitude / 100.0
    #lux =  rawLux / 100.0
    return (lux)

#
# From http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
# but combining all three values and giving magnitude.
# Magnitude tells us if we are at rest, falling, etc.
#

def calcAccel(rawX, rawY, rawZ):
    accel = lambda v: tosignedbyte(v) / 64.0  # Range -2G, +2G
    xyz = [accel(rawX), accel(rawY), accel(rawZ)]
    mag = (xyz[0]**2 + xyz[1]**2 + xyz[2]**2)**0.5
    return (xyz, mag)

#
# From http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
# but combining all three values.
#

def calcMagn(rawX, rawY, rawZ):
    magforce = lambda v: (tosigned(v) * 1.0) / (65536.0/2000.0)
    return [magforce(rawX),magforce(rawY),magforce(rawZ)]

#Barometer needs to be updated for the new sensor in the SensorTag 2015
class Barometer:

# Ditto.
# Conversion algorithm for barometer temperature
# 
#  Formula from application note, rev_X:
#  Ta = ((c1 * Tr) / 2^24) + (c2 / 2^10)
#
#  c1 - c8: calibration coefficients the can be read from the sensor
#  c1 - c4: unsigned 16-bit integers
#  c5 - c8: signed 16-bit integers
#
    def calcBarTmp(self, raw_temp):
        c1 = self.m_barCalib.c1
        c2 = self.m_barCalib.c2
        val = long((c1 * raw_temp) * 100)
        temp = val >> 24
        val = long(c2 * 100)
        temp += (val >> 10)
        return float(temp) / 100.0

#
# Conversion algorithm for barometer pressure (hPa)
# 
# Formula from application note, rev_X:
# Sensitivity = (c3 + ((c4 * Tr) / 2^17) + ((c5 * Tr^2) / 2^34))
# Offset = (c6 * 2^14) + ((c7 * Tr) / 2^3) + ((c8 * Tr^2) / 2^19)
# Pa = (Sensitivity * Pr + Offset) / 2^14
#
    def calcBarPress(self,Tr,Pr):
        c3 = self.m_barCalib.c3
        c4 = self.m_barCalib.c4
        c5 = self.m_barCalib.c5
        c6 = self.m_barCalib.c6
        c7 = self.m_barCalib.c7
        c8 = self.m_barCalib.c8
        # Sensitivity
        s = long(c3)
        val = long(c4 * Tr)
        s += (val >> 17)
        val = long(c5 * Tr * Tr)
        s += (val >> 34)
        # Offset
        o = long(c6) << 14
        val = long(c7 * Tr)
        o += (val >> 3)
        val = long(c8 * Tr * Tr)
        o += (val >> 19)
        # Pressure (Pa)
        pres = ((s * Pr) + o) >> 14
        return float(pres)/100.0

    def calc(self,  rawT, rawP):
        self.m_raw_temp = tosigned(rawT)
        self.m_raw_pres = rawP # N.B.  Unsigned value
        bar_temp = self.calcBarTmp( self.m_raw_temp )
        bar_pres = self.calcBarPress( self.m_raw_temp, self.m_raw_pres )
        return( bar_temp, bar_pres)
 
    def __init__(self, rawCalibration):
        self.m_barCalib = self.Calib( rawCalibration )
        return

    class Calib:

        # This works too
        # i = (hi<<8)+lo        
        def bld_int(self, lobyte, hibyte):
            return (lobyte & 0x0FF) + ((hibyte & 0x0FF) << 8)
        
        def __init__( self, pData ):
            self.c1 = self.bld_int(pData[0],pData[1])
            self.c2 = self.bld_int(pData[2],pData[3])
            self.c3 = self.bld_int(pData[4],pData[5])
            self.c4 = self.bld_int(pData[6],pData[7])
            self.c5 = tosigned(self.bld_int(pData[8],pData[9]))
            self.c6 = tosigned(self.bld_int(pData[10],pData[11]))
            self.c7 = tosigned(self.bld_int(pData[12],pData[13]))
            self.c8 = tosigned(self.bld_int(pData[14],pData[15]))
