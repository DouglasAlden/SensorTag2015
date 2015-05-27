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
# Read sensors from the TI SensorTag. It's a
# BLE (Bluetooth low energy) device so by
# automating gattsensortag (from BlueZ 5.14) with
# pexpect (3.1) we are able to read and write values.
#
# Usage: sensortag_test.py BLUETOOTH_ADR
#
# To find the address of your SensorTag run 'sudo hcisensortag lescan'
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

DEBUG = 0

hostname = socket.gethostname()

# Connect to SensorTag using gatttool
bluetooth_adr = sys.argv[1]
sensortag = pexpect.spawn('/usr/local/bin/gatttool -b ' + bluetooth_adr + ' --interactive')
# bug in pexpect? automating gattsensortag works only if we are using a logfile!
# TODO: check again with pexpect 3.1 and gattsensortag 5.14
if DEBUG==0:
  logfile = open("/dev/null", "w")
  sensortag.logfile = logfile
else:
  sensortag.logfile = sys.stdout

try:
  sensortag.expect(['\[LE\]>', pexpect.TIMEOUT], timeout=10)
except pexpect.TIMEOUT:
    print '\ngatttool could not find SensorTag', bluetooth_adr
    sensortag.kill(0)
    sys.exit (1)


# connect to SensorTag
try:
  print bluetooth_adr, "\nTrying to connect. You might need to press the side button ..."
  sensortag.sendline('connect')
  sensortag.expect('Connection successful', timeout=5)
  sensortag.expect('\[LE\]>')
except pexpect.TIMEOUT:
  print '\nUnable to initiate connection to SensorTag', bluetooth_adr
  sensortag.kill(0)
  sys.exit (1)


print "Enabling sensors on SensorTag: ", bluetooth_adr

# enable IR temperature sensor (TI TMP0007)
#sensortag.sendline('char-write-cmd 0x24 01')
#sensortag.expect('\[LE\]>')

# enable humidity sensor (TI HDC1000)
sensortag.sendline('char-write-cmd 0x2C 01')
sensortag.expect('\[LE\]>')

# enable lux sensor (TI OPT3001)
sensortag.sendline('char-write-cmd 0x44 01')
sensortag.expect('\[LE\]>')

# enable barometric pressure sensor (Bosch Sensortec BMP280)
#sensortag.sendline('char-write-cmd 0x34 02')
#sensortag.expect('\[LE\]>')r2

#sensortag.sendline('char-read-hnd 0x52')
#sensortag.expect('descriptor: .*? \r')

#after = sensortag.after
#v = after.split()[1:] 
#vals = [long(float.fromhex(n)) for n in v]
#barometer = Barometer( vals )
#sensortag.sendline('char-write-cmd 0x4f 01')
#sensortag.expect('\[LE\]>')


# wait for the sensors to become ready
time.sleep(1)

cnt = 0
try:
  while True:

    # read IR temperature sensor
    # sensortag.sendline('char-read-hnd 0x25')
    # sensortag.expect('descriptor: .*? \r') 
    # v = sensortag.after.split()
    # rawObjT = long(float.fromhex(v[2] + v[1]))
    # rawAmbT = long(float.fromhex(v[4] + v[3]))
    # (at, it) = calcTmp(rawAmbT, rawObjT)

    # read humidity sensor (
    sensortag.sendline('char-read-hnd 0x29')
    sensortag.expect('descriptor: .*? \r') 
    v = sensortag.after.split()
    rawT = long(float.fromhex(v[2] + v[1]))
    rawH = long(float.fromhex(v[4] + v[3]))
    (ht, h) = calcHum(rawT, rawH)

    # read lux sensor
    sensortag.sendline('char-read-hnd 0x41')
    sensortag.expect('descriptor: .*? \r') 
    v = sensortag.after.split()
    rawLux = long(float.fromhex(v[2] + v[1]))
    lux = calcLux(rawLux)

    dt = datetime.utcnow().isoformat()
    # replace T between date and time with a comma
    dt = dt.replace('T',',')
    # Truncate the time. We do not need microsec resolution
    dt = dt[:21]
    
    # remove colons from address
    bluetooth_adr = bluetooth_adr.replace(':','-')
    
    outputData = "%s,%s,%s,T,%.1f,RH,%.1f,Lux,%.1f " % (dt, hostname, bluetooth_adr, ht, h, lux)
    if DEBUG:
      print outputData
    
    data = open("/home/wind/metdata/log/sensortag/"+hostname+".log", "a")
    data.write("%s\n" % outputData)
    data.close()

    time.sleep(0.6)

except KeyboardInterrupt:
  # Print backspace to eat control-C
  print "\b\bExiting..."

except pexpect.TIMEOUT:
  print "\nSensorTag communication lost\n"
    
finally:
  if data:
    data.close()
  if sensortag:
    sensortag.kill(0)
  sys.exit (0)

