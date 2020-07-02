import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.io import loadmat
import scipy.linalg as la
import sys
from copy import copy
import os
from CORONA.Res3dC.DataSet_3dC import preprocess

def log_rms(mat):
    # TODO make the dynamic ranges the same (I think this is done by default)
    meansquare = np.sum(np.abs(mat)**2, axis=2, dtype=float)/mat.shape[2]
    logplot = 10*np.log10(meansquare/np.amax(meansquare))
    # logplot = meansquare/np.amax(meansquare)
    return logplot

def mse(L, S, D, Sp):
    Ln, Sn, Dn = preprocess(L, S, D)
    _, Spn, _ = preprocess(D-Sp, Sp, D)
    n1, n2, n3 = Spn.shape
    return np.mean(np.abs(Sn-Spn)**2)
    # return np.sum(np.abs(S-Sp)**2)/(n1*n2*n3)

def psnr(S, Sp):
    return 10*np.log10(np.abs(np.amax(S))**2/np.mean(np.abs(S-Sp)**2))

def psnr_per_frame(S, Sp):
    return psnr(S, Sp)/S.shape[-1]

def ssim(S, Sp):
    c1 = (0.01*2)**2
    c2 = (0.03*2)**2
    mu_x = np.mean(S)
    mu_y = np.mean(Sp)
    var_x = np.mean(np.abs(S)**2)-np.abs(np.mean(S))**2
    var_y = np.mean(np.abs(Sp)**2)-np.abs(np.mean(Sp))**2
    cov = np.mean(S*np.conj(Sp))-np.mean(S)*np.mean(np.conj(Sp))

    return np.abs((2*mu_x*mu_y+c1)*(2*cov+c2)/((mu_x**2+mu_y**2+c1)*(var_x+var_y+c2)))

def metrics():
    svt_metric = []
    resnet_metric = []
    data_dir = '/home/sam/Documents/mats/'
    outs = os.listdir(data_dir)
    for n in range(len(outs)):
        outputs = loadmat(os.path.join(data_dir, outs[n]))
        Sp = outputs['Sp']
        S = outputs['S']   
        D = outputs['D']
        svals, St = svt(D, 10)
        svt_metric.append(psnr(S, St))
        resnet_metric.append(psnr(S, Sp))
    plt.scatter(range(len(outs)), resnet_metric)
    plt.scatter(range(len(outs)), svt_metric)
    print(np.mean(resnet_metric))
    print(np.mean(svt_metric))
    plt.ylabel('PSNR (dB)')
    plt.xlabel('Sample #')
    plt.title('PSNR for ResNet, TB=2.5, Rank=4')
    plt.show()

def plot_column(n):
    # outputs = loadmat(f'/home/sam/Documents/mats-2-real/{n}.mat')
    outputs = loadmat(f'/home/sam/Documents/mats/{n}.mat')
    w = 39
    col = 3
    D = outputs['D']
    Sp = outputs['Sp']
    S = outputs['S']
    svals, St = svt(D, 10)
    width = outputs['width'][0][0]
    width_px = w/.0025*width

    fig, ax = plt.subplots(3, 2, figsize=(9,6))
    plt.set_cmap('hot')
    ax[0][1].imshow(10*np.log10(np.abs(S[:,col])**2), aspect='auto')
    ax[0][1].set_title(f'Column {col} per frame')
    ax[0][0].imshow(log_rms(S))
    rect = Rectangle((col, -1), 1, w+1, fill=False, color='green')
    ax[0][0].add_patch(rect)
    ax[0][0].set_title('Ground truth S')
    ax[1][1].imshow(10*np.log10(np.abs(Sp[:,col])**2), aspect='auto')
    ax[1][0].set_title('Reconstructed S')
    ax[1][0].imshow(log_rms(Sp))
    rect = Rectangle((col, -1), 1, w+1, fill=False, color='green')
    ax[1][0].add_patch(rect)
    ax[1][1].set_title(f'Column {col} per frame')
    ax[2][0].set_title('SVT S')
    ax[2][0].imshow(log_rms(St))
    rect = Rectangle((col, -1), 1, w+1, fill=False, color='green')
    ax[2][0].add_patch(rect)
    ax[2][1].set_title(f'Column {col} per frame')
    ax[2][1].imshow(10*np.log10(np.abs(St[:,col])**2), aspect='auto')

    print(f'ResNet PSNR: {psnr(S, Sp)}')
    print(f'SVT PSNR: {psnr(S, St)}')
    # print(ssim(S, Sp))
    # print(ssim(S, St))
    plt.show()

