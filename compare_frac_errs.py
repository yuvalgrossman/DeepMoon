import numpy as np, h5py, pandas as pd
import os
import cv2
from utils.template_match_target import *
import utils.processing as proc
import utils.transform as trf
import get_unique_craters as guc

#os.system("sshfs silburt@rein005.utsc.utoronto.ca:/data_local/silburt/moon-craters/datasets/HEAD /Users/silburt/remotemount/")
#dir = '/Users/silburt/remotemount'
dir = '../moon-craters/datasets/HEAD'

dtype = 'test'
n_imgs = 30000

#preds = h5py.File('../moon-craters/datasets/HEAD/HEAD_%spreds_n30000_final.hdf5'%(dtype), 'r')[dtype]
#imgs = h5py.File('/scratch/m/mhvk/czhu/moondata/final_data/%s_images.hdf5'%(dtype), 'r')
#craters = pd.HDFStore('%s/%s_craters.hdf5'%(dir,dtype), 'r')
preds = h5py.File('%s/HEAD_%spreds_n30000_final.hdf5'%(dir,dtype), 'r')[dtype]
imgs = h5py.File('%s/%s_images_final.hdf5'%(dir,dtype), 'r')
craters = pd.HDFStore('%s/%s_craters_final.hdf5'%(dir,dtype), 'r')

llbd, pbd, distcoeff = ('longlat_bounds', 'pix_bounds', 'pix_distortion_coefficient')
dim = (float(256), float(256))

longlat_thresh2 = 70
maxrad = 40
minrad = 5
rad_thresh = 1.0
template_thresh = 0.5
target_thresh = 0.1

