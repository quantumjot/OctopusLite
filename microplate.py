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

import numpy as np



def serpentine(rows, columns):
    """ Make a serpentine pattern """

    rows = range(rows)
    columns = range(columns)

    pos = []
    for row in rows:
        for column in columns:
            pos.append((row,column))
        columns.reverse()

    return pos


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
        self.width_mm = 85.0
        self.height_mm = 127.5

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


    def create(self,
               num_positions_per_well=1,
               z_pos=0.,
               fov_mm=(0.530,0.400)):

        self._wells = []

        # make the serperntine pattern
        pattern = serpentine(self.rows, self.columns)

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






class Microplate24Well(Microplate):
    def __init__(self):
        Microplate.__init__(self)

        self.rows = 4
        self.columns = 6
        self.spacing_mm = 18.9
        self.offset_mm = [14.4, 16.5]
        self.well_diameter_mm = 16.3






def visualise_microplate(plate):
    """ Visualise the positions in a microplate """
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as PathEffects

    fig, ax = plt.subplots(1, figsize=(10,16))

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
    plate = Microplate24Well()
    plate.create(num_positions_per_well=16)

    test_fn = "./data/microplate.pos"
    utils.write_micromanager_stage_positions(test_fn, plate.positions)
    visualise_microplate(plate)
