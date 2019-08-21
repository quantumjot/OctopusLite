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
import micromanager
# import rpcclient

import tifffile
# import numpy as np


# get the logger instance
logger = logging.getLogger('octopuslite_logger')

# use a consistent naming convention
def image_filename(im_num=0, pos_num=0, channel_num=0, z_num=0):
    """ create a filename based on the image number, position, channel and z

    Micro-manager format:
        img_channel000_position001_time000000002_z000.tif
    """
    filename = "img_channel{0:03d}_position{1:03d}_time{2:09d}_z{3:03d}.tif"
    return filename.format(channel_num, pos_num, im_num, z_num)


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





class AcquisitionObject(object):
    """ AcquisitionObject

    Container for an XYZ position with associated triggers. Takes care of
    position specific functions, such as moving to the position and running
    position specific triggers.

    Can be 'borrowed' by a command server to remotely drive the microscope.

    """
    def __init__(self, acquisitionid):

        self.id = acquisitionid
        self.path = None
        self.position = None
        self.triggers = []
        self.log = []
        self.cache = []

        self._stage_controller = None

        self.num_images = 1
        self._counter = 0

    def __len__(self):
        return len(self.cache)

    @property
    def stage_controller(self): return self._stage_controller
    @stage_controller.setter
    def stage_controller(self, stage_controller):
        assert(isinstance(stage_controller, prior.ProScanController))
        self._stage_controller = stage_controller

    @property
    def folder(self):
        return os.path.join(self.path, "Pos{}".format(self.id))

    @property
    def active(self):
        return self.image_num < self.num_images

    @property
    def image_num(self):
        return self._counter

    def write_log(self):
        """ write a log """
        # TODO(arl):
        with open(os.path.join(self.path, "log.txt", 'w')) as log_file:
            pass

    def write_images(self):
        """ write out images from the cache """
        while self.cache:
            # pop the first and write it out
            fn, image = self.cache.pop(0)
            tifffile.imwrite(fn, image)

    def goto(self):
        """ move to the position """
        self._stage_controller.goto(self.position)

    def acquire(self):
        """ run the acquisition """
        for t, trigger in enumerate(self.triggers):
            channel_img = trigger()
            image_fn = image_filename(self.image_num, self.id, t)
            channel_fn = os.path.join(self.folder, image_fn)
            self.cache.append((channel_fn, channel_img))

        self._counter += 1

    def goto_and_acquire(self):
        """ goto the position and acquire the images """
        logger.info("Acquiring position {} ({:04d}/{:04d})".format(self.id, self.image_num, self.num_images))
        self.goto()
        self.acquire()






class AcquisitionManager(object):
    """ AcquisitionManager

    A manager for timelapse acquisition. Can either be configured once, for a
    static acqusition, or communicate with a server.

    """

    def __init__(self):
        self.num_images = 1
        self.delay_s = 240
        self._params = None
        self._triggers = []

        self.positions = []

        # self.rpcclient = rpcclient.OctopusRPCClient()

    @property
    def path(self):
        return self._path

    @property
    def triggers(self):
        return self._triggers

    @property
    def active(self):
        """ are any of the positions still active? """
        return [acq for acq in self.positions if acq.active]

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
        for pos_id, pos_um in enumerate(position_list):
            x = int(pos_um['XYStage'][0])
            y = int(pos_um['XYStage'][1])
            z = int(pos_um['ZStage'][0] * 10.0)    # TODO(arl): get Z-resolution

            # make an acquisition object
            acq = AcquisitionObject(pos_id)
            acq.position = (x,y,z)
            acq.triggers = self._triggers
            acq.num_images = self.num_images
            acq.path = self.path

            # add the acquisition object to the list of positions
            self.positions.append(acq)

    def initialize_acquisition(self, mmc=None, stage=None):
        """ Initialize the acquisition """

        # initialize the triggers
        for trigger in self.triggers:
            trigger.initialize(mmc=mmc, stage=stage)

        # add the stage controller to the positions
        for acq in self.positions:
            acq.stage_controller = stage

        # make folders for the acquisitions
        for acq in self.positions:
            logger.info("Creating position folder {}".format(acq.folder))
            utils.check_and_makedir(acq.folder)

    def acquire(self):
        # start an acquisition by turning off the joystick
        # proscan.disable_joystick()

        # get the active positions
        for acq in self.active:
            acq.goto_and_acquire()

        # return to the first position to wait
        if self.active: self.active[0].goto()

        # now write out the images
        self.write_images()

        # turn the joystick back on
        # proscan.enable_joystick()

    def write_images(self):
        logger.info("Writing images to disk from cache...")
        for acq in self.positions:
            acq.write_images()

    def write_logs(self):
        logger.info("Writing acquisition logs...")
        for acq in self.positions:
            acq.write_log()

    @staticmethod
    def load_config(filename="params.json"):
        """ load a config from an experimental parameter file """

        # read the parameters from the file
        logger.info("Reading experiment configuration file...")
        params = utils.read_experiment_params(filename)
        manager = AcquisitionManager()
        manager.from_dict(params)

        # set up the triggers
        logger.info("Configuring triggers...")
        manager.build_triggers()

        # read the stage positions
        logger.info("Configuring stage positions...")
        manager.build_positions()

        return manager

    def update(self):
        # self.rpcclient.update(self.positions)
        pass





def acquire(manager):
    # make sure that the destination folder exists
    utils.check_and_makedir(manager.path)

    # set up micromanager
    mmc = micromanager.setup_micromanager()
    log_file = setup_logger(manager.path)

    # set up the stage controller, using device configurations
    devices = [(prior.PriorXYStage, prior.H117EX_config),
               (prior.PriorZStage, prior.FB203E_config)]

    proscan = prior.ProScanController(devices=devices)

    # make a banner for the log file
    logger.info("=============================================================")
    logger.info(" NEW TIME-LAPSE ACQUISITION ")
    logger.info("=============================================================")

    # initialize all of the triggers
    manager.initialize_acquisition(mmc=mmc, stage=proscan)

    # make an image cache
    # w, h = mmc.getImageWidth(), mmc.getImageHeight()

    # loop over the images to be collected
    while manager.active:

        # run the acquisition here
        timeout = utils.Timeout(timeout_seconds=manager.delay_s)

        # run the acquisition
        manager.acquire()

        # send images to command server
        # manager.update()

        while timeout.active:
            if int(timeout.remaining) % 30 == 0:
                logger.info("Remaining: {}s".format(int(timeout.remaining)))
                time.sleep(1)


    logger.info("Acquitison complete.")
    manager.write_logs()



if __name__ == "__main__":

    # load the configuration and start the acquistion
    manager = AcquisitionManager.load_config()
    acquire(manager)
