# -*- coding: utf-8 -*-
"""
Created on Mon Aug 20 13:53:01 2018

@author: Yi Zhang
"""

from scipy.io import savemat
from CORONA.SimPlatform.Simulator import Simulator
from CORONA.SimPlatform.Parameters import params_default
from CORONA.classes.Player import Player
import yaml
import os
import sys
import numpy as np
from tqdm import trange

setname='val'
numInst = 4860

Dname,Sname,Lname=['patch_180','patch_180','patch_180']\
                  if setname!='test2' else ['Patch','S_est_f','L_est_f']
#the start number of .mat file                      
numstart={'train':0, 'val':2400, 'test1':3200, 'test2':4000}[setname] 

# Load settings from config file
cfg_file = sys.argv[1]
cfg = yaml.safe_load(open(cfg_file))
ProjectName=cfg['ProjectName']
folder = cfg['datadir']
shape=(cfg['width'],cfg['height'])
print(shape)
T=cfg['nframes']
m = cfg['m']
n = cfg['n']

params=params_default
params['shape']=shape
params['pixel']=(0.043, 0.086)
rIter=int(shape[0]/n)
cIter=int(shape[1]/m)
player=Player()

# nIter=int(numInst/shape[0]/shape[1]/T*32*32*20)
nIter = int(numInst/rIter/cIter)

print('total iterations and instances: %d, %d'%(nIter,numInst))
numf=numstart
for i in trange(nIter):
    print('current iteration: %d, file number: %d to %d'%(i,numf,numf+rIter*cIter))
    simtor=Simulator(params)
    Sum,Bubbles,Tissue=simtor.generate(T)
    for rr in range(rIter):
        for cc in range(cIter):
            D=Sum[rr*n:(rr+1)*n,cc*m:(cc+1)*m,0:T]
            S=Bubbles[rr*n:(rr+1)*n,cc*m:(cc+1)*m,0:T]
            L=Tissue[rr*n:(rr+1)*n,cc*m:(cc+1)*m,0:T]
            np.savez_compressed(os.path.join(folder, f'{i}_{rr}_{cc}.npz'), D=D, L=L, S=S)            
            # savemat(folder+'D_data/%s/D%d.mat'%(setname,numf),{Dname:D.reshape([32*32,20])})
            # savemat(folder+'fista/%s/S_fista%d.mat'%(setname,numf),{Sname:S.reshape([32*32,20])})
            # savemat(folder+'fista/%s/L_fista%d.mat'%(setname,numf),{Lname:L.reshape([32*32,20])})
            numf+=1
            
# player.play([D,S,L],cmap='hot')
            
            