err_lo_pix, err_la_pix, err_r_pix = [], [], []
err_lo_deg, err_la_deg, err_r_deg = [], [], []
err_lo_csv, err_la_csv, err_r_csv = [], [], []
k2d = 180. / (np.pi * 1737.4)
i = -1
while i < n_imgs-1:
    i += 1
    print(i)
    id = proc.get_id(i)
    llbd_val, dist_val = imgs[llbd][id], imgs[distcoeff][id][0]
    
    coords = template_match_t(preds[i], minrad, maxrad, longlat_thresh2, rad_thresh, template_thresh, target_thresh)
    if len(coords) == 0:
        continue
    coords_conv = guc.estimate_longlatdiamkm(dim, llbd_val, dist_val, coords)
    
    # get csv coords
    csv = craters[id]
    csv_coords = np.asarray((csv['x'], csv['y'], csv['Diameter (pix)'] / 2.)).T
    csv_real = np.asarray((csv['Long'], csv['Lat'], csv['Diameter (km)'] / 2.)).T
    csv_conv = guc.estimate_longlatdiamkm(dim, llbd_val, dist_val, csv_coords)
    
    # compare template-matched results to ground truth csv input data
    N_match = 0
    csv_duplicates = []
    N_csv, N_detect = len(csv_coords), len(coords)
    for j in range(len(coords)):
        lo, la, r = coords[j]
        csvLong, csvLat, csvRad = csv_coords.T
        diff_longlat = (csvLong - lo)**2 + (csvLat - la)**2
        diff_rad = abs(csvRad - r)
        index = (diff_rad < max(1.01, rad_thresh * r)) & (diff_longlat < longlat_thresh2)
        index_True = np.where(index == True)[0]
        N = len(index_True)
        if N > 1:
            cratervals = np.array((lo, la, r))
            id_keep = index_True[0]
            diff = np.sum((csv_coords[id_keep] - cratervals)**2)
            csv_duplicates.append(csv_coords[id_keep])
            for id in index_True[1:]:
                dupevals = csv_coords[id]
                index[id] = False
                csv_duplicates.append(dupevals)
                diff_ = np.sum((dupevals - cratervals)**2)
                if diff_ < diff:
                    id_keep = id
                    diff = diff_
            index[id_keep] = True       # keep only closest match as true
        elif N == 1:
            Lo, La, R = csv_coords[index_True[0]].T
            
            lo_, la_, r_ = coords_conv[j].T
            Lo_, La_, R_ = csv_real[index_True[0]].T
            Loo_, Laa_, Rr_ = csv_conv[index_True[0]].T
            
            dL_pix = abs(Lo - lo) / r
            dL_deg = abs(Lo_ - lo_) / (r_* k2d / np.cos(np.pi * la_ / 180.))
            dL_csv = abs(Lo_ - Loo_) / (R_* k2d / np.cos(np.pi * Laa_ / 180.)
            
            err_lo_pix.append(dL_pix)
            err_la_pix.append(abs(La - la) / r)
            err_r_pix.append(abs(R - r) / r)
            err_lo_deg.append(dL_deg)
            err_la_deg.append(abs(La_ - la_) / (r_* k2d))
            err_r_deg.append(abs(R_ - r_) / r_)
            err_lo_csv.append(dL_csv)
            err_la_csv.append(abs(La_ - Laa_) / (R_* k2d))
            err_r_csv.append(abs(R_ - Rr_) / R_)
        N_match += min(1, N)
        # remove csv so it can't be re-matched again
        csv_coords = csv_coords[np.where(index == False)]
        csv_real = csv_real[np.where(index == False)]
        csv_conv = csv_conv[np.where(index == False)]
        if len(csv_coords) == 0:
            break

# printing stuff
print("Stats:")
print("median, err Longitude (pix) = %f, IQR: %f, %f"%(np.median(err_lo_pix), np.percentile(err_lo_pix, 25), np.percentile(err_lo_pix, 75)))
print("median, err Longitude (deg) = %f, IQR: %f, %f"%(np.median(err_lo_deg), np.percentile(err_lo_deg, 25), np.percentile(err_lo_deg, 75)))
print("median, err Longitude (csv) = %f, IQR: %f, %f"%(np.median(err_lo_csv), np.percentile(err_lo_csv, 25), np.percentile(err_lo_csv, 75)))
#print(list(zip(err_lo_pix, err_lo_deg)))

print("median, err Latitude (pix) = %f, IQR: %f, %f"%(np.median(err_la_pix), np.percentile(err_la_pix, 25), np.percentile(err_la_pix, 75)))
print("median, err Latitude (deg) = %f, IQR: %f, %f"%(np.median(err_la_deg), np.percentile(err_la_deg, 25), np.percentile(err_la_deg, 75)))
print("median, err Latitude (csv) = %f, IQR: %f, %f"%(np.median(err_la_csv), np.percentile(err_la_csv, 25), np.percentile(err_la_csv, 75)))
#print(list(zip(err_la_pix, err_la_deg)))

print("median, err Radius (pix) = %f, IQR: %f, %f"%(np.median(err_r_pix), np.percentile(err_r_pix, 25), np.percentile(err_r_pix, 75)))
print("median, err Radius (deg) = %f, IQR: %f, %f"%(np.median(err_r_deg), np.percentile(err_r_deg, 25), np.percentile(err_r_deg, 75)))
print("median, err Radius (csv) = %f, IQR: %f, %f"%(np.median(err_r_csv), np.percentile(err_r_csv, 25), np.percentile(err_r_csv, 75)))
#print(list(zip(err_r_pix, err_r_deg)))

"""
import matplotlib.pyplot as plt
fig, axes = plt.subplots(nrows=3, ncols=3, figsize=(8, 8))
ax0, ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8 = axes.flatten()
_,_,_=ax0.hist(err_lo_pix)
_,_,_=ax1.hist(err_la_pix)
_,_,_=ax2.hist(err_r_pix)
ax0.set_title('err_lo_pix', fontsize=7)
ax1.set_title('err_la_pix', fontsize=7)
ax2.set_title('err_r_pix', fontsize=7)

_,_,_=ax3.hist(err_lo_deg)
_,_,_=ax4.hist(err_la_deg)
_,_,_=ax5.hist(err_r_deg)
ax3.set_title('err_lo_deg', fontsize=7)
ax4.set_title('err_la_deg', fontsize=7)
ax5.set_title('err_r_deg', fontsize=7)

_,_,_=ax6.hist(err_lo_csv)
_,_,_=ax7.hist(err_la_csv)
_,_,_=ax8.hist(err_r_csv)
ax6.set_title('err_lo_csv', fontsize=7)
ax7.set_title('err_la_csv', fontsize=7)
ax8.set_title('err_r_csv', fontsize=7)
plt.savefig('images/compare_frac_errs.png')
plt.show()
"""
