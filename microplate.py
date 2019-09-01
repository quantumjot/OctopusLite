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

import utils

import heapq
import numpy as np


MICROPLATE_WIDTH_MM = 127.5
MICROPLATE_HEIGHT_MM = 85.0
CAMERA_FOV_MM = (0.53, 0.40)


def serpentine(rows, columns):
    """ Make a serpentine pattern """

    rows = range(rows)
    columns = range(columns)

    pos = []

    for column in columns:
        for row in rows:
            pos.append((row,column))
        rows.reverse()

    return pos


def custom_plate_config(raw_positions):
    """ positions should be 1-6, A-D e.g. 3C """
    assert(isinstance(raw_positions, list))

    # # make sure we don't have any duplicates and order them
    raw_positions = list(set(raw_positions))
    raw_positions.sort(key=lambda p: p[1])

    COLUMNS = ['A','B','C','D']
    index_to_row_col = lambda s: (int(s[0])-1, int(COLUMNS.index(s[1])))

    pos = []

    for position in raw_positions:
        row, col = index_to_row_col(position)
        assert(row>=0 and row<6 and col>=0 and col<4)
        pos.append((row,col))

    pos = greedy_optimize(pos)

    return pos



def greedy_optimize(positions):
    """ do a greedy optimisation to find the optimal layout """
    # TODO(arl): argh the travelling salesman problem
    return positions






class MicroplateWell(object):
    """ MicroplateWell

    Object to store a microplate well.
    """
    def __init__(self, x_mm, y_mm, diameter_mm):
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.diameter_mm = diameter_mm

        self.positions = []

    @property
    def radius_mm(self):
        return self.diameter_mm / 2.

    @property
    def relative_positions(self):
        pass




class Microplate(object):
    """ Microplate

    Object to deal with positioning microscope for multiwell plate
    acquisitions. This is an abstract class which should be subclassed for
    different plate configurations.

    Defaults to a serpentine configuration

    """
    def __init__(self):
        self.width_mm = MICROPLATE_WIDTH_MM
        self.height_mm = MICROPLATE_HEIGHT_MM

        self.offset_mm = None
        self.spacing_mm = None

        self.rows = None
        self.columns = None

        self._wells = []

    @property
    def num_wells(self):
        return self.rows*self.columns

    @property
    def wells(self):
        """ Return the well centres """
        return self._wells

    @property
    def positions(self):
        positions = []
        for well in self.wells:
            positions+=well.positions
        return positions


    def full_plate_config(self):
        # make the serperntine pattern
        return serpentine(self.rows, self.columns)

    def custom_plate_config(self, use_positions):
        return custom_plate_config(use_positions)



    def create(self,
               use_positions=[],
               num_positions_per_well=1,
               z_pos=0.,
               fov_mm=CAMERA_FOV_MM):

        self._wells = []

        if use_positions:
            pattern = self.custom_plate_config(use_positions)
        else:
            pattern = self.full_plate_config()

        # set up the wells for the given pattern
        for px, py in pattern:
            # set up the wells according to the plate configuration
            x0, y0 = self.offset_mm
            x = x0 + px*self.spacing_mm
            y = y0 + py*self.spacing_mm

            # add the well object
            well = MicroplateWell(x, y, self.well_diameter_mm)
            self._wells.append(well)

        if num_positions_per_well < 1: return

        # estimate the number of rows and columns for the number of positions
        # per well
        n = np.ceil(np.sqrt(num_positions_per_well)).astype('int')
        pattern = serpentine(n,n)[:num_positions_per_well]

        for well in self.wells:
            well.positions = []
            x0, y0 = well.x_mm - n*fov_mm[0]/2., well.y_mm - n*fov_mm[1]/2.
            for px, py in pattern:
                x = x0 + px*fov_mm[0]
                y = y0 + py*fov_mm[1]
                well.positions.append((x, y, z_pos))


    def visualise(self):
        """ proxy for visualising the plate """
        visualise_microplate(self)

    def export(self, filename):
        """ export the positions to micromanager """
        utils.write_micromanager_stage_positions(filename, self.positions, use_Z=False)






class Microplate24Well(Microplate):
    def __init__(self):
        Microplate.__init__(self)

        self.rows = 6
        self.columns = 4
        self.spacing_mm = 18.9
        self.offset_mm = [16.5, 14.4]
        self.well_diameter_mm = 16.3






def visualise_microplate(plate):
    """ Visualise the positions in a microplate """
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as PathEffects

    fig, ax = plt.subplots(1, figsize=(8,5))

    # create a microplate boundary
    r = plt.Rectangle((0,0), plate.width_mm, plate.height_mm, fill=False,
                  edgecolor='k', linewidth=3)
    ax.add_artist(r)

    travel = []

    # now create the wells
    for i, well in enumerate(plate.wells):
        x, y = well.x_mm, well.y_mm
        travel.append((x,y))
        r = well.radius_mm
        c = plt.Circle((x, y), r, edgecolor='k', fill=False)
        ax.add_artist(c)
        txt = ax.text(x-r, y-r, str(i+1), color='k')

        # now plot the positions for imaging
        x, y, z = zip(*well.positions)
        plt.plot(x, y, 'b.-')

    tx, ty = zip(*travel)
    plt.plot(tx, ty, 'r:')

    plt.axis("image")
    plt.xlim([-5, plate.width_mm+5])
    plt.ylim([-5, plate.height_mm+5])
    plt.show()


if __name__ == "__main__":
    pos_list = ['1A','2A','3A','4B','6C','2D','4A']
    plate = Microplate24Well()
    # plate.create(num_positions_per_well=16)
    plate.create(use_positions=pos_list)

    # test_fn = "./data/microplate.pos"
    # plate.export(test_fn)

    plate.visualise()
