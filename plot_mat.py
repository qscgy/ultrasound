import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.io import loadmat
import scipy.linalg as la
from scipy.signal import filtfilt
import sys
from copy import copy
import os
from CORONA.Res3dC.DataSet_3dC import preprocess
import argparse
from scipy.ndimage import gaussian_filter

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
    S = np.abs(S)
    Sp = np.abs(Sp)
    c1 = (0.01*2)**2
    c2 = (0.03*2)**2
    mu_x = np.mean(S)
    mu_y = np.mean(Sp)
    var_x = np.mean(np.abs(S)**2)-np.abs(np.mean(S))**2
    var_y = np.mean(np.abs(Sp)**2)-np.abs(np.mean(Sp))**2
    cov = np.mean((S-mu_x)*(Sp-mu_y))

    return np.abs((2*mu_x*mu_y+c1)*(2*cov+c2)/((mu_x**2+mu_y**2+c1)*(var_x+var_y+c2)))

def filter_mats(data_dir, rank=None, ls=None):
    data_dir = os.path.abspath(data_dir)
    mats = os.listdir(data_dir)
    for m in mats:
        mat = loadmat(os.path.join(data_dir, m))
        if rank==None or rank==mat['rank'][0][0]:
            if ls==None or ls==mat['lsratio'][0][0]:
                print(m)

def plot_metrics(fname):
    fname = os.path.abspath(fname)
    metric_data = np.load(fname)
    nums = np.array(range(len(metric_data['rn'])))+6800
    plt.scatter(nums, metric_data['rn'], label='ResNet')
    plt.scatter(nums, metric_data['sv'], label='SVT')
    plt.title('PSNR for ResNet, TB=2.5, Rank 1-3')
    plt.ylabel('PSNR (dB)')
    plt.xlabel('Sample #')
    plt.hlines(np.mean(metric_data['rn']), 6800, 8800, color='yellow', label='ResNet avg.')
    plt.hlines(np.mean(metric_data['sv']), 6800, 8800, color='black', label='SVT avg.')
    plt.legend(loc='best')
    plt.show()

def plot_by_rank(fname, diff=False):
    fname = os.path.abspath(fname)
    metric_data = np.load(fname)
    grid = np.zeros((10,10))
    grid_sv = np.zeros_like(grid)
    counts = np.zeros_like(grid)
    for i in range(len(metric_data['rn'])):
        ls = metric_data['lsratios'][i]
        rank = metric_data['ranks'][i]
        counts[int(ls-1)][rank-1] += 1
        grid[int(ls-1)][rank-1] += metric_data['rn'][i]
        grid_sv[int(ls-1)][rank-1] += metric_data['sv'][i]
    if diff:
        grid -= grid_sv
    grid /= counts
    plt.figure(figsize=(8,8))
    plt.imshow(grid)

    for (j,i),label in np.ndenumerate(grid):
        label_text = '{:6.2f}'.format(label)
        plt.text(i,j,label_text,ha='center',va='center')

    xticks = np.arange(grid.shape[1])
    xticklabels = np.arange(grid.shape[1])+1
    # yticks = np.arange(8)-0.5
    yticks = np.arange(grid.shape[0]+1)-0.5
    # yticklabels = [1,1.5,2,2.5,3,3.5,4]
    yticklabels = np.arange(grid.shape[0])+1
    plt.xticks(xticks, xticklabels)
    plt.yticks(yticks, yticklabels)

    plt.xlabel('Rank')
    plt.ylabel('L/S')
    if diff:
        plt.title('PSNR (dB) difference from SVT vs. rank and L/S')
    else:
        plt.title('PSNR (dB) vs. rank and L/S')
    plt.show()

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
        svals, St = svt(D, 6)
        svt_metric.append(psnr(S, St))
        resnet_metric.append(psnr(S, Sp))
    plt.scatter(range(len(outs)), resnet_metric, label='ResNet')
    plt.scatter(range(len(outs)), svt_metric, label='SVT')
    print(np.mean(resnet_metric))
    print(np.mean(svt_metric))
    plt.ylabel('PSNR (dB)')
    plt.xlabel('Sample #')
    plt.title('PSNR for ResNet, TB=2.5, Rank=4')
    plt.legend()
    plt.show()

