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


import os
import time
import serial
import json
import logging

# get the logger instance
logger = logging.getLogger('octopuslite_logger')

class SerialWrapper(object):
    """ SerialWrapper

    A simple wrapper around a pyserial interface to enable simple communications
    with hardware devices.


    send_serial_command
    get_serial_answer
    send_and_receive_serial_command


    """
    def __init__(self, port, baud):
        self._port = port
        self._baud = baud

        # open a serial port
        self._ser = serial.Serial(port, baud, timeout=1)

    def __del__(self):
        # make sure we close the serial port at exit
        if self._ser:
            if self._ser.is_open: self._ser.close()

    def send_serial_command(self, cmd):
        # assert(isinstance(cmd, basestring))
        if not cmd.endswith("\r"): cmd+="\r"
        try:
            self._ser.write(cmd)
        except serial.SerialTimeoutException:
            logger.error("Serial write timeout (port: {})".format(self._port))
        return

    def flush(self):
        """ flush the input """
        self._ser.reset_output_buffer()


    def get_serial_answer(self):
        try:
            answer = self._ser.readline()
        except:
            logger.error("Serial read failed")
        return answer

    def send_and_receive_serial_command(self, cmd):
        self.send_serial_command(cmd)
        return self.get_serial_answer()





class Timeout(object):
    """ Timeout

    A simple, non blocking, timeout timer.
    """
    def __init__(self, timeout_seconds=5):
        self._start = time.time()
        self._timeout = float(timeout_seconds)

    @property
    def active(self):
        return self.elapsed < self._timeout

    @property
    def elapsed(self):
        return time.time() - self._start



def read_micromanager_stage_positions(filename):
    """ read a list of micromanager stage positions, store these as a list """
    with open(filename, 'r') as stage_positions:
        pos = json.load(stage_positions)

    positions = []

    # iterate over each position in the list, grab the devices and positions
    for p in pos['map']['StagePositions']['array']:
        devs = p['DevicePositions']['array']
        sp = {d['Device']['scalar']: d['Position_um']['array'] for d in devs}
        positions.append(sp)

    return positions


def read_experiment_params(filename="params.json"):
    with open(filename, 'r') as exp_params:
        params = json.load( exp_params)
    return params

def check_and_makedir(folder_name):
    """ Does a directory exist? if not create it. """
    if not os.path.isdir(folder_name):
    	os.mkdir(folder_name)
    	return False
    else:
    	return True



if __name__ == "__main__":
    pass
