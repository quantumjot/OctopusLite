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
import logging

import utils


# get the logger instance
logger = logging.getLogger('octopuslite_logger')

# definitions
DEVICE_OK = "0\r"
STAGE_AXES = ("X","Y","Z","S")


# configurations
class H117EX_config:
    axis = "S"
    name = "H117EX XY Stage"
    max_speed = 100
    acceleration = 100
    s_curve = 100
    encoders = True


class FB203E_config:
    axis = "Z"
    name = "FB203E Z Stage"
    max_speed = 100
    acceleration = 100
    s_curve = 100
    encoders = True
    encoder_window = 1
    servo = True
    backlash = False





class ProScanController(object):
    """ ProScanController

    This class deals with communications with the ProScan III controller via
    serial port. This is used to access stage movement and TTL triggering for
    light sources.

    Notes:
        DONE(arl): implement settings checking/updating
        DONE(arl): check TTL pulse generation

    """

    def __init__(self, port="COM8", baud=9600, devices=[]):

        # set up the serial interface
        self._ser = utils.SerialWrapper(port, baud)

        # initialize the controller
        ret = self._ser.send_and_receive_serial_command("COMP")
        if ret != DEVICE_OK:
            logger.error("ProScan controller is not in Standard mode")
            raise Exception("ProScan controller is not in Standard mode")

        # instantiate the devices with the config and serial port
        self._devices = []
        for device, device_config in devices:
            self._devices.append(device(self._ser, device_config))

        # set all TTL pins to 0
        for pin in range(4):
            self.ttl(pin=pin, state=False)

    def goto(self, position):
        """ move the stage to a position """

        #TODO(arl): proper formatting of the position string
        p_str = "{}, {}, {}".format(position[0], position[1], position[2])
        # self.position
        logger.info("Sending stage to position: {}".format(p_str))

        # go to the absolute position
        self._ser.send_and_receive_serial_command("G {}".format(p_str))

        # block until we reach the position or timeout
        timeout = utils.Timeout()
        while self.busy and timeout.active:
            time.sleep(0.1) # sleep for 100 ms

        # break if we cannot reach the position
        if self.busy and not timeout.active:
            logger.error("Stage move timed out. Exiting")
            raise Exception("Stage move failed")

    def ttl(self, **kwargs):
        raise DeprecationWarning("Use prior.TTL")
        self.TTL(**kwargs)

    def TTL(self, pin=0, state=False):
        """ change the state of one of the ttl pins """
        assert(isinstance(pin, int) and pin>=0 and pin<4)
        assert(isinstance(state, bool))

        # NOTE(arl): the TTL command does not return any string?
        # NOTE(arl): IT DOES!
        ttl_str = "TTL {}, {}".format(pin, int(state))
        # ret = self._ser.send_and_receive_serial_command(ttl_str)
        # if ret != DEVICE_OK:
        #     logger.error("TTL pulse (pin: {} -> {}) failed".format(pin, state))

        # speed this up by not waiting for an answer and flush the serial port
        self._ser.send_serial_command(ttl_str)
        self._ser.flush()

    @property
    def position(self):
        """ get the position of the stage """
        p_str = self._ser.send_and_receive_serial_command("P")
        # logger.info("Current stage position: {}".format(p_str))
        return p_str

    @property
    def info(self):
        """ return information about the contoller """
        pass

    @property
    def busy(self):
        """ return the busy status of the controller """
        ret = self._ser.send_and_receive_serial_command("$")
        busy = [int(busy_axis) for busy_axis in ret.split()]
        status = sum(busy)
        if status == 0:
            return False

        # if it is busy, log which axes are busy, add 64 (higher than any bit
        # returned, so that python returns a string repr that is long enough)
        moving = bin(status+64)[::-1]
        for i, axis in enumerate(STAGE_AXES[:3]):
            if moving[i] > 0:
                logger.info("Stage axis {} is still moving...".format(axis))

        return True

    def enable_joystick(self):
        """ enable the joystick """
        ret = self._ser.send_and_receive_serial_command("J")
        if ret != DEVICE_OK:
            logger.error("Joystick enable failed.")

    def disable_joystick(self):
        """ disable the joystick """
        ret = self._ser.send_and_receive_serial_command("H")
        if ret != DEVICE_OK:
            logger.error("Joystick disable failed.")





