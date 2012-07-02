#-------------------------------------------------------------------------------
#
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
    HasTraits, Instance, Int, Array, List, Callable, Interface, \
    implements, Trait, cached_property, Property, Float
from stats.spirrid.spirrid import SPIRRID, FunctionRandomization, MonteCarlo
from stats.spirrid.rv import RV
from interpolated_spirrid import InterpolatedSPIRRID
from stats.misc.random_field.random_field_1D import RandomField
from operator import attrgetter
import numpy as np

class CBRandomSample(HasTraits):

    randomization = Instance(FunctionRandomization)

    sampling = Property
    @cached_property
    def _get_sampling(self):
        return MonteCarlo(randomization = self.randomization)

    def __call__(self, e):
        q = self.randomization.q
        sig = q(e, *self.sampling.theta)
        return np.sum(sig)

class CB(HasTraits):

    get_sigma_f_x_reinf = Callable
    randomization = Instance(FunctionRandomization)

    E_m = Property
    @cached_property
    def _get_Em(self):
        return self.randomization.tvars['E_m']

    V_f = Property
    @cached_property
    def _get_V_f(self):
        return self.randomization.tvars['V_f']

    E_f = Property
    @cached_property
    def _get_E_f(self):
        return self.randomization.tvars['E_f']

    position = Float
    Ll = Float
    Lr = Float
    x = Array
    load_sigma_c = Array

    def get_sigma_x_reinf(self):
        '''
        evaluation of stress profile in the vicinity of a crack bridge
        '''
        return self.get_sigma_f_x_reinf(self.load_sigma_c, self.x, self.Ll, self.Lr)

    def get_eps_x_reinf(self):
        '''
        evaluation of strain profile in the vicinity of a crack bridge
        '''
        return self.get_sigma_x_reinf() / self.E_f

    def get_eps_x_matrix(self):
        '''
        evaluation of strain profile in the vicinity of a crack bridge
        '''
        return self.get_sigma_x_matrix()/self.E_m

    def get_sigma_x_matrix(self):
        '''
        evaluation of stress profile in the vicinity of a crack bridge
        '''
        load_sigma_c = self.load_sigma_c
        sigma_c_ff = np.ones(len(self.x))[:, np.newaxis] * load_sigma_c[np.newaxis, :]
        sigma_x_matrix = (sigma_c_ff - self.get_sigma_x_reinf() * self.V_f)/(1.-self.V_f)
        return sigma_x_matrix

class ICBMFactory(Interface):

    def new_cb_model(self):
        pass

class CBMFactory(HasTraits):

    implements(ICBMFactory)

    randomization = Instance(FunctionRandomization)

class CBMeanFactory(CBMFactory):

    # homogenization model
    spirrid = Property(Instance(SPIRRID))
    @cached_property
    def _get_spirrid(self):
        args = self.randomization.trait_get(['q', 'evars', 'tvars'])
        return SPIRRID(**args)

    interpolated_spirrid = Property()
    @cached_property
    def _get_interpolated_spirrid(self):
        return InterpolatedSPIRRID(spirrid = self.spirrid)
        #return NonInterpolatedSPIRRID(spirrid = self.spirrid)

    #===========================================================================
    # Construct new crack bridge (the mean response is shared by all instances)
    #===========================================================================
    def new_cb(self):
        return CB(randomization = self.randomization,
                  get_sigma_f_x_reinf = self.interpolated_spirrid
                  )

class CBRandomFactory(CBMFactory):

    #===========================================================================
    # Construct new crack bridge (each crack bridge has its own random realization)
    #===========================================================================
    def new_cb(self):
        sample = CBRandomSample(randomization = self.randomization)
        return CB(get_sigma_f_x_reinf = sample,
                  randomization = self.randomization)

from scipy.interpolate import RectBivariateSpline

