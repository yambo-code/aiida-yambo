import xarray
import numpy as np
import matplotlib.pyplot as plt
import netCDF4
from aiida_yambo.utils.common_helpers import *
from ase import units

def build_ndbQP(db_path,DFT_pk,Nb=[1,1],Nk=1,verbose=False):
    
    '''
    This just build a QP with KS results, then you can modify the script to change
    the values as you want. Or also just modify the output ds, which has already
    the right dimensions. 
    '''
    
    db = xarray.open_dataset(db_path,engine='netcdf4')
    
    
    data = {}
    for k in db.variables.keys():
        data[k] = (db[k].dims, db[k].data)
        if verbose: print(data[k])
    
    Nb=list(range(Nb[0],Nb[1]+1))
    dimensions = {}
    for d in [Nk,len(Nb)]:
        dimensions['D_'+str(d).zfill(10)] = range(d)
    
    d=[[i]*len(Nb) for i in range(1,Nk+1)]
    ff=[]
    for dd in d:
        ff+=dd
    qp_table = np.array([Nb*Nk,Nb*Nk,ff])
    
    pw = find_pw_parent(load_node(DFT_pk))
    bands = pw.outputs.output_band.get_bands()
    kpoints = pw.outputs.output_band.get_kpoints().reshape(3,Nk)
    kpoints = db.QP_kpts.data[:]
    fermi = pw.outputs.output_parameters.get_dict()['fermi_energy']
    print('Fermi=',fermi)
    
    SOC = pw.outputs.output_parameters.get_dict()['spin_orbit_calculation']
    nelectrons = pw.outputs.output_parameters.get_dict()['number_of_electrons']
    if SOC:
        v = int(nelectrons) - 1
        c = v + 2
    else:
        v = int(nelectrons/2) + int(nelectrons%2)
        c = v + 1
    
    v_cond = np.where((db.QP_table[0] == v) & (abs(db.QP_E[:,0]-db.QP_Eo[:])*units.Ha<5))
    c_cond = np.where((db.QP_table[0] == c) & (abs(db.QP_E[:,0]-db.QP_Eo[:])*units.Ha<5))
    fit_v = np.polyfit(db.QP_Eo[v_cond[0]],db.QP_E[v_cond[0]],deg=1)
    fit_c = np.polyfit(db.QP_Eo[c_cond[0]],db.QP_E[c_cond[0]],deg=1)
    
    QP = np.zeros((Nk*len(Nb),2))
    Z = np.zeros((Nk*len(Nb),2))
    KS = np.zeros((Nk*len(Nb),))

    for i in range(len(qp_table[0])):
        QP[i,0] = (bands[qp_table[2,i]-1,qp_table[0,i]-1]-fermi)/units.Ha
        QP[i,1] = 0
        KS[i] = (bands[qp_table[2,i]-1,qp_table[0,i]-1]-fermi)/units.Ha
        Z[i] = [1,0]
        

    data['QP_E'] = (('D_'+str(len(QP)).zfill(10),'D_'+str(2).zfill(10)),QP)
    data['QP_Eo'] = (('D_'+str(len(KS)).zfill(10)), KS)
    data['QP_Z'] = (('D_'+str(len(Z)).zfill(10),'D_'+str(2).zfill(10)),Z)
    data['QP_table'] = (('D_'+str(3).zfill(10),'D_'+str(len(QP)).zfill(10)),qp_table)

    data['QP_kpts'] = (('D_'+str(3).zfill(10),'D_'+str(Nk).zfill(10)),kpoints)
    
    de = []
    for l in data.keys():
        if 'K_range' in l or 'b_range' in l:
            de.append(l)
                
    #data['PARS'] = (('D_'+str(6).zfill(10)), [Nk,len(Nb),len(QP),0,0,0])
    data['PARS'] = (('D_'+str(6).zfill(10)), [len(Nb),Nk,len(QP),0,0,0])
    data['QP_QP_@_state_1_K_range'] =(('D_'+str(2).zfill(10)),[1,Nk])
    data['QP_QP_@_state_1_b_range'] =(('D_'+str(2).zfill(10)),[1,len(Nb)]) 
    
    ds = xarray.Dataset(
        data,
        #coords=dimensions,
    )
    
    return ds, fit_v, fit_c, v, c #, db_reordered


