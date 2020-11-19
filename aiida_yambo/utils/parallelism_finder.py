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
    if a/b < 0.5:
        pass
    elif a/b > 0.5:
        pass

    return int(c),int(d) 

def reorganize_resources(mpi_new, nodes, mpi_per_node, threads):

    nodes = mpi_new/mpi_per_node
    
    resources = {'num_machines': int(nodes),
                 'num_mpiprocs_per_machine': int(mpi_per_node),
                 'num_cores_per_mpiproc': int(threads)}

    return resources

def fact(n):
    l = []
    r = []
    for i in range(1,n+1):
        if n%i == 0:
        #print(i)
            l.append(i)
            r.append(i/n)
    return l, r

def find_para(mpi,b,k):
    l,r = fact(mpi)
    if b == 1: b = 0
    if k == 1: k = 0
    if b == 0 and k == 0:
        return 1, 1
    p = b/(b+k)
    pp = p**1.5
    print(pp)
    print(l)
    print(r)
    g = [abs(rr-pp) for rr in r]
    print(g.index(min(g)))
    print('b={}, k={}'.format(l[g.index(min(g))],mpi/l[g.index(min(g))]))
    return int(l[g.index(min(g))]), int(mpi/l[g.index(min(g))])

def parallelize_DIP(mpi, mpi_per_node, bands, occupied, kpoints, g_vecs):
    
    if mpi > bands*kpoints:
        mpi = bands*kpoints

    if bands/kpoints < 0.6:
        b, k = find_para(mpi,bands,kpoints)
    else:
        b, k = find_para(mpi,bands,1)

    if (bands-occupied)/occupied > 0.6:
        c, v = find_para(b,bands-occupied,occupied)
    else:
        c, v = find_para(b,bands-occupied,1)
    
    return int(mpi), int(k), int(c), int(v)

def parallelize_X_matrix(mpi, mpi_per_node, bands, occupied, kpoints):

    g = 1
    q = 1

    if mpi > bands*kpoints:
        mpi = bands*kpoints

    if bands/kpoints < 0.6:
        b, k = find_para(mpi,bands,kpoints)
    else:
        b, k = find_para(mpi,bands,1)

    if (bands-occupied)/occupied > 0.6:
        c, v = find_para(b,bands-occupied,occupied)
    else:
        c, v = find_para(b,bands-occupied,1)
    
    return int(mpi), int(k), int(c), int(v), int(g), int(q)

def parallelize_SE_bands(mpi, mpi_per_node, bands, qp_corrected, g_vecs):

    q = 1
    g = 1

    if mpi > bands*qp_corrected:
        mpi = bands*qp_corrected
    
    if qp_corrected == 2:
        b, qp = mpi/2, qp_corrected 
    else:
        b, qp = find_para(mpi,bands,qp_corrected)
    
    return int(mpi), int(qp), int(b), int(g), int(q)

def find_parallelism_qp(nodes, mpi_per_node, threads, bands, occupied=2, qp_corrected=2, kpoints = 1, \
                        last_qp = 2, namelist = {}):
                                                
    mpi = nodes*mpi_per_node

    # GW #

    q = 1
    g = 1
    k = 1
    c = 1
    v = 1
    b = 1
    qp = 1
    g_vecs = 1

    if 'HF_issue' in []:
        if last_qp <= occupied:
             print('last_qp lower than occupied, setting to occupied')
             last_qp = occupied+1 
        bands = last_qp*qp_corrected
    
    
    mpi, k, c, v = parallelize_DIP(mpi, mpi_per_node, bands, occupied, kpoints, g_vecs)
    mpi, k, c, v, g, q = parallelize_X_matrix(mpi, mpi_per_node, bands, occupied, kpoints)
    mpi, qp, b, g, q = parallelize_SE_bands(mpi, mpi_per_node, bands, qp_corrected, g_vecs)

    mpi_DIP = {'k':k,'c':c,'v':v}
    mpi_X = {'q':q,'k':k,'g':g,'c':c,'v':v}
    mpi_SE = {'q':q,'qp':qp,'b':b,'g':g}

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