class CTT(HasTraits):

    cb_randomization = Instance(FunctionRandomization)

    cb_type = Trait('mean', dict(mean = CBMeanFactory,
                                 random = CBRandomFactory))

    cb_factory = Property(depends_on = 'cb_type')
    @cached_property
    def _get_cb_factory(self):
        return self.cb_type_(randomization = self.cb_randomization)

    cb_list = List

    length = Float(desc = 'composite specimen length')

    nx = Int(desc = 'number of discretization points')

    load_sigma_c = Property(depends_on = '+load')
    def _get_load_sigma_c(self):
        return np.linspace(self.load_sigma_c_min, self.load_sigma_c_max, self.load_n_sigma_c)

    load_sigma_c_min = Float(load = True)
    load_sigma_c_max = Float(load = True)
    load_n_sigma_c = Int(load = True)

    x_arr = Property(Array, depends_on = 'length, nx')
    @cached_property
    def _get_x_arr(self):
        '''discretizes the specimen length'''
        return np.linspace(0., self.length, self.nx)

    sigma_mx_load_ff = Property(depends_on = '+load, cb_randomization')
    @cached_property
    def _get_sigma_mx_load_ff(self):
        '''2D array of stress in the matrix along an uncracked composite X load array'''
        Em = self.cb_randomization.tvars['E_m']
        Ef = self.cb_randomization.tvars['E_f']
        Vf = self.cb_randomization.tvars['V_f']
        Ec = Ef*Vf + Em*(1-Vf)
        sigma_m_ff = self.load_sigma_c[:, np.newaxis] * Em / Ec
        return np.ones(len(self.x_arr)) * sigma_m_ff

    random_field = Instance(RandomField)
    matrix_strength = Property(depends_on = 'random_field.+modified')
    @cached_property
    def _get_matrix_strength(self):
        rf = self.random_field.random_field
        field_2D = np.ones_like(self.load_sigma_c[:, np.newaxis]) * rf
        rf_spline = RectBivariateSpline(self.load_sigma_c, self.random_field.xgrid, field_2D)
        return rf_spline(self.load_sigma_c, self.x_arr)

    def sort_cbs(self, load_sigma_c):
        '''sorts the CBs by position and adjusts the boundary conditions'''
        # sort the CBs
        self.cb_list = sorted(self.cb_list, key = attrgetter('position'))
        # specify the boundaries at the ends (0 and self.length) of the specimen 
        self.cb_list[0].Ll = self.cb_list[0].position
        self.cb_list[-1].Lr = self.length - self.cb_list[-1].position

        # specify the boundaries between the cracks
        for i, cb in enumerate(self.cb_list[:-1]):
            self.cb_list[i].Lr = (self.cb_list[i + 1].position - cb.position) / 2.
        for i, cb in enumerate(self.cb_list[1:]):
            self.cb_list[i + 1].Ll = (cb.position - self.cb_list[i].position) / 2.

        # specify the x range within the specimen length for every crack
        for i, cb in enumerate(self.cb_list):
            mask1 = self.x_arr >= (cb.position - cb.Ll)
            if i == 0:
                mask1[0] = True
            mask2 = self.x_arr <= (cb.position + cb.Lr)
            cb.x = self.x_arr[mask1 * mask2] - cb.position

        for idx, cb in enumerate(self.cb_list):
            self.cb_list[idx].load_sigma_c = load_sigma_c
            crack_position_idx = np.argwhere(self.x_arr == cb.position)
            left = crack_position_idx - len(np.nonzero(cb.x < 0.)[0])
            right = crack_position_idx + len(np.nonzero(cb.x > 0.)[0]) + 1
            self.sigma_m[-len(load_sigma_c):, left:right] = cb.get_sigma_x_matrix().T

    x_area = Property(depends_on = 'length, nx')
    def _get_x_area(self):
        return  np.ones_like(self.load_sigma_c)[:, np.newaxis] * self.x_arr[np.newaxis, :]

    def evaluate(self):
        '''seek for the minimum strength redundancy to find the position
        of the next crack'''
        while np.any(self.sigma_m > self.matrix_strength):
            mask = self.sigma_m < self.matrix_strength
            idx = np.argmin(mask.sum(0))
            f = mask.sum(0)[idx]
            crack_position = self.x_arr[idx]
            load_sigma_c = self.load_sigma_c[f:]
            self.load_sigma_c_list.append(load_sigma_c[0])
            cbf = self.cb_factory
            new_cb = cbf.new_cb()
            new_cb.position = float(crack_position)
            self.crack_positions.append(float(crack_position))
            self.crack_positions.sort()
            new_cb.load_sigma_c = load_sigma_c
            self.cb_list.append(new_cb)
            self.sort_cbs(load_sigma_c)
