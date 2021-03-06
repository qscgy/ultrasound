# -*- coding: utf-8 -*-
"""
Created on Sun Aug 26 15:10:02 2018

@author: Yi Zhang
@author: Sam Ehrenstein
"""

import numpy as np
import sys
import torch
import matplotlib.pyplot as plt
from scipy.io import savemat
# sys.path.append('../')
from CORONA.classes.Player import Player
from CORONA.classes.Dataset import Converter
from UnfoldedNet3dC import UnfoldedNet3dC
import torch.utils.data as data
import os
from main_resnet import to_var
from plot_mat import psnr, svt
from DataSet import BigImageDataset
#from tools.mat2gif import mat2gif

"""Settings"""
"""========================================================================="""
#Model file
# Unfoledd trained only on sim for 50 epochs
mfile = '/results/x2_better_10layer_sim_Unfolded_Model_al0.50_Tr3200_epoch50_lr2.00e-03.pkl'

"""Network Settings: Remember to change the parameters when you change model!"""
params_net={'layers':10,
            'kernel':[(5,1)]*3+[(3,1)]*7,
            'coef_L':0.4,
            'coef_S':1.8,
            'CalInGPU':True}
gpu=True #if gpu=True, the ResNet will use more parameters
#Directory of input data and its size
data_dir='/data/toy-real/'
m,n,time=39,39,20 #size of data
#Save gif
saveGif=True
save_gif_dir='/results/gifs'
cmap='hot'
note='abs'
#Save matrix
saveMat=False
save_mat_dir='/results/mats'
"""========================================================================="""

#Converter
form_in={'pre':'concat','shape':[-1,1,m,n,time*2]}
form_out={'pre':'concat','shape':[m,n,time]}
convert=Converter()

#Load the model
device='cuda:0' if torch.cuda.is_available() else 'cpu'
# device='cpu'
if mfile[-3:]=='pkl':
    model=UnfoldedNet3dC(params_net)
    state_dict=torch.load(mfile,map_location=device)
    model.load_state_dict(state_dict)
else:
    model=torch.load(mfile)

model = model.cuda()
model.eval()
floss = torch.nn.MSELoss()

TrainInstances = 3200
ValInstances = 800

#Processing
with torch.no_grad():
    loss_mean = 0
    test_data = BigImageDataset(1000, (m,n,time*2), 2, data_dir=data_dir, train_size=TrainInstances, val_size=ValInstances)
    test_loader = data.DataLoader(test_data, batch_size=4, shuffle=False)
    nx = 0
    fnames = os.listdir(data_dir)[TrainInstances+ValInstances:]
    fnames.sort()

    widths = []
    angles = []
    quads = []
    for i in range(1000):
        sample = np.load(os.path.join(data_dir, fnames[i]))
        widths.append(sample['width'])
        angles.append(sample['angle'])
        quads.append((sample['x'], sample['z']))

    resnet_list = []
    svt_list = []
    for i,(L,S,D) in enumerate(test_loader):
        for jj in range(len(D)):
            inputs = to_var(D[jj])
            targets = to_var(L[jj])

            out_L = model(inputs)
            loss = floss(out_L.squeeze(), targets).item()
            print(f'{nx}: {loss}')
            loss_mean += loss
            [Lp, Dg, Sg]=convert.torch2np([out_L, D[jj], S[jj]],[form_out, form_out, form_out])

            #Save gif
            # if saveGif:
            #     mat2gif([Sum,predmv,Bubbles],save_gif_dir,
            #             note=note,cmap=cmap,tit=['Input','Prediction','Ground Truth'])

            #Save matrix or PSNR
            Sp = Dg-Lp
            if saveMat:
                savemat(os.path.join(save_mat_dir, f'{nx}.mat'),{'Lp':Lp, 'D':Dg,'S':Sg,'Sp':Sp, \
                    'width':widths[4*i+jj], 'angle':angles[4*i+jj], 'quad':quads[4*i+jj]})
            else:
                _, St = svt(Dg, 10)
                resnet_list.append(psnr(Sg, Sp))
                svt_list.append(psnr(Sg, St))

            nx += 1

loss_mean /= len(test_data)
print(f'Mean loss: {loss_mean}')
if not saveMat:
    print(f'ResNet mean PSNR: {np.mean(resnet_list)} dB')
    print(f'SVT mean PSNR: {np.mean(svt_list)} dB')
    np.savez_compressed(os.path.join(save_mat_dir, f'metrics_unf_{TrainInstances}.npz'), rn=resnet_list, sv=svt_list)