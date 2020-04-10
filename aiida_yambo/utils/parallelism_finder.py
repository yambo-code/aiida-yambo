def find_commensurate(max, ratio):

    comm = 1
    for value in range(ratio,max+1):
        if value%ratio == 0 :
            comm = value
    return comm

def balance_tasks(mpi, a, b, ratio = 2):
    
    r = ratio
    c = mpi
    d = 1
    while c%r != 0 and r < mpi:
        r = r+1
    while r*d <= b and c%r == 0:
        c /= r
        d *= r

    return int(c),int(d) 

def parallelize_DIP_X_bands(mpi, mpi_per_node, bands, occupied, ratio = 2):

    if mpi > bands:
        mpi = find_commensurate(bands, mpi_per_node)
    
    #if occupied/bands >= 0.25: # at least 25% of bands are occupied
    #    c, v = balance_tasks(mpi, bands-occupied, occupied, ratio)
    #else:
    c = mpi
    v = 1

    return int(mpi), int(c), int(v)

def parallelize_SE_bands(mpi, bands, qp, ratio = 2):
    
    b, qp = balance_tasks(mpi, bands, qp, ratio) #prefer bands for memory reasons.
    
    return int(b), int(qp)
    
def parallelize_kpoints(mpi, mpi_per_node, kpoints):

    if mpi > kpoints:
        mpi = find_commensurate(kpoints, mpi_per_node)
    
    k = mpi

    return int(mpi), int(k)

def parallelize_bands_and_kpoints(mpi, mpi_per_node, bands, occupied, qp, kpoints, ratio = 2):

    tot = bands*kpoints
    if mpi > tot:
        mpi = find_commensurate(tot, mpi_per_node)
    
    mpi_b, mpi_k = balance_tasks(mpi, bands, kpoints, ratio) #prefer bands for memory reasons. 

    mpi_b, c, v = parallelize_DIP_X_bands(mpi_b, mpi_per_node/mpi_k, bands, occupied)
    b, qp = parallelize_SE_bands(mpi, c*v, qp)

    return int(mpi), int(mpi_k), int(c), int(v), int(mpi_b), int(qp)

def parallelize_bands_and_g(mpi, mpi_per_node, bands, occupied, qp, g, ratio = 2):

    tot = bands
    if mpi > tot:
        mpi = find_commensurate(tot, mpi_per_node)
    
    mpi_b, mpi_g = balance_tasks(mpi, bands, g, ratio) #prefer bands for memory reasons. 

    mpi_b, c, v = parallelize_DIP_X_bands(mpi_b, mpi_per_node/mpi_g, bands, occupied)
    b, qp = parallelize_SE_bands(mpi, c*v, qp)

    return int(mpi), int(mpi_g), int(c), int(v), int(mpi_b), int(qp)

def reorganize_resources(mpi_new, nodes, mpi_per_node, threads):

    nodes = mpi_new/mpi_per_node
    
    resources = {'num_machines': int(nodes),
                 'num_mpiprocs_per_machine': int(mpi_per_node),
                 'num_cores_per_mpiproc': int(threads)}

    return resources

def find_parallelism_qp(nodes, mpi_per_node, threads, bands, occupied=2, qp_corrected=2, kpoints = 1, \
                        what = ['bands'], last_qp = 2, namelist = {}):
                                                
    mpi = nodes*mpi_per_node

    # GW #

    q = 1
    g = 1
    k = 1
    c = 1
    v = 1
    b = 1
    qp = 1

    if 'HF_issue' in what:
        if last_qp <= occupied:
             print('last_qp lower than occupied, setting to occupied')
             last_qp = occupied+1 
        bands = last_qp*qp_corrected

    if 'bands' in what and not 'kpoints' in what and not 'g' in what:
        mpi, c, v = parallelize_DIP_X_bands(mpi, mpi_per_node, bands, occupied, ratio = 2)
        b, qp = parallelize_SE_bands(mpi, c*v, qp_corrected, ratio = 2)
    elif 'kpoints' in what and not 'bands' in what and not 'g' in what:
        mpi, k = parallelize_kpoints(mpi, mpi_per_node, kpoints, ratio = 2)
    elif 'bands' in what and 'g' in what and not 'kpoints' in what:
        g = 20
        ratio = 3
        mpi, g, c, v, b, qp = parallelize_bands_and_g(mpi, mpi_per_node, bands, occupied, qp_corrected, g, ratio)
    else: 
        mpi, k, c, v, b, qp = parallelize_bands_and_kpoints(mpi, mpi_per_node, bands, occupied, qp_corrected, kpoints, ratio = 2)

    mpi_DIP = {'k':k,'c':c,'v':v}
    mpi_X = {'q':q,'k':k,'g':g,'c':c,'v':v}
    mpi_SE = {'q':q,'qp':qp,'b':b}

    parallelism = {}

    parallelism['X_CPU'] = ''
    parallelism['X_ROLEs'] = ''

    parallelism['SE_CPU'] =  ''
    parallelism['SE_ROLEs'] = ''

    parallelism['DIP_CPU'] = ''
    parallelism['DIP_ROLEs'] = ''


    for key in mpi_X:

        parallelism['X_CPU'] = parallelism['X_CPU']+str(int(mpi_X[key]))+' '
        parallelism['X_ROLEs'] = parallelism['X_ROLEs']+key+' '


    for key in mpi_SE:

        parallelism['SE_CPU'] = parallelism['SE_CPU']+str(int(mpi_SE[key]))+' '
        parallelism['SE_ROLEs'] = parallelism['SE_ROLEs']+key+' '


    for key in mpi_DIP:

        parallelism['DIP_CPU'] = parallelism['DIP_CPU']+str(int(mpi_DIP[key]))+' '
        parallelism['DIP_ROLEs'] = parallelism['DIP_ROLEs']+key+' '

    resources = reorganize_resources(mpi, nodes, mpi_per_node, threads)

    return parallelism, resources