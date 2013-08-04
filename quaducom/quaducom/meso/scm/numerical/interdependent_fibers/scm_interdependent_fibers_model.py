'''
Created on 12 May 2013

@author: Q
'''

# Copyright (c) 2009, IMB, RWTH Aachen.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in simvisage/LICENSE.txt and may be redistributed only
# under the conditions described in the aforementioned license.  The license
# is also available online at http://www.simvisage.com/licenses/BSD.txt
#
# Thanks for using Simvisage open source!
#
# Created on Oct 21, 2011 by: rch

from etsproxy.traits.api import \
    HasTraits, Instance, Int, Array, List, \
    cached_property, Property, Float
from interpolator import Interpolator
from stats.misc.random_field.random_field_1D import RandomField
from operator import attrgetter
import numpy as np
from scipy.interpolate import interp1d
from scipy.optimize import brentq
import copy
from quaducom.meso.homogenized_crack_bridge.elastic_matrix.reinforcement import Reinforcement, ContinuousFibers
from stats.pdistrib.weibull_fibers_composite_distr import WeibullFibers
from quaducom.meso.homogenized_crack_bridge.elastic_matrix.hom_CB_elastic_mtrx import CompositeCrackBridge
from quaducom.meso.homogenized_crack_bridge.elastic_matrix.hom_CB_elastic_mtrx_view import CompositeCrackBridgeView
from spirrid.rv import RV
from matplotlib import pyplot as plt
from math import pi


class CB(HasTraits):
    '''crack bridge class - includes informations about position,
    stress range and evaluates the stress and strain profiles in the
    composite components'''
    interpolator = Instance(Interpolator)
    position = Float
    Ll = Float
    Lr = Float
    x = Array
    crack_load_sigma_c = Float

    max_sigma_c = Property(Float, depends_on='Ll, Lr')
    @cached_property
    def _get_max_sigma_c(self):
        return self.interpolator.interpolate_max_sigma_c(self.Ll, self.Lr)

    def get_epsf_x_w(self, load):
        '''
        evaluation of matrix strain profile
        '''
        return self.interpolator.interpolate_mu_epsf(load, self.x, self.Ll, self.Lr)

    def get_epsm_x_w(self, load):
        '''
        evaluation of matrix strain profile
        '''
        return self.interpolator.interpolate_epsm(load, self.x, self.Ll, self.Lr)


