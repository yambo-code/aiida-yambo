def reorganize_resources(mpi_new, nodes, mpi_per_node, threads):

    nodes = mpi_new/mpi_per_node
    
    resources = {'num_machines': int(nodes),
                 'num_mpiprocs_per_machine': int(mpi_per_node),
                 'num_cores_per_mpiproc': int(threads)}

    return resources

def find_commensurate(a,b):
    for j in range(a,0,-1):
        if a%b==0:
            return a
        else:
            a -= 1

def balance(tasks,a,b,rec=0):
        r = a/b
        #if r > 1: r=1/r
        t = int(tasks*r)
        if t == 0: t = 1
        for i in range(t,0,-1):
            if tasks%i == 0:
                t = i
                break
        k  = tasks//t

        if rec > 0: a, b=a*2, b*2
        
        if t > a:
            rec +=1
            t,k = balance(t,a/2,b,rec)   
        elif k > b:
            rec +=1
            t,k = balance(t,a,b/2,rec) 
        return t,k

def distribute(tasks=10, what='DIP', **ROLEs):
    ROLEs_DIP = {'k','c','v'}
    ROLEs_X = {'k','c','v','g','q'}
    ROLEs_SE = {'q','qp','b','g'}
    #for role in ROLEs.keys():
    #    print(role,ROLEs[role],ROLEs[role]%tasks,ROLEs[role]//tasks)
    
    if what=='DIP':
        if tasks > ROLEs['c']*ROLEs['k']*ROLEs['v']: 
            print('set')
            tasks = ROLEs['c']*ROLEs['k']*ROLEs['v']
        b,k = balance(tasks=tasks,a=ROLEs['c']+ROLEs['v'],b=ROLEs['k'])
        c,v = balance(tasks=b,a=ROLEs['c'],b=ROLEs['v'])
        print('mpi k c v')
        return k*c*v,k,c,v
        
    elif what == 'X':
        if tasks > ROLEs['c']*ROLEs['k']*ROLEs['v']*ROLEs['g']*ROLEs['q']: 
            tasks = ROLEs['c']*ROLEs['k']*ROLEs['v']*ROLEs['g']*ROLEs['q']
        b,k = balance(tasks=tasks,a=ROLEs['c']+ROLEs['v'],b=ROLEs['k'])
        c,v = balance(tasks=b,a=ROLEs['c'],b=ROLEs['v'])
        if ROLEs['g']> 1: 
            c,g = balance(tasks=c,a=ROLEs['c'],b=ROLEs['g'])
        else:
            g = 1
        q = 1
        print('mpi q k g c v')
        return q*k*g*c*v,q,k,g,c,v
        
    elif what == 'SE':       
        if tasks > ROLEs['q']*ROLEs['qp']*ROLEs['b']*ROLEs['g']: 
            tasks = ROLEs['q']*ROLEs['qp']*ROLEs['b']*ROLEs['g']
        b,qp = balance(tasks=tasks,a=ROLEs['b'],b=ROLEs['qp'])
        print(b,qp)
        if ROLEs['g']> 1: 
            b,g = balance(tasks=b,a=ROLEs['b'],b=ROLEs['g'])
        else:
            g = 1
        q = 1
        print('mpi q qp b g')
        return q*qp*b*g,q,qp,b,g

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
    k_dip, c_dip, v_dip = 1 , 1 , 1
    k_X, c_X, v_X, g_X, q_X = 1 , 1 , 1 , 1, 1
    qp_SE, b_SE, g_SE, q_SE =1 , 1 , 1 , 1

    if 'HF_issue' in []:
        if last_qp <= occupied:
             print('last_qp lower than occupied, setting to occupied')
             last_qp = occupied+1 
        bands = last_qp*qp_corrected
    
    for i in range(10):
        mpi1, k_dip, c_dip, v_dip = distribute(tasks=mpi, what='DIP', c=bands-occupied, v=occupied, k=kpoints, g=g_vecs)
        mpi2, k_X, c_X, v_X, g_X, q_X = distribute(tasks=mpi1, what='X', c=bands-occupied, v=occupied, k=kpoints, g=g_vecs,q=q)
        mpi3, qp_SE, b_SE, g_SE, q_SE = distribute(tasks=mpi1, what='SE', b=bands, qp=qp, g=g_vecs,q=q)
        if mpi1 == mpi2 and mpi2 == mpi3:
            if mpi1%mpi_per_node==0:
                mpi = mpi1
                break
            else:
                mpi=find_commensurate(mpi1,mpi_per_node)  
        else:
            mpi = mpi3

    for i in [mpi, k, c, v, g, q, qp, b]:
        if i == 0 :
            i = 1

    mpi_DIP = {'k':k_dip,'c':c_dip,'v':v_dip}
    mpi_X = {'q':q_X,'k':k_X,'g':g_X,'c':c_X,'v':v_X}
    mpi_SE = {'q':q_SE,'qp':qp_SE,'b':b_SE,'g':g_SE}
    
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