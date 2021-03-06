'''
Created on Jun 16, 2010

@author: alexander
'''
from etsproxy.traits.api import \
    HasTraits, Float, Array, implements, Property, cached_property, Instance, Enum, \
    Dict, Bool, Int, List

import numpy as np

import scipy as sp

from os.path import join

from math import pi


class GeoST(HasTraits):
    '''Geometry definition of the slab test with round load introduction area
    corresponding to steel plate in the test setup.
    '''

    #-----------------------------------------------------------------
    # geometric parameters of the slab
    #-----------------------------------------------------------------
    # NOTE: coordinate system is placed where the symmetry planes cut each other,
    # i.e the center of the load introduction area (=middle of steel plate)

    # discretization of total slab in x- and y-direction (region 'L')
    #
    shape_xy = Int(14, input=True)

    # discretization of the load introduction plate (region 'R')
    #
    shape_R = Int(2, input=True)

    # ratio of the discretization, i.e. number of elements for each region
    #
    r_ = Property(depends_on='+input')
    @cached_property
    def _get_r_(self):
        return 1.* self.shape_R / self.shape_xy

    #-----------------
    # geometry:
    #-----------------

    # x and y-direction
    #
    length_quarter = Float(0.625, input=True)

    # Radius of load introduction plate
    #
    radius_plate = Float(0.10, input=True)

    # z-direction
    #
    thickness = Float(0.06, input=True)

    # specify offset (translation) for the plain concrete patch (if used)
    # in global coordinates
    #
    zoffset = Float(0.0, input=True)

#    # used regular discretization up to y = L1
#    # (by default use regular discretization up to support)
#    #
#    L1 = Float(0.30, input = True)

    def __call__(self, pts):
        print '*** geo_slab_test called ***'

        x_, y_, z_ = pts.T

        R = self.radius_plate
        L = self.length_quarter
        t = self.thickness

        #-------------------------------------------
        # transformation to global coordinates
        #-------------------------------------------

        x = np.zeros_like(x_)
        y = np.zeros_like(y_)
        z = z_ * t

        r_ = self.r_

        # 1. quadrant
        #
        bool_x = x_ >= r_
        bool_y = y_ >= r_
        bool_xy = bool_x * bool_y
        idx_xy = np.where(bool_xy == 1.)[0]
        x[ idx_xy ] = R + (x_[ idx_xy ] - r_) / (1 - r_) * (L - R)
        y[ idx_xy ] = R + (y_[ idx_xy ] - r_) / (1 - r_) * (L - R)

        # 2. quadrant
        #
        bool_x = x_ >= r_
        bool_y = y_ <= r_
        bool_xy = bool_x * bool_y
        idx_xy = np.where(bool_xy == 1.)[0]
        xR = R * np.cos(y_[ idx_xy ] / r_ * np.pi / 4.)
        x[ idx_xy ] = xR + (x_[ idx_xy ] - r_) / (1 - r_) * (L - xR)
        y[ idx_xy ] = y_[ idx_xy ] / r_ * R

        # 4. quadrant
        #
        bool_x = x_ <= r_
        bool_y = y_ >= r_
        bool_xy = bool_x * bool_y
        idx_xy = np.where(bool_xy == 1.)[0]
        x[ idx_xy ] = x_[ idx_xy ] / r_ * R
        yR = R * np.cos(x_[ idx_xy ] / r_ * np.pi / 4.)
        y[ idx_xy ] = yR + (y_[ idx_xy ] - r_) / (1 - r_) * (L - yR)

        # 3. quadrant (mesh in load introduction area)
        #
        bool_x = x_ <= r_
        bool_y = y_ <= r_
        bool_xy = bool_x * bool_y
        idx_xy = np.where(bool_xy == 1.)[0]
        xR = R * np.cos(y_[ idx_xy ] / r_ * np.pi / 4.)
        yR = R * np.cos(x_[ idx_xy ] / r_ * np.pi / 4.)
        x[ idx_xy ] = x_[ idx_xy ] / r_ * xR
        y[ idx_xy ] = y_[ idx_xy ] / r_ * yR

        # rotate coordinates in order to have the load introduction plate at the
        # top left corner of the grid
        # and add offset for translation
        #
        zoffset = self.zoffset
        pts = np.c_[L - x, L - y, z + zoffset]
#        pts = np.c_[x, y, z]

        # switch order of the points in order to start in the opposite corner of the slab
        # instead of the center of the load introduction plate. The opposite center of the
        # slab corresponds to the origin of the slab in the model 'sim_st' (as generated by
        # the FEGrid mesh;
        #
        pts = pts[::-1]
        # switch back the order of the z-axis in order to maintain starting from 0
        #
        pts[:, -1] = pts[:, -1][::-1]

#        print pts
        return pts




if __name__ == '__main__':

    from etsproxy.mayavi import mlab

    st = GeoST()

    st = GeoST(shape_xy=11,
               shape_R=2,
               shape_z=2,
               radius_plate=0.04,  # D=8cm
               length_quarter=0.40,  # L=80cm
               thickness=0.02)

#    shape_xy = 26
#    st.shape_R = 5

    # discretization in z-direction
    # (thickness direction):
    #
    shape_z = 0

    grid = np.mgrid[0:1:complex(0, st.shape_xy + 1),
                    0:1:complex(0, st.shape_xy + 1),
                    0:1:complex(0, shape_z + 1)]

    X, Y, Z = grid

    gpoints = np.c_[ X.flatten(), Y.flatten(), Z.flatten() ]

    mlab.figure(bgcolor=(1., 1., 1.,))
    fp1 = st(gpoints)

    # save x,y,z - node coordinates of FE-mesh to file
    print fp1.shape
    from matresdev.db.simdb import SimDB
    simdb = SimDB()
    import os
    simdata_dir = os.path.join(simdb.simdata_dir, 'SimST')
    if os.path.isdir(simdata_dir) == False:
        os.makedirs(simdata_dir)
    filename = os.path.join(simdata_dir, 'FE-mesh_ST-80cm_nxy11.csv')
    np.savetxt(filename, fp1, delimiter=';')
    print 'xyz_arr saved to file %s' % (filename)

    mlab.points3d(fp1[:, 0], fp1[:, 1], fp1[:, 2],
                   scale_factor=0.01 ,
                   resolution=8)
    mlab.axes()
    mlab.show()