class SCM(HasTraits):
    '''Stochastic Cracking Model - compares matrix strength and stress,
    inserts new CS instances at positions, where the matrix strength
    is lower than the stress; evaluates stress-strain diagram
    by integrating the strain profile along the composite'''

    length = Float(desc='composite specimen length')
    nx = Int(desc='number of discretization points')
    CB_model = Instance(CompositeCrackBridge)
    load_sigma_c_arr = Array

    interpolator = Instance(Interpolator)
    def _interpolator_default(self):
        return Interpolator(CB_model=self.CB_model,
                            load_sigma_c_arr=self.load_sigma_c_arr,
                            length=self.length, n_w=50, n_BC=6, n_x=50
                            )

    sigma_c_crack = List
    cracks_list = List

    x_arr = Property(Array, depends_on='length, nx')
    @cached_property
    def _get_x_arr(self):
        # discretizes the specimen length
        return np.linspace(0., self.length, self.nx)

    random_field = Instance(RandomField)

    matrix_strength = Property(depends_on='random_field.+modified')
    @cached_property
    def _get_matrix_strength(self):
        # evaluates a random field
        # realization and creates a spline reprezentation
        rf = self.random_field.random_field
        rf_spline = interp1d(self.random_field.xgrid, rf)
        return rf_spline(self.x_arr)

    def sort_cbs(self):
        # sorts the CBs by position and adjusts the boundary conditions
        # sort the CBs
        cb_list = self.cracks_list[-1]
        crack_position = cb_list[-1].position
        cb_list = sorted(cb_list, key=attrgetter('position'))
        # find idx of the new crack
        for i, crack in enumerate(cb_list):
            if crack.position == crack_position:
                idx = i
        # specify the boundaries
        if idx != 0:
            # there is a crack at the left hand side
            cbl = cb_list[idx - 1]
            cb = cb_list[idx]
            cbl.Lr = (cb.position - cbl.position) / 2.
            cb.Ll = cbl.Lr
        else:
            # the new crack is the first from the left hand side
            cb_list[idx].Ll = cb_list[idx].position

        if idx != len(cb_list) - 1:
            # there is a crack at the right hand side
            cb, cbr = cb_list[idx], cb_list[idx + 1]
            cbr.Ll = (cbr.position - cb.position) / 2.
            cb.Lr = cbr.Ll
        else:
            # the new crack is the first from the right hand side
            cb_list[idx].Lr = self.length - cb_list[idx].position

        # specify the x range and stress profile for
        # the new crack and its neighbors
        idxs = [idx - 1, idx, idx + 1]
        if idx == 0:
            idxs.remove(-1)
        if idx == len(cb_list) - 1:
            idxs.remove(len(cb_list))
        for idx in idxs:
            mask1 = self.x_arr >= (cb_list[idx].position - cb_list[idx].Ll)
            if idx == 0:
                mask1[0] = True
            mask2 = self.x_arr <= (cb_list[idx].position + cb_list[idx].Lr)
            cb_list[idx].x = self.x_arr[mask1 * mask2] - cb_list[idx].position
        self.cracks_list[-1] = cb_list

    def cb_list(self, load):
        if len(self.cracks_list) is not 0:
            idx = np.sum(np.array(self.sigma_c_crack) < load) - 1
            if idx == -1:
                return [None]
            else:
                return self.cracks_list[idx]
        else:
            return [None]

    def sigma_m(self, load):
        Em = self.CB_model.E_m
        Ec = self.CB_model.E_c
        sigma_m = load * Em / Ec * np.ones(len(self.x_arr))
        cb_load = self.cb_list(load)
        if cb_load[0] is not None:
            for cb in cb_load:
                crack_position_idx = np.argwhere(self.x_arr == cb.position)
                left = crack_position_idx - len(np.nonzero(cb.x < 0.)[0])
                right = crack_position_idx + len(np.nonzero(cb.x > 0.)[0]) + 1
                sigma_m[left:right] = cb.get_epsm_x_w(load) * Em
        return sigma_m

    def epsf_x(self, load):
        Ec = self.CB_model.E_c
        epsf_x = load / Ec * np.ones(len(self.x_arr))
        cb_load = self.cb_list(load)
        if cb_load[0] is not None:
            for cb in cb_load:
                crack_position_idx = np.argwhere(self.x_arr == cb.position)
                left = crack_position_idx - len(np.nonzero(cb.x < 0.)[0])
                right = crack_position_idx + len(np.nonzero(cb.x > 0.)[0]) + 1
                epsf_x[left:right] = cb.get_epsf_x_w(load)
        return epsf_x

    def residuum(self, q):
        return np.min(self.matrix_strength - self.sigma_m(q))

    def evaluate(self):
        # seek for the minimum strength redundancy to find the position
        # of the next crack
        last_pos = pi
        sigc_min = 0.0
        sigc_max = self.load_sigma_c_arr[-1]
        while np.any(self.sigma_m(sigc_max) > self.matrix_strength):
            sigc_min = brentq(self.residuum, sigc_min, sigc_max)
            crack_position = self.x_arr[np.argmin(self.matrix_strength -
                                                  self.sigma_m(sigc_min))]
            new_cb = CB(position=float(crack_position),
                     crack_load_sigma_c=sigc_min - self.load_sigma_c_arr[-1] / 1000.,
                     interpolator=self.interpolator)
            self.sigma_c_crack.append(sigc_min - 1e-10)
            if len(self.cracks_list) is not 0:
                self.cracks_list.append(copy.copy(self.cracks_list[-1])
                                        + [new_cb])
            else:
                self.cracks_list.append([new_cb])
            self.sort_cbs()
            cb_list = self.cracks_list[-1]
            sigc_max_lst = [cbi.max_sigma_c for cbi in cb_list] 
            sigc_max = min(sigc_max_lst + [self.load_sigma_c_arr[-1]]) - 1e-10
            print sigc_max
#             #plt.plot(self.x_arr, self.epsf_x(sigc_min), color='red', lw=2)
#             plt.plot(self.x_arr, self.sigma_m(sigc_min)/self.CB_model.E_m, color='blue', lw=2)
#             plt.plot(self.x_arr, self.matrix_strength / self.CB_model.E_m, color='black', lw=2)
#             #plt.ylim(0,0.0008)
#             plt.show()
            if float(crack_position) == last_pos:
                print last_pos
                raise ValueError('''got stuck in loop,
                try to adapt x, w, BC ranges''')
            last_pos = float(crack_position)
        #plt.plot(self.x_arr, self.matrix_strength)
        
        #print sigc_min, sigc_min / (self.reinforcement.E_f * self.reinforcement.V_f + self.E_m * (1. - self.reinforcement.V_f))

if __name__ == '__main__':
    length = 1000.
    nx = 1000
    random_field = RandomField(seed=True,
                               lacor=10.,
                                xgrid=np.linspace(0., length, 400),
                                nsim=1,
                                loc=.0,
                                shape=15.,
                                scale=3.5,
                                non_negative_check=True,
                                distribution='Weibull'
                               )

    reinf = ContinuousFibers(r=0.00345,
                          tau=RV('weibull_min', loc=0.007, shape=1.22, scale=.04),
                          V_f=0.0103,
                          E_f=180e3,
                          xi=WeibullFibers(shape=5.0, sV0=0.0052),
                          n_int=200,
                          label='carbon')

    CB_model = CompositeCrackBridge(E_m=25e3,
                                 reinforcement_lst=[reinf],
                                 )

    scm = SCM(length=length,
              nx=nx,
              random_field=random_field,
              CB_model=CB_model,
              load_sigma_c_arr=np.linspace(0.01, 25., 100),
              )

    scm.evaluate()
    