def rsvd(quad):
    m,n,NFRAMES=quad.shape
    power = 1
    rank_k = 10
    L = quad.reshape((m*n, NFRAMES))
    Y2 = np.random.randn(NFRAMES, rank_k)
    for _ in range(power+1):
        Y1 = L@Y2
        Y2 = (L.T)@Y1
    Q, R = la.qr(Y2, mode='economic')
    L_new = (L@Q)@(Q.T)
    L3_new = L_new.reshape((m, n, NFRAMES))
    quad = quad-L3_new
    return L3_new

def plot_column(fname, col=11, sf=0):
    outputs = loadmat(os.path.abspath(fname))
    w = 40
    D = outputs['D'][:,:,sf:]
    Sp = outputs['Sp'][:,:,sf:]
    if 'S' in outputs.keys():
        S = outputs['S'][:,:,sf:]
    else:
        S = D
    # svals, St = svt(D)
    idx = np.abs(S) < 0.01*np.max(np.abs(S))
    S[idx] = 0
    svals, St = np.ones(30), rsvd(D)
    # width = outputs['width'][0][0]
    # width_px = w/.0025*width

    fig, ax = plt.subplots(3, 2, figsize=(7,12))
    plt.set_cmap('hot')
    if 'S' in outputs.keys():
        ax[2][0].set_title('Ground truth S')
    else:
        ax[2][0].set_title('Input')
    ax[2][1].imshow(10*np.log10(np.abs(S[:,col])**2), aspect='auto')
    ax[2][1].set_title(f'Column {col} per frame')
    ax[2][0].imshow(log_rms(S))
    rect = Rectangle((col, -1), 1, w+1, fill=False, color='green')
    ax[2][0].add_patch(rect)        
    ax[0][1].imshow(10*np.log10(np.abs(Sp[:,col])**2), aspect='auto')
    ax[0][0].set_title('Reconstructed S')
    ax[0][0].imshow(log_rms(Sp))
    rect = Rectangle((col, -1), 1, w+1, fill=False, color='green')
    ax[0][0].add_patch(rect)
    ax[0][1].set_title(f'Column {col} per frame')
    ax[1][0].set_title('SVT S')
    ax[1][0].imshow(log_rms(St))
    rect = Rectangle((col, -1), 1, w+1, fill=False, color='green')
    ax[1][0].add_patch(rect)
    ax[1][1].set_title(f'Column {col} per frame')
    ax[1][1].imshow(10*np.log10(np.abs(St[:,col])**2), aspect='auto')

    if 'lsratio' in outputs.keys():
        print(f'ResNet PSNR: {psnr(S, Sp)} dB')
        print(f'SVT PSNR: {psnr(S, St)} dB')
        print(f'ResNet SSIM: {ssim(S, Sp)} dB')
        print(f'SVT SSIM: {ssim(S, St)} dB')
        # print(f"Rank: {outputs['rank'][0][0]}")
        print(f"L/S: {outputs['lsratio'][0][0]}")
    plt.show()