def plot_patches(n, q1, q2):
    # outputs = loadmat(f'/home/sam/Documents/mats-2-real/{n}.mat')
    outputs = loadmat(f'/home/sam/Documents/mats/{n}.mat')
    w = 39
    D = outputs['D']
    Sp = outputs['Sp']
    S = outputs['S']
    width = outputs['width'][0][0]
    width_px = w/.0025*width

    if q1==0 and q2==0:
        angle = 90 + 45
        x = w - width_px/2*np.cos((angle-90)/np.pi*180)
        y = w - width_px/2*np.sin((angle-90)/np.pi*180)
    elif q1==1 and q2==1:
        angle = -75
        x = -width_px/2*np.cos(angle/np.pi*180)
        y = width_px/2*np.sin(angle/np.pi*180)

    bbox = Rectangle((x,y), width_px, 39*1.414, angle=angle, fill=False, color='blue')
    copies = [copy(bbox) for _ in range(3)]


    fig, ax = plt.subplots(2,3, figsize=(9,6))
    plt.set_cmap('hot')

    svals, Drec = svt(D, 5)

    ax[0][0].imshow(log_rms(D))
    ax[0][0].set_title('Input')
    ax[0][0].add_patch(bbox)

    ax[0][1].imshow(log_rms(S))
    ax[0][1].set_title('Ground truth S')
    ax[0][1].add_patch(copies[0])

    ax[0][2].imshow(log_rms(Sp))
    ax[0][2].set_title('Reconstructed S')
    ax[0][2].add_patch(copies[1])


    ax[1][0].semilogy(range(1, len(svals)+1), svals)
    ax[1][0].set_title('Singular values')

    ax[1][1].imshow(log_rms(Drec))
    ax[1][1].set_title('SVT')
    ax[1][1].add_patch(copies[2])

    print(mse(D-S, S, D, Sp))
    print(mse(D-Drec, S, D, Drec))
    plt.show()

def plot_loss():
    losses1 = np.load('/home/sam/Documents/Res3dC_nocon_sim_Res3dC_LossData_Tr2400_epoch20_lr2.00e-03.npz')
    losses2 = np.load('/home/sam/Documents/working-20/Res3dC_nocon_sim_Res3dC_LossData_Tr2400_epoch20_lr2.00e-03.npz')
    lossmeans = np.hstack([losses2['arr_0'], losses1['arr_0']])
    lossmeans_val = np.hstack([losses2['arr_1'], losses1['arr_1']])
    plt.semilogy(range(1,41), lossmeans, '-s', label='Train loss', markersize=3)
    plt.semilogy(range(1,41), lossmeans_val, '-x', label='Validation loss', markersize=3)
    plt.title('Losses over 40 epochs of training base ResNet')
    plt.xlabel('Epoch')
    plt.ylabel('MSE loss')
    plt.legend()
    plt.show()

def svt(D,e1, e2=None):
    n1, n2, n3 = D.shape
    e1 -= 1     # change 1-indexed e.val number to 0-indexed array index
    caso = D.reshape((n1*n2, n3))
    U, S, Vh = la.svd(caso, full_matrices=False)
    if e2 is None:
        e2 = n3
    casorec = U[:,e1:e2]@np.diag(S[e1:e2])@(Vh[:,e1:e2].T)
    Drec = casorec.reshape(D.shape)
    return S, Drec

if __name__=='__main__':
    # plot_patches(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
    # plot_loss()
    plot_column(int(sys.argv[1]))
    # metrics()