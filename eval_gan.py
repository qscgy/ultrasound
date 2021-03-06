# -*- coding: utf-8 -*-
"""
Created on Fri Jul 17 2020

@author: Sam Ehrenstein
"""

import numpy as np
import sys
import torch
import matplotlib.pyplot as plt
from scipy.io import savemat
sys.path.append('../')
from CORONA.classes.Player import Player
from CORONA.classes.Dataset import Converter
from UGAN import UDiscriminator, UGenerator
from DataSet import BigImageDataset
import torch.utils.data as data
import os
from main_resnet import to_var
from plot_mat import psnr, svt
from tqdm import tqdm
import yaml
#from tools.mat2gif import mat2gif

"""Settings"""
"""========================================================================="""
#Model file
# 10 epochs on sim
mfile = '/results/multi_rank_1_6_sim_Res3dC_Model_Tr6000_epoch30_lr1.00e-03.pkl'

"""Network Settings: Remember to change the parameters when you change model!"""
gpu=True #if gpu=True, the ResNet will use more parameters
#Directory of input data and its size
m,n,time=39,39,20 #size of data
#Save gif
saveGif=True
save_gif_dir='/results/gifs'
cmap='hot'
note='abs'
#Save matrix
saveMetadata=True
save_mat_dir='/results/mats'

cfg = yaml.load(open('/data/resnet.yaml'))
data_dir = cfg['datadir']
TestInstances = cfg['ntest']
saveMat = cfg['saveMat']
"""========================================================================="""

#Converter
form_in={'pre':'concat','shape':[-1,1,m,n,time*2]}
form_out={'pre':'concat','shape':[m,n,time]}
convert=Converter()

TrainInstances = 6000
ValInstances = 800

# with open('eval_resnet.yml') as f:
#     config = yaml.load(f)
#     mfile = config['mfileYi Zhang
    state_dict=torch.load(mfile,map_location=device)
    model.load_state_dict(state_dict)
else:
    model=torch.load(mfile)

model = model.cuda()
model.eval()
floss = torch.nn.MSELoss()

#Processing
with torch.no_grad():
    loss_mean = 0
    test_data = BigImageDataset(TestInstances, (m,n,time*2), 2, data_dir=data_dir, \
        train_size=TrainInstances, val_size=ValInstances)
    test_loader = data.DataLoader(test_data, batch_size=4, shuffle=False)
    nx = 0
    fnames = os.listdir(data_dir)
    fnames.sort()
    fnames = fnames[TrainInstances+ValInstances:]

    widths = []
    angles = []
    quads = []
    ranks = []
    coeffs = []
    for i in range(TestInstances):
        sample = np.load(os.path.join(data_dir, fnames[i]))
        widths.append(sample['width'])
        angles.append(sample['angle'])
        quads.append((sample['x'], sample['z']))
        coeffs.append(sample['coeff'])
        ranks.append(sample['nsv'])

    resnet_list = []
    svt_list = []
    for i,(_,S,D) in tqdm(enumerate(test_loader)):
        for jj in range(len(D)):
            inputs = to_var(D[jj])
            targets = to_var(S[jj])

            out_S = model(inputs[None, None])
            loss = floss(out_S.squeeze(), targets).item()
            loss_mean += loss
            [Sp, Dg, Sg]=convert.torch2np([out_S, D[jj], S[jj]],[form_out, form_out, form_out])

            #Save gif
            # if saveGif:
            #     mat2gif([Sum,predmv,Bubbles],save_gif_dir,
            #             note=note,cmap=cmap,tit=['Input','Prediction','Ground Truth'])

            #Save matrix
            if saveMat:
                savemat(os.path.join(save_mat_dir, f'{nx}.mat'),{'D':Dg,'S':Sg,'Sp':Sp, \
                    'width':widths[4*i+jj], 'angle':angles[4*i+jj], 'quad':quads[4*i+jj], \
                    'lsratio':coeffs[4*i+jj], 'rank':ranks[4*i+jj]})
            else:
                _, St = svt(Dg, 8)
                resnet_list.append(psnr(Sg, Sp))
                svt_list.append(psnr(Sg, St))

            nx += 1

loss_mean /= len(test_data)
print(f'Mean loss: {loss_mean}')
if not saveMat:
    print(f'ResNet mean PSNR: {np.mean(resnet_list)} dB')
    print(f'SVT mean PSNR: {np.mean(svt_list)} dB')
    np.savez_compressed(os.path.join(save_mat_dir, f'complex_deep_1_7_{TrainInstances}.npz'), rn=resnet_list, sv=svt_list,\
        lsratios=coeffs, ranks=ranks)