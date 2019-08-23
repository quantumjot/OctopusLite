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

import logging

# get the logger instance
logger = logging.getLogger('octopuslite_logger')

class FilterWheel(object):
    """ FilterWheel

    Wrapper for the filter wheel. Takes care of maintaining the position,
    homing and moving.

    """
    def __init__(self):
        self._position = -1     # set this to 'home' on initialization
        self._num_positions = 6
        self._steps_per_position = 60000
        self._mmc = None

    @property
    def position(self):
        return self._mmc.getPosition("Fast Filter Wheel")

    def initialize(self, mmc=None):
        """ intialize the wheel and home it """
        self._mmc = mmc
        self.goto(0)

    def goto(self, position):
        if self._position == position: return
        pos_um = float((position % 6) * self._steps_per_position)
        self._mmc.setPosition("Fast Filter Wheel", pos_um)
        self._mmc.waitForDevice("Fast Filter Wheel")
        self._position = position
        logger.info("Filter position: {2.2f}um".format(self.position))


if __name__ == "__main__":
    pass
