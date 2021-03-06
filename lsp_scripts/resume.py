#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import cPickle as pickle
import logging
from mini_batch_loader_softmax import MiniBatchLoader
from VGGNet import VGGNet
from chainer import serializers
from myfcn import MyFcn
from copy_model import *
from chainer import cuda, optimizers, Variable
import sys
import math
import time
import numpy as np
from draw_loss import draw_loss_curve
 
#_/_/_/ paths _/_/_/ 
VGG_MODEL_PATH              = 'VGG.model'
IMAGE_DIR_PATH              = "data/LSP/images/"
PICKLE_DUMP_PATH            = "result/myfcn_epoch_{i}.model"
train_fn = "data/LSP/train_joints.csv"
test_fn = "data/LSP/test_joints.csv"
 
#_/_/_/ training parameters _/_/_/ 
GPU = 0
train_data_size = 11000
test_data_size = 1000
LEARNING_RATE    = 0.01
TRAIN_BATCH_SIZE = 10
TEST_BATCH_SIZE  = 5
EPOCHS           = 1000
DECAY_FACTOR     = 1
#DECAY_FACTOR_2   = 0.8
SNAPSHOT_EPOCHS  = 10
EPOCH_BORDER     = 15
TEST_EPOCHS      = 10

#_/_/_/ log _/_/_/ 
fp = open('result/log2', 'w')
 
def test(loader, model, test_dl):
    sum_accuracy = 0
    sum_loss     = 0

    mini_batch_loader = MiniBatchLoader(IMAGE_DIR_PATH, TEST_BATCH_SIZE, MyFcn.IN_SIZE)
    for i in range(0, test_data_size, TEST_BATCH_SIZE):
        raw_x, raw_t = mini_batch_loader.load_data(test_dl[i:i+TEST_BATCH_SIZE])
        x = Variable(cuda.to_gpu(raw_x))
        t = Variable(cuda.to_gpu(raw_t))
        model.train = False
        model(x, t)
        sum_loss     += model.loss.data * TEST_BATCH_SIZE
        sum_accuracy += model.accuracy * TEST_BATCH_SIZE
 
    msg = "test mean loss {a}, accuracy {b}".format(a=sum_loss/test_data_size, b=sum_accuracy/test_data_size)
    print(msg)
    sys.stdout.flush()
    logging.info(msg)
 
 
def main():
    logging.basicConfig(filename='result/log2', level=logging.DEBUG)
    #_/_/_/ load dataset _/_/_/ 
    train_dl = np.array([l.strip() for l in open(train_fn).readlines()])
    test_dl = np.array([l.strip() for l in open(test_fn).readlines()])

    mini_batch_loader = MiniBatchLoader(IMAGE_DIR_PATH, TRAIN_BATCH_SIZE, MyFcn.IN_SIZE)
 
    #_/_/_/ load model _/_/_/
    cuda.get_device(GPU).use()

    myfcn = pickle.load(open('result/myfcn_epoch_60.model', 'rb'))
    myfcn = myfcn.to_gpu()
    
    #_/_/_/ setup _/_/_/
    #optimizer = chainer.optimizers.SGD(LEARNING_RATE)
    optimizer = optimizers.MomentumSGD(lr=LEARNING_RATE)
    optimizer.setup(myfcn)
 
    #_/_/_/ training _/_/_/
    for epoch in range(61, EPOCHS+1):
        st = time.time()
        sys.stdout.flush()
        indices = np.random.permutation(train_data_size)
        sum_accuracy = 0
        sum_loss     = 0
 
        for i in range(0, train_data_size, TRAIN_BATCH_SIZE):
            r = indices[i:i+TRAIN_BATCH_SIZE]
            raw_x, raw_y = mini_batch_loader.load_data(train_dl[r])
            x = Variable(cuda.to_gpu(raw_x))
            y = Variable(cuda.to_gpu(raw_y))
            myfcn.zerograds()
            myfcn.train = True
            loss = myfcn(x, y)
            loss.backward()
            optimizer.update()
 
            if math.isnan(loss.data):
                raise RuntimeError("ERROR in main: loss.data is nan!")
 
            sum_loss     += loss.data * TRAIN_BATCH_SIZE
            sum_accuracy += myfcn.accuracy * TRAIN_BATCH_SIZE
 
        end = time.time()
        msg = "epoch:{x} training loss:{a}, accuracy {b}, time {c}".format(x=epoch,a=sum_loss/train_data_size,
                                                                 b=sum_accuracy/train_data_size, c=end-st)
        print(msg)
        logging.info(msg)
        draw_loss_curve('result/log2', 'result/shape/loss2.png')
        
        sys.stdout.flush()
         
        optimizer.lr *= DECAY_FACTOR # if EPOCH_BORDER > epoch else DECAY_FACTOR_2
        if epoch == 1 or epoch % SNAPSHOT_EPOCHS == 0:
            pickle.dump(myfcn, open(PICKLE_DUMP_PATH.format(i=epoch), "wb"))
 
        #_/_/_/ testing _/_/_/
        if epoch == 1 or epoch % TEST_EPOCHS == 0:
            test(mini_batch_loader, myfcn,test_dl)
     
 
if __name__ == '__main__':
    try:
        start = time.time()
        main()
        end = time.time()
        print("{s}[s]".format(s=end - start))
        print("{s}[m]".format(s=(end - start)/60))
        print("{s}[h]".format(s=(end - start)/60/60))
    except Exception as error:
        print(error.message)
