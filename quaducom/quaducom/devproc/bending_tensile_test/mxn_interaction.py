'''
Created on Jul 1, 2014

Script evaluating the mxn interaction between
tensile and bending load
'''

if __name__ == '__main__':

    from exp_btt_db import ExpBTTDB
    from matresdev.db.simdb import SimDB
    from aramis_cdt import AramisInfo, AramisUI, AramisFieldData, AramisCDT, AramisUI
    # AramisData, AramisBSA,
    simdb = SimDB()
    import os
    import numpy as np

    import pylab as p


    test_files = ['BTT-6c-2cm-TU-0-V11_MxN2.DAT',
                  # 'BTT-4c-2cm-TU-0-V09_MxN2.DAT',
                  # 'BTT-4c-2cm-TU-0-V13_MxN2.DAT',
                  ]

    test_file_path = os.path.join(simdb.exdata_dir,
                             'bending_tensile_test',
                             '2014-06-12_BTT-6c-2cm-0-TU_MxN2')

    e_list = [ExpBTTDB(data_file=os.path.join(test_file_path, test_file),
                    delta_t_aramis=5)
           for test_file in test_files]
    for e in e_list:
        e.process_source_data()
        # print 'w_idx_cut', e.t[e.w_cut_idx]
        # print 'F_max1', e.F_max1
        print 'step_times', e.aramis_field_data.step_times
        print 'crack filter', e.crack_filter_avg

    p.subplot(231)
    for e in e_list:
        p.plot(e.t_aramis_cut, e.N_t_aramis, color='blue', label='N')
        p.ylim(0, 50)
        p.xlim(0, 900)
        p.grid()
        p.xlabel('t [sec]')
        p.ylabel('N [kN]')
        p.legend(loc=2)
        p.twinx()
        p.plot(e.t_aramis_cut, e.F_t_aramis, color='red', label='F')
        p.ylabel('F [kN]')
        p.ylim(0, 6)
        p.xlim(0, 900)
        p.title(test_files)
        p.legend()

    p.subplot(232)
    for e in e_list:
        aramis_file_path = e.get_cached_aramis_file('Xf15s3-Yf15s3')
        AI = AramisInfo(data_dir=aramis_file_path)
        ad = AramisFieldData(aramis_info=AI, integ_radius=3)
        ac = AramisCDT(aramis_info=AI,
                         aramis_data=ad)

        p.plot(ad.i_cut.T, ad.ux_arr.T, color='green')
        p.plot(ad.i_cut[0, :], ad.ux_arr_avg, color='red', linewidth=2)
        # y_min_lim = np.min(p.get_ylim())
        # y_max_lim = np.max(p.get_ylim())
        # p.vlines(ad.i_cut[0, :-1], y_min_lim, ac.crack_filter_avg * y_max_lim + ~ac.crack_filter_avg * y_min_lim,
                    # color='magenta', linewidth=1, zorder=10)

    p.subplot(233)
    for e in e_list:
        p.plot(e.t_aramis_cut, e.eps_t_aramis[0] * 1000, color='grey', label='strain_max')
        p.plot(e.t_aramis_cut, e.eps1_t_aramis * 1000, color='green', label='strain_1re')
        p.plot(e.t_aramis_cut, e.eps_t_aramis[1] * 1000, color='black', label='strain_min')
        # p.xlim(0, 500)
        p.ylim(-5, 30)
        p.grid()
        p.xlabel('t [sec]')
        p.ylabel('strain [1*E-3]')
        p.legend(loc=2)
        p.twinx()
        p.plot(e.t_aramis_cut, e.w_t_aramis, color='darkred', label='w')
        p.ylim(0, 10)
        p.xlim(0, 900)
        p.ylabel('w [mm]')
        p.legend(loc=1)
        print 'max tension strain', (e.eps_t_aramis[0] * 1000)[-1]
        print 'min compression strain', (e.eps_t_aramis[1] * 1000)[-1]
        print 'max tension strain in first reinforcement layer', max(e.eps1_t_aramis * 1000)

    p.subplot(234)
    for e in e_list:
        # p.plot(e.MF_t_aramis, e.N_t_aramis, color='red', label='M0')
        # p.plot(e.MN_t_aramis, e.N_t_aramis, color='aqua', label='MII')
        p.plot()
        p.plot(e.M_t_aramis, e.N_t_aramis, color='black', label='M')
        # print 'e.M_t_aramis', e.M_t_aramis
        # print 'e.M', e.M
        # print 'e.N'. e.N
        # print 'e.N_t_aramis'. e.N
        # print 'e.N'. e.N
        p.ylim(50 , 0)
        p.xlim(0 , 0.4)
        p.grid()
        p.xlabel('M [kNm]')
        p.ylabel('N [kN]')
        p.legend(loc=4)
        x = [0, 0.35]
        y = [44, 0]
        p.plot(x, y, color='grey', linestyle='--')
        # p.xticks
        # p.set_label_position('top')
        # p.xaxis.tick_top()


    p.subplot(235)
    for e in e_list:
        aramis_file_path = e.get_cached_aramis_file('Xf15s3-Yf15s3')
        AI = AramisInfo(data_dir=aramis_file_path)
        ad = AramisFieldData(aramis_info=AI, integ_radius=3)
        ac = AramisCDT(aramis_info=AI,
                         aramis_data=ad)

        max_step = e.n_steps
        a = e.crack_bridge_strain_all
        F_max = np.max(e.F_t_aramis)
        eps_list = []

        for step in range(0, max_step, 1):
            ad.current_step = step

            eps = np.mean(ad.d_ux[:, :], axis=1)
            eps_list.append(np.mean(eps))

        eps_mean = np.array(eps_list, dtype='f')
        sig_c = e.N_t_aramis / (e.A_c * 1000)
        sig_tex = e.N_t_aramis * 1000 / (e.A_tex)

        # print'eps_mean', eps_mean
        # print 'shape_eps_mean', np.shape(eps_mean)
        # print 'N_t_aramis', e.N_t_aramis
        # print 'N_t_aramis', np.shape(e.N_t_aramis)
        # print 'sig_c', sig_c
        # print 'e.A_tex', e.A_tex
        # print  'sig_tex', sig_tex

        print 'tensile_text_max tension strain', eps_mean[-1] * 1000

        # p.plot(eps_mean * 1000, sig_c, label='sig_c')
        if F_max > 1.2:
            p.plot(8, 1000)
            p.xlabel('strain [1*E-3]')
            p.ylabel('sigma tex [N/mm]')

        else:
            p.plot(eps_mean * 1000, sig_tex, label='sig_tex')

            E_tex = e.ccs.E_tex
            K_III = E_tex
            eps_max = max(eps_mean)
            # print 'K_III', K_III
            eps_lin = np.array([0, eps_max * 1000], dtype='float_')
            sig_lin = np.array([0, eps_max * K_III], dtype='float_')
            p.plot(eps_lin, sig_lin, color='grey', linestyle='--')
            p.xlim(-2, 8)
            p.ylim(0, 1600)
            p.xlabel('strain [1*E-3]')
            p.ylabel('sigma tex [N/mm]')
            p.legend(loc=2)


    ''''p.subplot(235)
    for e in e_list:
        aramis_file_path = e.get_cached_aramis_file('Xf15s3-Yf15s3')
        AI = AramisInfo(data_dir=aramis_file_path)
        ad = AramisFieldData(aramis_info=AI, integ_radius=10)
        ac = AramisCDT(aramis_info=AI,
                         aramis_data=ad)

        # fig = self.figure
        # fig.clf()
        # ax = fig.add_subplot(111, aspect='equal')
        p.title(ac.aramis_info.specimen_name + ' - %d' % e.n_steps)

        plot3d_var = getattr(ad, 'd_ux')

        mask = np.logical_or(np.isnan(ad.x_arr_0),
                             ad.x_0_mask[0, :, :])
        mask = None

        print plot3d_var[mask].shape

        CS = p.contourf(ad.x_arr_0,
                        ad.y_arr_0,
                         plot3d_var, 2)
                        #plot3d_var, 2, cmap=plt.get_cmap('binary')
        p.plot(ad.x_arr_0, ad.y_arr_0, 'ko')

        p.plot(ad.x_arr_0[ac.crack_filter],
                 ad.y_arr_0[ac.crack_filter], linestyle='None',
                 marker='.', color='white')

        p.vlines(ad.x_arr_0[0, :][ac.crack_filter_avg],
                   [0], np.nanmax(ad.y_arr_0[mask]),
                   color='magenta', zorder=100, linewidth=2)

        p.xlabel('x [mm]')
        p.ylabel('y [mm]')'''

    p.subplot(236)
    for e in e_list:
        aramis_file_path = e.get_cached_aramis_file('Xf15s3-Yf15s3')
        AI = AramisInfo(data_dir=aramis_file_path)
        ad = AramisFieldData(aramis_info=AI, integ_radius=3)
        ac = AramisCDT(aramis_info=AI,
                         aramis_data=ad)

        max_step = e.n_steps
        a = e.crack_bridge_strain_all
        n_fa = ad.d_ux.shape[0]
        h = np.linspace(e.pos_fa[0], e.pos_fa[1], num=n_fa)
        # print 'h', h

        # print 'crack filter', e.crack_filter_avg

        for step in range(0, max_step, 10):

            ad.current_step = step

            if a == None:
                mid_idx = ad.d_ux.shape[1] / 2
                eps_range = 3
                eps = np.mean(ad.d_ux[:, mid_idx - eps_range:mid_idx + eps_range], axis=1)
            else:
                ux = ad.ux_arr
                x_0 = ad.x_arr_0
                idx_border1 = e.idx_failure_crack[1]
                idx_border2 = e.idx_failure_crack[2]
                eps_range = 2
                ux1 = np.mean(ux[:, idx_border1 - eps_range: idx_border1 + eps_range ], axis=1)
                ux2 = np.mean(ux[:, idx_border2 - eps_range: idx_border2 + eps_range ], axis=1)
                x_0_1 = np.mean(x_0[:, idx_border1 - eps_range: idx_border1 + eps_range ], axis=1)
                x_0_2 = np.mean(x_0[:, idx_border2 - eps_range: idx_border2 + eps_range ], axis=1)

                # ux1 = ux[:, 0]
                # ux2 = ux[:, -1]
                # x_0_1 = x_0[:, 0]
                # x_0_2 = x_0[:, -1]
                # print 'ux1', ux1

                eps = (ux2 - ux1) / (x_0_2 - x_0_1)

                # print 'eps', eps

                # eps = np.mean(ac.d_ux_arr[:, idx_border1:idx_border2], axis=1)
                p.title('strain in the failure crack')

            x = ((20 - h[-1]) * (eps[0] - eps[-1])) / (h[0] - h[-1])
            # print 'x', x
            eps_ed_up = x + eps[-1]
            # print 'eps_ed_up', eps_ed_up
            eps_ed_lo = eps[0] - x
            # print 'eps_ed_lo', eps_ed_lo
            eps_to1 = np.append(eps, eps_ed_lo)
            eps_to2 = np.append(eps_ed_up, eps_to1)
            # print 'eps_to2', eps_to2

            h_1 = np.append(h, 0)
            h_2 = np.append(20, h_1)
            # print 'h_2', h_2

            eps_rev = eps_to2[::-1]

            step_time = e.t_aramis[step]
            p.plot(eps_rev * 1000, h_2, label='%i' % step_time)
            p.xlim(-5, 25)
            p.ylim(0, 20)
            p.xlabel('strain [1*E-3]')
            p.ylabel('h [mm]')
            # p.legend(bbox_to_anchor=(0.66, 0.02), borderaxespad=0., ncol=2, loc=3)
            p.legend(bbox_to_anchor=(0.99, 0.98), borderaxespad=0., ncol=2, loc=1)



        p.show()

    '''p.subplot(235)
    for e in e_list:
        p.plot(e.t_aramis_cut, e.N_t_aramis, color='blue', label='N')
        p.xlim(0, 500)
        p.ylim(0, 50)
        p.grid()
        p.xlabel('t [sec]')
        p.ylabel('N [kN]')
        p.legend(loc=2)
        p.twinx()
        p.plot(e.t_aramis_cut, e.M_t_aramis, color='black', label='M')
        p.plot(e.t_aramis_cut, e.MF_t_aramis, color='red', label='M0')
        p.plot(e.t_aramis_cut, e.MN_t_aramis, color='aqua', label='MII')
        p.ylim(-0.25, 0.5)
        # p.xlim(0, 950)
        p.ylabel('M [kNm]')
        p.legend(ncol=3)'''


#        AUI = AramisUI(aramis_info=e.aramis_info)
#        AUI.configure_traits()
