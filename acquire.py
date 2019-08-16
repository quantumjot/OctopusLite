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
import prior
import triggers

import tifffile
# import numpy as np


# get the logger instance
logger = logging.getLogger('octopuslite_logger')



class AcquisitionConfig(object):
    """ AcquisitionConfig

    A configuration for a timelapse acquisition.
    """

    def __init__(self):
        self.num_images = 0
        self.delay_s = 240
        self._triggers = []
        self._positions = []
        self._params = None

    @property
    def triggers(self):
        return self._triggers

    @property
    def stage_positions(self):
        return self._positions

    @property
    def path(self):
        return self._path


    def from_dict(self, params):
        """ set up the configuration from a dictionary """
        assert(isinstance(params, dict))

        # store the parameters in an internal dictionary
        self._params = params

        # set some useful params
        self.num_images = params.get("num_images", 1)
        self.delay_s = params.get("delay_s", 240)

        # set up the data folder
        self._path = params.get("data_folder", "")

    def build_triggers(self):
        """ build a list of triggers using the config """
        self._triggers = []
        for t in self._params["triggers"]:
            logger.info("Adding trigger: {}".format(t.keys()[0]))
            self._triggers.append(triggers.Trigger(t))

    def build_positions(self):
        """ build a list of positions """
        position_fn = self._params["stage_positions"]
        position_list = utils.read_micromanager_stage_positions(position_fn)

        # make a list of positions
        self._positions = []
        for p, pos in enumerate(position_list):
            x = int(pos['XYStage'][0])
            y = int(pos['XYStage'][1])
            z = int(pos['ZStage'][0] * 10.0)    # TODO(arl): get Z-resolution
            self._positions.append((x,y,z))


    def initialize_acquisition(self, **kwargs):
        """ Initialize the acquisition """
        for trigger in self.triggers:
            trigger.initialize(**kwargs)

    @staticmethod
    def load(filename="params.json"):
        """ load a config from an experimental parameter file """

        # read the parameters from the file
        logger.info("Reading experiment configuration file...")
        params = utils.read_experiment_params(filename)
        config = AcquisitionConfig()
        config.from_dict(params)

        # set up the triggers
        logger.info("Configuring triggers...")
        config.build_triggers()

        # read the stage positions
        logger.info("Configuring stage positions...")
        config.build_positions()

        return config










def setup_micromanager():
    import sys
    sys.path.append("C:\\Program Files\\Micro-Manager-2.0gamma")
    import MMCorePy
    mmc = MMCorePy.CMMCore()  # Instance micromanager core
    mmc.getVersionInfo()

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







def setup_logger(log_path):
    # if we don't have any handlers, set one up
    if not logger.handlers:
        # configure stream handler
        logfmt = '[%(levelname)s][%(asctime)s] %(message)s'
        log_formatter = logging.Formatter(logfmt, datefmt='%Y/%m/%d %I:%M:%S %p')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)

        log_file = os.path.join(log_path, 'acquisition_log.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)

        logger.setLevel(logging.DEBUG)

        return log_file




def image_fn(im_num=0, pos_num=0, channel_num=0, z_num=0):
    """ create a filename based on the image number, position, channel and z

    Micro-manager format:
        img_channel000_position001_time000000002_z000.tif
    """
    filename = "img_channel{0:03d}_position{1:03d}_time{2:09d}_z{3:03d}.tif"
    return filename.format(channel_num, pos_num, im_num, z_num)







# def acquire(position_list, num_images=500, period_s=4*60):
def acquire(config):

    # # make sure that the destination folder exists
    utils.check_and_makedir(config.path)

    # set up micromanager
    mmc = setup_micromanager()
    log_file = setup_logger(config.path)

    # set up the stage controller
    proscan = prior.ProScanController()

    # set the image counter to zero
    image_num = 0

    # make a banner for the log file
    logger.info("=============================================================")
    logger.info(" NEW IMAGE ACQUISITION ")
    logger.info("=============================================================")


    # make a list of positions
    for p, pos in enumerate(config.stage_positions):
        # create folders for those positions
        pos_pth = os.path.join(config.path, "Pos{}".format(p))
        logger.info("Creating position folder {}".format(pos_pth))
        utils.check_and_makedir(pos_pth)

    # initialize all of the triggers
    config.initialize_acquisition(mmc=mmc, prior=proscan)

    # make an image cache
    w, h = mmc.getImageWidth(), mmc.getImageHeight()


    # loop over the images to be collected
    while image_num < config.num_images:

        # give the user a status update
        logger.info("Acquiring image set {} of {}".format(image_num, config.num_images))

        # start an acquisition by turning off the joystick
        # proscan.disable_joystick()

        # reset the cache
        cache = []

        # run the acquisition here
        timeout = utils.Timeout(timeout_seconds=config.delay_s)
        for p, pos in enumerate(config.stage_positions):
            # select the correct folder
            pos_pth = os.path.join(config.path, "Pos{}".format(p))

            # send the stage to the correct position
            proscan.goto(pos)

            # cycle through each of the triggers in order
            for t, trigger in enumerate(config.triggers):
                channel_fn = os.path.join(pos_pth, image_fn(image_num, p, t))

                logger.info(" - Acquiring {} image...".format(trigger.name))
                channel_im = trigger()
                # store the image in the cache
                cache.append((channel_fn, channel_im))

        # return to the initial position
        proscan.goto(config.stage_positions[0])

        # turn the joystick back on
        # proscan.enable_joystick()

        # now write out the images while we're waiting
        logger.info("Writing images to disk from cache...")
        for fn, image in cache:
            logger.info(" - "+fn)
            # tifffile.imwrite(fn, image.astype('uint8'), compress=6)
            tifffile.imwrite(fn, image)

        while timeout.active:
            remaining = int(config.delay_s-timeout.elapsed)
            if remaining % 30 == 0:
                logger.info("Time remaining: {}s".format(remaining))
                time.sleep(1)

        image_num+=1


if __name__ == "__main__":

    # load the configuration and start the acquistion
    config = AcquisitionConfig.load()
    acquire(config)
