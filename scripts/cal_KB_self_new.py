# cal_KB_self_new.py
# Tracy Whelen, Microwave Remote Sensing Lab, University of Massachusetts
# Yang Lei, Microwave Remote Sensing Lab, University of Massachusetts
# December 8, 2015

# This is the python version of cal_KB_self_new.m, which calculates k and b between the central image and LiDAR strip.

#!/usr/bin/python
from numpy import * 
import scipy.io as sio
import math as mt   
import json
import arc_sinc as arc
import mean_wo_nan as mwn
import remove_outlier as rout
import extract_scatterplot_density as espd
import pdb

# Define cal_KB_self_new function
# input parameters are the change in s and c, the file directory, averaging number in lat/lon for fitting (Nd_self), 
    # bin_size for density calculation in scatter plot fitting, flag for sparse data cloud filtering
def cal_KB_self_new(deltaS2, deltaC2, directory, Nd_self, bin_size, sparse_lidar_flag):
    
    # Load and read data from .json file
    # Image data is stored as a list and must be turned back into an array
    # Samples and lines are calculated from the shape of the images
    # selffile = open(directory + "output/" + "self.json")
    # selffile_data = json.load(selffile)
    # selffile.close()
    # image1 = array(selffile_data[0])
    # image2 = array(selffile_data[1])
    # lines = int(image1.shape[0])
    # samples = int(image1.shape[1])
    
    # Load and read data from .mat file
    # Samples and lines are calculated from the shape of the images
    selffile_data = sio.loadmat(directory + "output/" + "self.mat")
    image1 = selffile_data['I1']
    image2 = selffile_data['I2']
    lines = int(image1.shape[0])
    samples = int(image1.shape[1])

    # Set the S and C parameters to the average S and C plus the delta values
    S_param2 = 0.65 + deltaS2
    C_param2 = 13 + deltaC2

    # Create gamma and run arc_since for image2   
    gamma2 = image2.copy()
    gamma2 = gamma2 / S_param2
    image2 = arc.arc_sinc(gamma2, C_param2)
    image2[isnan(gamma2)] = nan

    # Partition image into subsections for noise suppression (multi-step process)
    # Create M and N which are the number of subsections in each direction
    # NX and NY are the subsection dimensions
    NX = Nd_self
    NY = Nd_self
    M = fix(lines / NY)
    N = fix(samples / NX)

    # Create JM and JN, which is the remainder after dividing into subsections
    JM = lines % NY
    JN = samples % NX

    # Select the portions of images that are within the subsections
    image1 = image1[0:lines - JM][:, 0:samples - JN]
    image2 = image2[0:lines - JM][:, 0:samples - JN]

    # Split each image into subsections and run mean_wo_nan on each subsection
    
    # Declare new arrays to hold the subsection averages
    image1_means = zeros((M, N))
    image2_means = zeros((M, N))
    
    # Processing image1
    # Split image into sections with NY number of rows in each
    image1_rows = split(image1, M, 0)
    for i in range(M):
        # split each section into subsections with NX number of columns in each
        row_array = split(image1_rows[i], N, 1)
        # for each subsection shape take the mean without NaN and save the value in another array
        for j in range(N):
            image1_means[i, j] = mwn.mean_wo_nan(row_array[j])

    # Processing image2
    # Split image into sections with NY number of rows in each
    image2_rows = split(image2, M, 0)
    for i in range(M):
        # split each section into subsections with NX number of columns in each
        row_array = split(image2_rows[i], N, 1)
         # for each subsection shape take the mean without NaN and save the value in another array
        for j in range(N):
            image2_means[i, j] = mwn.mean_wo_nan(row_array[j]) 
    
    # Make an array for each image of where mean > 0 for both images
    IND1 = logical_and((image1_means > 0), (image2_means > 0))
    I1m_trunc = image1_means[IND1, ...]
    I2m_trunc = image2_means[IND1, ...]
    
    # Remove the overestimation at low height end (usually subjet to imperfection of the mask 
    # over water bodies, farmlands and human activities) and the saturation points over the forested areas due to logging
    IND2 = logical_or((I1m_trunc < 5), (I2m_trunc > (mt.pi * C_param2 - 1)))
    IND2 = logical_not(IND2);


    # Call remove_outlier on these cells when there are only a few of lidar samples that are sparsely distributed
    if sparse_lidar_flag == 1:
        I1m_trunc = I1m_trunc[IND2, ...]
        I2m_trunc = I2m_trunc[IND2, ...]
        # Extract density values from the 2D scatter plot
        I1m_den, I2m_den = espd.extract_scatterplot_density(I1m_trunc, I2m_trunc, bin_size)
    else:
        I1m_trunc, I2m_trunc = rout.remove_outlier(I1m_trunc, I2m_trunc, 0.5, 2)
        I1m_den = I1m_trunc
        I2m_den = I2m_trunc

    # DEBUG: to see the shape of the data cloud
    # linkfilename = "I1_I2.json"
    # linkfile = open(directory + linkfilename, 'w')
    # json.dump([I1m_den.tolist(), I2m_den.tolist()], linkfile)
    # linkfile.close()




    # Calculate the covariance matrix of the data with outliers removed
    cov_matrix = cov(I1m_den, I2m_den)
    
    # Calculate the eigenvalues
    dA, vA = linalg.eig(cov_matrix)
    
#    # print the elliptical ratio (from 0 to 1; the lower value, the better elliptical shape -> the more robust estimation)
#    elliptical_ratio = dA.min() / dA.max()
#    print "Elliptical ratio (i.e. b/a of the ellipse): %f" % elliptical_ratio
#    if elliptical_ratio > 0.5:
#        print "Warning: Relatively bad elliptical shape!"

    # Calculate K and B
    # K is based on whichever value in dA is the largest
    if (dA[0] > dA[1]): # dA[0] is largest
        K = vA[1, 0] / vA[0, 0]
    else: # dA[1] is largest
        K = vA[1, 1] / vA[0, 1]
    B = 2 * mean(I1m_den - I2m_den) / mean(I1m_den + I2m_den)
    
#    print "K&B: %f %f" % (K, B)
    return K, B
