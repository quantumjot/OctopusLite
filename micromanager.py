#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:     OctopusLite
# Purpose:  OctopusLite is a simple script based timelapse acquisition. It
#           uses other open-source hardware control software for image
#           acquisition and some hardware synchronisation. Mostly takes care
#           of stage control for long timelapse experiments. Integrates with
#           real-time image processing software via RPC.
#
# Authors:  Alan R. Lowe (arl) a.lowe@ucl.ac.uk
#
# License:  See LICENSE.md
#
# Created:  09/08/2019
#-------------------------------------------------------------------------------

__author__ = 'Alan R. Lowe'
__email__ = 'a.lowe@ucl.ac.uk'


import sys
import logging


sys.path.append("C:\\Program Files\\Micro-Manager-2.0gamma")
import MMCorePy


# get the logger instance
logger = logging.getLogger('octopuslite_logger')


def setup_micromanager():
    # TODO(arl): load a micromanager config from file?

    mmc = MMCorePy.CMMCore()  # Instance micromanager core
    mmc_version = mmc.getVersionInfo()

    logger.info("Imported MMCore v{}".format(mmc_version))

    # set up the camera and niji
    mmc.loadDevice('Grasshopper3', 'PointGrey', 'Grasshopper3 GS3-U3-91S6M_14103093')
    mmc.loadDevice('COM9', 'SerialManager', 'COM9')
    mmc.loadDevice('niji', 'BlueboxOptics_niji', 'niji')

    # set up serial port for niji
    mmc.setProperty('COM9', 'AnswerTimeout', '500.0000')
    mmc.setProperty('COM9', 'BaudRate', '115200')
    mmc.setProperty('COM9', 'DataBits', '8')
    mmc.setProperty('COM9', 'DelayBetweenCharsMs', '0.0000')
    mmc.setProperty('COM9', 'Fast USB to Serial', 'Disable')
    mmc.setProperty('COM9', 'Handshaking', 'Off')
    mmc.setProperty('COM9', 'Parity', 'None')
    mmc.setProperty('COM9', 'StopBits', '1')
    mmc.setProperty('COM9', 'Verbose', '1')
    mmc.setProperty('niji', 'Port', 'COM9')

    # initialize all of the devices
    mmc.initializeAllDevices()

    # make sure we use 2x2 binning on the camera as default
    mmc.setProperty('Grasshopper3', 'Use Advanced Mode?', 'Yes')
    mmc.setProperty('Grasshopper3', 'Format-7 Mode', 'Mode-1')
    mmc.setProperty('Grasshopper3', 'PixelType', '8-bit')

    # niji settings
    mmc.setProperty('niji', 'Channel3Intensity', '20')  # GFP
    mmc.setProperty('niji', 'Channel5Intensity', '20')  # RFP
    mmc.setProperty('niji', 'Channel6Intensity', '20')  # iRFP
    mmc.setProperty('niji', 'Channel3State', '0')
    mmc.setProperty('niji', 'Channel5State', '0')
    mmc.setProperty('niji', 'Channel6State', '0')
    mmc.setProperty('niji', 'TriggerSource', 'Internal')
    mmc.setProperty('niji', 'State', '0')

    # set the camera to be the grasshopper
    mmc.setCameraDevice('Grasshopper3')

    return mmc


if __name__ == "__main__":
    pass