#            e_arr = orthogonalize([np.arange(len(self.x_arr)), np.arange(len(self.load_sigma_c))])
#            m.surf(e_arr[0], e_arr[1], self.sigma_m)
#            m.surf(e_arr[0], e_arr[1], self.matrix_strength)
#            m.show()  
            if self.last_pos == crack_position:
                print 'FAIL'
                break
            self.last_pos = crack_position  
    last_pos = Float
    crack_positions = List
    load_sigma_c_list = []

    sigma_m = Array
    def _sigma_m_default(self):
        return self.sigma_mx_load_ff

    eps_m = Property(Array, depends_on = 'cb_list')
    @cached_property
    def _get_eps_m(self):
        return self.sigma_m / self.cb_randomization.q.E_m

    sigma_r = Property(Array, depends_on = 'cb_list')
    @cached_property
    def _get_sigma_r(self):
        Vf = self.cb_randomization.q.V_f
        return (self.load_sigma_c[:, np.newaxis] - self.sigma_m * (1-Vf))/Vf

    eps_r = Property(Array, depends_on = 'cb_list')
    @cached_property
    def _get_eps_r(self):
        return self.sigma_r / self.cb_randomization.q.E_r

    eps_sigma = Property(depends_on = '+load, length, nx, random_field.+modified')
    def _get_eps_sigma(self):
        coords = self.eps_r.shape
#        e_arr = orthogonalize([np.arange(coords[0]), np.arange(coords[1])])
#        m.surf(e_arr[0], e_arr[1], self.eps_r*1000)
#        m.show() 
        eps = np.trapz(self.eps_r, self.x_area, axis = 1) / self.length
        sigma = self.load_sigma_c
        return eps, sigma

if __name__ == '__main__':

    from quaducom.micro.resp_func.cb_emtrx_clamped_fiber_stress import \
        CBEMClampedFiberStressSP
    from stats.spirrid import make_ogrid as orthogonalize
    from matplotlib import pyplot as plt
    import etsproxy.mayavi.mlab as m
    import pickle

    # filaments
    r = 0.00345
    Vf = 0.0103
    tau = .5 #RV('uniform', loc = 0.02, scale = .01) # 0.5
    Ef = 200e3
    Em = 25e3
    l = RV( 'uniform', scale = 10., loc = 2. )
    theta = 0.0
    xi = 0.2#RV( 'weibull_min', scale = 0.12, shape = 5 ) # 0.017
    phi = 1.
    w = np.linspace(0.0, .7, 41)
    x = np.linspace(-50., 50., 121)
    Ll = np.linspace(0.5,50,5)
    Lr = np.linspace(0.5,50,5)

    length = 600.
    nx = 600
    random_field = RandomField(lacor = 4.,
                                xgrid = np.linspace(0., length, 600),
                                nsim = 1,
                                loc = .0,
                                shape = 7.5,
                                scale = 7.8,
                                non_negative_check = True,
                                distribution = 'Weibull'
                               )

    rf = CBEMClampedFiberStressSP()
    rand = FunctionRandomization(   q = rf,
                                    evars = dict(w = w,
                                                 x = x,
                                                 Ll = Ll,
                                                 Lr = Lr,
                                                 ),
                                    tvars = dict(tau = tau,
                                                 l = l,
                                                 E_f = Ef,
                                                 theta = theta,
                                                 xi = xi,
                                                 phi = phi,
                                                 E_m = Em,
                                                 r = r,
                                                 V_f = Vf
                                                 ),
                                    n_int = 30
                                    )

    ctt = CTT(length = length,
              nx = nx,
              random_field = random_field,
              cb_randomization = rand,
              cb_type = 'mean',
              load_sigma_c_min = 0.1,
              load_sigma_c_max = 20.,
              load_n_sigma_c = 100
              )
    
    ctt.evaluate()

    def plot():
        eps, sigma = ctt.eps_sigma
        plt.plot(eps, sigma, color = 'black', lw = 2, label = 'model')
        plt.legend(loc = 'best')
        plt.show()
        #m.show()

    plot()
