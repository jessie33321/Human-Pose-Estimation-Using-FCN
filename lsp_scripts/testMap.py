#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
import cPickle as pickle
from mini_batch_loader_heatmap import MiniBatchLoader
from VGGNet import VGGNet
from chainer import serializers
from myfcn import MyFcn
from copy_model import *
from chainer import cuda, optimizers, Variable
import sys
import math
import time
import numpy as np
import scipy.io as sio
import cv2

TEST_BATCH_SIZE = 1
IMAGE_DIR_PATH  = "data/LSP/images/"

if __name__ == '__main__':

    test_fn = "data/LSP/test_joints.csv" #
    test_dl = np.array([l.strip() for l in open(test_fn).readlines()])

    mini_batch_loader = MiniBatchLoader(IMAGE_DIR_PATH, TEST_BATCH_SIZE, MyFcn.IN_SIZE)

    # get model
    myfcn = pickle.load(open('result/rot40/myfcn_epoch_200.model', 'rb'))  
    myfcn = myfcn.to_gpu()

    sum_accuracy = 0
    sum_loss     = 0
    test_data_size = 1000  #
    allmap = np.zeros((14,224,224,test_data_size)).astype(np.float32)

    for i in range(0, test_data_size, TEST_BATCH_SIZE):
        raw_x, raw_t= mini_batch_loader.load_data(test_dl[i:i+TEST_BATCH_SIZE])
        x = Variable(cuda.to_gpu(raw_x))
        t = Variable(cuda.to_gpu(raw_t))
        myfcn.train = False
        pred = myfcn(x, t)
        sum_loss     += myfcn.loss.data * TEST_BATCH_SIZE
        heatmap = cuda.to_cpu(pred.data)
        heatmap = np.squeeze(heatmap)
        heatmap = heatmap[1:15,:,:]

        allmap[:,:,:,i] = heatmap

        #img = cv2.imread('data/LSP/images/'+test_dl[i].split(',')[0])
        #sio.savemat('trainMap/'+str(i)+'.mat', {'pred':heatmap})
        #cv2.imwrite('testMap/'+str(i).zfill(4)+'.jpg',heatmap*255)
        #cv2.imwrite('trainMap/'+str(i)+'img.jpg',img)

    sio.savemat('allmap.mat', {'allmap':allmap})
    print("test mean loss {a}, accuracy {b}".format(a=sum_loss/test_data_size, b=test_data_size))
    sys.stdout.flush()
