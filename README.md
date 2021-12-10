# ECE4564 Fall 2021 - Final Project: HeatstrokeCanary
## Team 09
#### Keerthana Aluri, Michael Fuhrer, Kirti Patel

This repository contains scripts which implement a Heatstroke Canary and 
Server interaction. The Heatstroke Canary uses an IMU, Camera, and Govee
Thermometer (H5074) to detect unsafe conditions within a parked automobile.
The Server receives data from Canaries and hosts a WebGUI to allow users to register and set conditions when
and to where alert notifications should be set.

## Requirements

### CanaryPi

The CanaryPi, which can be executed via `python canary.py`, requires the following dependencies:
* <b>GoveeBTTempLogger</b>: Used to read temperatures advertised by Govee thermometer.
  See intructions below to run daemon.
* <b>BerryIMU</b>: Used to retrieve IMU accelerometer data. Included in /lib directory
* <b>picamera</b>: Used to take photographs. Installed by default on Raspbian.
* <b>Amazon Rekognition</b>: Leveraged to get labels for captured photographs. Included in /lib directory
* <b>boto3</b>: Used to establish a connection to the AWS suite.
* <b>requests</b>: Used to make HTTP posts to the ServerPi
* <b>json</b>: Used to prepare HTTP payload.
* <b>twilio</b>: Used to send SMS notifications to the emergency contact.

#### GoveeBTTempLogger Set-Up

https://github.com/wcbonner/GoveeBTTempLogger

This service is a logger daemon which searches for Bluetooth Low-Energy advertisements
from the Govee thermometer and appends the reading to a log file. To configure the daemon
to run properly with CanaryPi do the following:

1. Enter the service's directory: `cd {Parent Path}/HeatstrokeCanary/lib/GoveeBtTempLogger`
2. Install the daemon: `sudo apt-get install ./GoveeBTTempLogger.deb`
3. Configure the daemon: `sudo systemctl edit goveebttemplogger.service`
4. Add the following to the configuration document:
```
[Service]
Environment="VERBOSITY=0"
Environment="LOGDIR={Parent Path}/HeatstrokeCanary/templog"
Environment="SVGARGS="
```
5. Restart the daemon: `sudo systemctl restart goveebttemplogger.service`

### ServerPi

The ServerPi, which can be executed via `python server.py`, requires the following dependencies:

* <b>flask</b>: For WebGUI implementation and handling CanaryPi HTTP posts.
* <b>pymongo==3.4.0</b>: Used to implement the user-preference and event databases.
* <b>json</b>: Used to interpret CanaryPi HTTP posts.
* <b>twilio</b>: Used to send SMS notifications to users.