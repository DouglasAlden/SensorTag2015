#!/usr/bin/env python

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
# Read sensors from the TI SensorTag. It's a
# BLE (Bluetooth low energy) device so by
# automating gatttool (from BlueZ 5.14) with
# pexpect (3.1) we are able to read and write values.
#
# Usage: sensortag_test.py BLUETOOTH_ADR
#
# To find the address of your SensorTag run 'sudo hcitool lescan'
# To power up your bluetooth dongle run 'sudo hciconfig hci0 up'
#
# Revisions:
# 19 May 2015 - Douglas Alden
#   Revised for humidity and added lux for SensorTag 2.0

import sys
import time
from datetime import datetime
import pexpect
from sensortag_funcs import *
import socket

hostname = socket.gethostname()

# start gatttool
adr = sys.argv[1]
tool = pexpect.spawn('gatttool -b ' + adr + ' --interactive')
tool.expect('\[LE\]>')

# bug in pexpect? automating gatttool works only if we are using a logfile!
# TODO: check again with pexpect 3.1 and gatttool 5.14
logfile = open("/dev/null", "w")
tool.logfile = logfile

# connect to SensorTag
print adr, " Trying to connect. You might need to press the side button ..."
tool.sendline('connect')
tool.expect('\[LE\]>')

print adr, " Enabling sensors ..."

# enable IR temperature sensor (TI TMP0007)
#tool.sendline('char-write-cmd 0x24 01')
#tool.expect('\[LE\]>')

# enable humidity sensor (TI HDC1000)
tool.sendline('char-write-cmd 0x2C 01')
tool.expect('\[LE\]>')

# enable lux sensor (TI OPT3001)
tool.sendline('char-write-cmd 0x44 01')
tool.expect('\[LE\]>')

# enable barometric pressure sensor (Bosch Sensortec BMP280)
#tool.sendline('char-write-cmd 0x34 02')
#tool.expect('\[LE\]>')

#tool.sendline('char-read-hnd 0x52')
#tool.expect('descriptor: .*? \r')

#after = tool.after
#v = after.split()[1:] 
#vals = [long(float.fromhex(n)) for n in v]
#barometer = Barometer( vals )
#tool.sendline('char-write-cmd 0x4f 01')
#tool.expect('\[LE\]>')


# wait for the sensors to become ready
time.sleep(2)

cnt = 0
try:
  while True:

    cnt = cnt + 1
    #print adr, " CNT %d" % cnt

    # read IR temperature sensor
    # tool.sendline('char-read-hnd 0x25')
    # tool.expect('descriptor: .*? \r') 
    # v = tool.after.split()
    # rawObjT = long(float.fromhex(v[2] + v[1]))
    # rawAmbT = long(float.fromhex(v[4] + v[3]))
    # (at, it) = calcTmp(rawAmbT, rawObjT)

    # read humidity sensor (
    tool.sendline('char-read-hnd 0x29')
    tool.expect('descriptor: .*? \r') 
    v = tool.after.split()
    rawT = long(float.fromhex(v[2] + v[1]))
    rawH = long(float.fromhex(v[4] + v[3]))
    (ht, h) = calcHum(rawT, rawH)

    # read lux sensor
    tool.sendline('char-read-hnd 0x41')
    tool.expect('descriptor: .*? \r') 
    v = tool.after.split()
    rawLux = long(float.fromhex(v[2] + v[1]))
    lux = calcLux(rawLux)

    dt = datetime.utcnow().isoformat()
    # replace T between date and time with a comma
    dt = dt.replace('T',',')
    # Truncate the time. We do not need microsec resolution
    dt = dt[:21]
    outputData = "%s,%s,%s,T,%.1f,RH,%.1f,Lux,%.1f " % (dt, hostname, adr, ht, h, lux)
    print outputData
    
    data = open("/home/wind/ble/log/sensortag/"+hostname+"_"+adr, "w")
    data.write("%s\n" % outputData)
    data.close()

    time.sleep(1)
except KeyboardInterrupt as e:
  # Print backspace to eat control-C
  print "\b\bExiting..."