def plot_patches(fname, th=None):
    fname = os.path.abspath(fname)
    outputs = loadmat(fname)
    w = 39
    sf=0
    D = outputs['D']
    Sp = outputs['Sp']
    # Sp = Sp.real * (Sp.real > 0) + 1j*(Sp.imag * (Sp.imag > 0))
    if 'S' in outputs.keys():
        S = outputs['S']
    else:
        S = np.ones_like(Sp)
    if 'rank' in outputs.keys():
        rank = outputs["rank"][0][0]
    else:
        rank = 0
    # L = outputs['L']

    # width = outputs['width'][0][0]
    # angle = outputs['angle'][0][0]
    # q = outputs['quad']
    # q1 = q[0][0]
    # q2 = q[0][1]
    # width_px = w/.0025*width
    # print(q1, q2)

    # if q1==1 and q2==1:
    #     x = w - width_px/2*np.cos(angle-np.pi/2)
    #     y = w - width_px/2*np.sin(angle-np.pi/2)
    # elif q1==1 and q2==1:
    #     angle = -75
    #     x = -width_px/2*np.cos(angle/np.pi*180)
    #     y = width_px/2*np.sin(angle/np.pi*180)

    # bbox = Rectangle((x,y), width_px, 39*1.414, angle=angle, fill=False, color='blue')
    # copies = [copy(bbox) for _ in range(3)]


    fig, ax = plt.subplots(2,3, figsize=(9,6))
    plt.set_cmap('hot')

    if th:
        svals, Drec = svt(D, th)
        thresh = th
    else:
        svals, Drec, thresh = svt(D, ret_thresh=True)
    # idx = np.abs(S) < 0.01*np.max(np.abs(S))
    # S[idx] = 0
    svals2, S2 = svt(S, 6)
    # print(S)
    print(f'PSNR: {psnr(S, Sp)}')
    pow_L = np.sum(svals[:thresh])
    pow_S = np.sum(svals[thresh:])
    print(f'L power: {pow_L}')
    print(f'S power: {pow_S}')
    print(f'L/S: {pow_L/pow_S}')
    print(f'Thresh: {thresh}')

    ax[0][0].imshow(log_rms(D))
    ax[0][0].set_title('Input')
    # ax[0][0].add_patch(bbox)

    ax[0][1].imshow(log_rms(S))
    ax[0][1].set_title('Ground truth S')
    # ax[0][1].add_patch(copies[0])

    ax[0][2].imshow(log_rms(Sp))
    ax[0][2].imshow(log_rms(Sp))
    ax[0][2].set_title('Reconstructed S')
    # ax[0][2].add_patch(copies[1])


    ax[1][0].semilogy(range(1, len(svals)+1), svals)
    ax[1][0].set_title('Singular values')
    ax[1][0].vlines(thresh, ymin=np.min(svals), ymax=np.max(svals))

    ax[1][1].imshow(log_rms(Drec))
    ax[1][1].set_title('SVT')
    # ax[1][1].add_patch(copies[2])

    # ax[1][2].imshow(gaussian_filter(log_rms(Drec), sigma=3))
    ax[1][2].imshow(log_rms(np.max(Sp)-Sp))
    ax[1][0].semilogy(range(1, len(svals2)+1), svals2)
    print(ssim(Drec, Sp))
    # print(angle*180/np.pi)
    print(f'Rank: {rank}')
    if 'width' in outputs.keys():
        print(f'Width: {outputs["width"][0][0]}')
    print(f'L/S: {outputs["lsratio"][0][0]}')
    plt.show()

def normalize_to(M, N):
    mmax = np.max(np.abs(M))
    nmax = np.max(np.abs(N))
    return M*nmax/mmax

def sv_threshold(svals):
    normed = svals/np.max(svals)
    hflen = 4
    log_filtered = filtfilt(np.hamming(hflen), np.sum(np.hamming(hflen)), np.log(normed))
    second_deriv = np.diff(np.diff(log_filtered))
    sdthresh = 0.001
    return np.min(np.argwhere(second_deriv < sdthresh))

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

def svt(D,e1=None, e2=None, ret_thresh=False):
    n1, n2, n3 = D.shape
    caso = D.reshape((n1*n2, n3))
    U, S, Vh = la.svd(caso, full_matrices=False)
    if e1 is None:
        e1 = sv_threshold(S)
    else:
        e1 -= 1     # change 1-indexed e.val number to 0-indexed array index
    if e2 is None:
        e2 = n3
    casorec = U[:,e1:e2]@np.diag(S[e1:e2])@(Vh[:,e1:e2].T)
    Drec = casorec.reshape(D.shape)
    if ret_thresh:
        return S, Drec, e1
    return S, Drec

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--patches', action='store_true')
    parser.add_argument('--column', action='store_true')
    parser.add_argument('--metrics', action='store_true')
    parser.add_argument('--grid', action='store_true')
    parser.add_argument('--filter', action='store_true')

    parser.add_argument('-f', '--fname')
    parser.add_argument('-c', '--col', type=int)
    parser.add_argument('--rank', type=int)
    parser.add_argument('--ls', type=float)
    parser.add_argument('--diff', action='store_true')
    parser.add_argument('-t', '--thresh', type=int)
    args = parser.parse_args()

    if args.patches:
        plot_patches(args.fname, args.thresh)
    elif args.column:
        plot_column(args.fname, args.col)
    elif args.metrics:
        plot_metrics(args.fname)
    elif args.grid:
        plot_by_rank(args.fname, args.diff)
    elif args.filter:
        filter_mats(args.fname, args.rank, args.ls)