def FD_even(x,mu,e_ref=0,T=1e-6):
        if T==0: T=1e-4
        return 1/(np.exp((abs(x-e_ref)-mu)/T)+1)
    
def Apply_FD_scissored_correction(start,corrections,scissor,mu,e_ref=0,T=1e-6,unit=units.Ha):
    '''corrections should be a zeroes with shape of start, 
    filled only for the corrections that we computed explicitely.
    provide the scissors in Hartree units...'''
    mu = mu/unit
    e_ref = e_ref/unit
    return FD_even(start,mu,e_ref,T)*(corrections+start)+(1-FD_even(start,mu,e_ref,T))*(start*scissor[0]+scissor[1])

def update_FD_and_scissor(db_dft,db_gw,conduction,mu,scissors=[[1,0],[1,0]],e_ref=0,T=1e-6,verbose=False):
    '''
    update with FD*realGW for the region of interest, then scissor(DFT) for the 
    outside region. 
    ds: the created ndb.QP
    db: the explicit GW corrections that we have.
    mu: window of energy needed in which we want the correction to be exact. except for the smearing of T>0. 
    '''
    dss = db_dft
    
    #update the qp where possible, so we introduce the QP that we have in db:
    for i in range(len(db_gw.QP_table[0,:])):
        b=int(db_gw.QP_table.data[0,i])
        k=int(db_gw.QP_table.data[2,i])

        _b24 = np.where((db_dft.QP_table[0].isin([b]))  & (db_dft.QP_table[2].isin([k]))) 
        b24 = np.where((db_gw.QP_table[0].isin([b])) & (db_gw.QP_table[2].isin([k])))
        
        dss.QP_E.data[_b24] = db_gw.QP_E.data[b24]
        dss.QP_Eo.data[_b24] = db_gw.QP_Eo.data[b24]
        
    for i in range(len(db_dft.QP_table[0,:])):
        b=int(db_dft.QP_table.data[0,i])
        k=int(db_dft.QP_table.data[2,i])

        b24 = np.where((db_dft.QP_table[0].isin([b]))  & (db_dft.QP_table[2].isin([k]))) 

        corr = dss.QP_E.data[b24,0]- dss.QP_Eo.data[b24]
               
        if b<conduction:
            corr[0] = Apply_FD_scissored_correction(dss.QP_Eo.data[b24],corr,scissors[0],mu,e_ref,T)
        else:
            corr[0] = Apply_FD_scissored_correction(dss.QP_Eo.data[b24],corr,scissors[1],mu,e_ref,T)
    
        dss.QP_E.data[b24,0] = corr[0]
            
    return dss

def FD_and_scissored_db(out_db_path,pw,Nb,Nk,v_max,c_min,fit_v,fit_c,conduction,e_ref=None,mu=None,T=1e-2):
    
    db_dft = build_ndbQP(db_path=out_db_path,DFT_pk=pw.pk,Nb=Nb,Nk=Nk)
    
    out_db = xarray.open_dataset(out_db_path,engine='netcdf4')
    #find the min and the max of c and v to have exact GW corrections
    #in this way we can choose e_ref and mu
    v_ref = np.where((out_db.QP_table[0].isin([v_max])))
    c_ref = np.where((out_db.QP_table[0].isin([c_min])))
    
    v_ref_max = (max(out_db.QP_Eo.data[v_ref]*units.Ha)+min(out_db.QP_Eo.data[v_ref]*units.Ha))/2
    c_ref_min = (max(out_db.QP_Eo.data[c_ref]*units.Ha)+min(out_db.QP_Eo.data[c_ref]*units.Ha))/2
    
    if not e_ref: e_ref = (c_ref_min+v_ref_max)/2
    if not mu: mu = (c_ref_min-v_ref_max)/2

    
    db_final = update_FD_and_scissor(db_dft = db_dft[0],
                      db_gw=out_db,
                      conduction=conduction,
                      mu=mu,
                      scissors=[fit_v,fit_c],
                      e_ref=e_ref,
                      T=T,
                      verbose=False)
    
    return db_final