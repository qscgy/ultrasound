import torch
from scipy.io import loadmat
import h5py
import numpy as np
import os
import random
import tqdm
from scipy.linalg import svd

def find_2nd(string, substring):
    '''
    Finds the start index of the second instance of `substring` in `string`.
    '''
   return string.find(substring, string.find(substring) + 1)

def create_quads(blood, tissue, x, z):
    '''
    Splits blood and tissue into quadrants. x,z are in [1,2] that define the quadrant.

    Arguments:
        blood : the blood array, at least 2D
        tissue : the tissue array, at least 2D
        x, int : the x quadrant index. 1=left, 2=right.
        z, int : the z quadrant index. 1=top, 2=bottom.
    
    Returns:
        array : the blood quadrant
        array : the tissue quandrant
    '''
    blood_quad = blood[int(39*(z-1)):int(39*z), int(39*(x-1)):int(39*x)]
    tissue_quad = tissue[int(39*(z-1)):int(39*z), int(39*(x-1)):int(39*x)]
    return blood_quad, tissue_quad

def create_random_quads(blood, tissue, x, z, maxdist, shape2d):
    '''
    Like create_quads, but with a random offset from the side that is between 0 and maxdist.

    Arguments:
        blood : the blood array, at least 2D
        tissue : the tissue array, at least 2D
        x, int : the x quadrant index. 1=left, 2=right.
        z, int : the z quadrant index. 1=top, 2=bottom.
        maxdist, int : the maximum distance, in array entries, to offset from the two sides the quadrant would align with if not\
for the offset. For example, the x=1, z=1 quadrant would be offset from the top and left by up to maxdist units.
        shape2d, (int, int) : the first two dimension of blood and tissue.
    
    Returns:
        array : the blood quadrant
        array : the tissue quandrant
    '''
    n1, n2 = shape2d
    if x==1:
        xl = random.randint(0, maxdist)
        xr = xl+n2
    else:
        xr = n2-random.randint(0, maxdist)
        xl = xr-n2
    
    if z==1:
        zl = random.randint(0, maxdist)
        zr = zl+n1
    else:
        zr = n1-random.randint(0, maxdist)
        zl = zr-n1
    
    blood_quad = blood[zl:zr, xl:xr]
    tissue_quad = tissue[zl:zr, xl:xr]
    return blood_quad, tissue_quad

LR_DIR = '/data/low-rank/'
SD_DIR = '/data/sim-data-better/'
OUT_DIR = '/data/toy-real-ranked/'
NSV = 4
TB = 5
NFRAMES = 20
sd_names = os.listdir(SD_DIR)
random.shuffle(sd_names)

for i in tqdm.tqdm(range(len(sd_names))):
    mats = loadmat(os.path.join(SD_DIR, sd_names[i]))
    coeff = random.choice([1,1.5,2,2.5])
    blood = mats['blood'][:,:,:NFRAMES]*TB/coeff
    tissue = mats['L'][:,:,:NFRAMES]
    angle = mats['a']
    width = mats['b']

    rank = random.randint(1,NSV)
    n1, n2, n3 = tissue.shape
    caso = tissue.reshape((n1*n2, n3))
    U, s, Vh = svd(caso, full_matrices=False)
    caso_red = U[:,:rank]@np.diag(s[:rank])@(Vh[:,:rank].T)
    tissue = caso_red.reshape((n1, n2, n3))
    for x in (1,2):
        for z in (1,2):
            
            blood_quad, tissue_quad = create_quads(blood, tissue, x, z)
            # blood_quad, tissue_quad = create_random_quads(blood, tissue, x, z, 10, (n1,n2))

            # bw_start = sd_names[i].find('vesselwidth')+12
            # bw_end = find_2nd(sd_names[i][bw_start:], '_')+bw_start
            # width_str = sd_names[i][bw_start:bw_end]
            # width = float(width_str[:width_str.find('_')])
            # width_unit = width_str[width_str.find('_')+1:]
            # if width_unit=='mm':
            #     width *= 0.001
            # elif width_unit=='mum':
            #     width *= 1e-6

            np.savez_compressed(os.path.join(OUT_DIR, f'{i}_x{x}_z{z}'), \
                L=tissue_quad, S=blood_quad, width=width, angle=angle, nsv=rank, x=x, z=z, coeff=coeff)