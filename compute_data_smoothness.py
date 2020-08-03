from __future__ import absolute_import, division, print_function

import argparse
import os

import numpy as np
import scipy.io as sio
import torch

parser = argparse.ArgumentParser(description='Smoothness Computing')
parser.add_argument('--datadir', default='Data/modelnet40_1024_processed', type=str, metavar='DIR', help='path to dataset')
parser.add_argument('--k', type=int, default=16, help='')
parser.add_argument('--k2', type=int, default=16, help='')

cfg  = parser.parse_args()
print(cfg)

filenames = os.listdir(os.path.join(cfg.datadir, 'Mat'))
k = cfg.k

smoothness = []
for i, filename in enumerate(filenames):
	pc = torch.FloatTensor(sio.loadmat(os.path.join(cfg.datadir, 'Mat', filename))['adversary_point_clouds'])
	pc = pc.t()
	normal = torch.FloatTensor(pc.size())
	n = pc.size(0)

	dis = ((pc.unsqueeze(1) - pc.unsqueeze(0))**2).sum(2) # n*n
	idx = dis.topk(cfg.k2+1,  dim=-1, largest=False, sorted=True)[1][:, 1:].contiguous()
	pts = torch.gather(pc, 0, idx.view(n*cfg.k2, 1).expand(n*cfg.k2, 3)).view(n, cfg.k2, 3)
	pts = pts - pc.unsqueeze(1)
	pts_ = pts.permute(2, 0, 1).numpy()

	for j in range(n):
		pts_single = pts_[:, j, :]
		C = np.cov(pts_single)
		v, t = np.linalg.eig(C)
		t = t[:, np.argsort(v)][:, 0]
		normal[j] = torch.FloatTensor(t).view(3)

	idx = dis.topk(k+1,  dim=-1, largest=False, sorted=True)[1][:, 1:].contiguous()
	pts = torch.gather(pc, 0, idx.view(n*k, 1).expand(n*k, 3)).view(n, k, 3)
	#FIXME: here use the hypotheis that the plane across the point
	pts = pts - pc.unsqueeze(1)
	#FIXME: here use cross prodcut to simulate the l_2 norm
	s = torch.abs((pts*normal.unsqueeze(1)).sum(2)).mean(1).max()
	smoothness.append(s)
	print('[{0}/{1}]: {2:.4f}({3:.4f})'.format(i+1, len(filenames), s.item(), torch.FloatTensor(smoothness).mean().item()))

# print(smoothness)
smoothness = torch.FloatTensor(smoothness)
# print(smoothness.size())

if not os.path.exists(os.path.join(cfg.datadir, 'metric')):
	os.mkdir(os.path.join(cfg.datadir, 'metric'))

sio.savemat(os.path.join(cfg.datadir, 'metric', 'k'+str(cfg.k)+'.mat'), {"smoothness": smoothness.numpy()})
# pdb.set_trace()
ma = smoothness.max().item()
mi = smoothness.min().item()
av = smoothness.mean().item()
with open(os.path.join(cfg.datadir, 'metric', 'result.txt'), 'at') as f:
	info = 'k: {0}, avg: {1:.4f}, min: {2:.4f}, max: {3:.4f}\n'.format(k, av, mi,ma)
	print(info)
	f.write(info)