class PriorStage(object):
    """ PriorStage

    Generic Prior stage object. Deals with configuration only. All stage
    movement is handled by the ProScanController object.

    """
    def __init__(self, ser, config):
        self._ser = ser
        self._axis = None

        # run the config
        cfg_params = [c for c in config.__dict__ if not c.startswith('__')]
        logger.info("Setting stage parameters for {}".format(config.name))
        for p in cfg_params:
            logger.info("{} - > {}".format(p, getattr(config,p)))
            # setattr(self, p, getattr(config,p))

    def _set(self, cmd):
        """ shortuct to set and test successful parameter update """
        ret = self._ser.send_and_receive_serial_command(cmd)
        if ret != DEVICE_OK:
            logger.error("Command: {} failed.".format(cmd))
            raise Exception("Command: {} failed.".format(cmd))

    def _read(self, cmd):
        """ shortcut to read paramter """
        pass

    @property
    def axis(self): return self._axis
    @axis.setter
    def axis(self, axis):
        if axis not in STAGE_AXES:
            logger.error("Stage axis {} not recognized".format(axis))
            raise Exception

    @property
    def resolution(self):
        """ get the resolution """
        cmd = "RES, {}".format(self.axis)
        ret = self._ser.send_and_receive_serial_command(cmd)
        logger.info("Stage axis {} resolution: {}".format(self.axis, ret))
        return ret

    # TODO(arl): read these from the stage controller rather than assuming
    # they're what we set them to
    @property
    def max_speed(self): return self._max_speed
    @property
    def acceleration(self): return self._acceleration
    @property
    def s_curve(self): return self._s_curve
    @property
    def encoder(self): return self._encoder
    @property
    def backlash(self): return self._backlash
    @property
    def encoder_window(self): return self._encoder_window
    @property
    def servo(self): return self._servo

    @resolution.setter
    def resolution(self, resolution):
        """ set the resolution """
        # NOTE(arl): don't really want to change this, so no code here
        pass

    @max_speed.setter
    def max_speed(self, max_speed):
        assert(max_speed>0 and max_speed<=100)
        cmd = "SM{}, {}".format(self.axis, max_speed)
        self._set(cmd)
        self._max_speed = max_speed

    @acceleration.setter
    def acceleration(self, acceleration):
        assert(acceleration>0 and acceleration<=100)
        cmd = "SA{}, {}".format(self.axis, max_speed)
        self._set(cmd)
        self._acceleration = acceleration

    @s_curve.setter
    def s_curve(self, s_curve):
        assert(s_curve>0 and s_curve<=100)
        cmd = "SC{}, {}".format(self.axis, max_speed)
        self._set(cmd)
        self._s_curve = s_curve

    @encoder.setter
    def encoder(self, encoder):
        assert(isinstance(encoder, bool))
        cmd = "ENCODER {}, {}".format(self.axis, int(encoder))
        self._set(cmd)
        self._encoders = encoder

    @backlash.setter
    def backlash(self, backlash):
        assert(isinstance(backlash, bool))
        cmd = "BL{}H, {}".format(self.axis, int(backlash))
        self._set(cmd)
        self._backlash = backlash

    @encoder_window.setter
    def encoder_window(self, encw):
        assert(encw>1 and encw<=2)
        cmd = "ENCW {}, {}".format(self.axis, encw)
        self._set(cmd)
        self._s_curve = s_curve

    @servo.setter
    def servo(self, servo):
        assert(isinstance(servo, bool))
        cmd = "SERVO {}, {}".format(self.axis, int(servo))
        self._set(cmd)
        self._servo = servo





class PriorXYStage(PriorStage):
    """ Container object for XY Stage """
    def __init__(self, ser, config):
        PriorStage.__init__(self, ser, config)





class PriorZStage(PriorStage):
    """ Container object for Z Stage """
    def __init__(self, ser, config):
        PriorStage.__init__(self, ser, config)





if __name__ == "__main__":
    pass
