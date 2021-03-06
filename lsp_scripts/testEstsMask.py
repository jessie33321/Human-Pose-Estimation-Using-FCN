#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
import cPickle as pickle
from mini_batch_loader_revert import MiniBatchLoader
from chainer import serializers
from myfcn import MyFcn
from chainer import cuda, optimizers, Variable
import sys
import numpy as np
import scipy.io as sio
from skimage import measure
import cv2

TEST_BATCH_SIZE = 1
IMAGE_DIR_PATH  = "data/LSP/images/"

def createMask(originalMap , alpha):

    height,width = originalMap.shape;
    threshold = alpha * np.amax(originalMap)

    # im2bw
    bw = np.zeros((height,width))
    idx = originalMap > threshold
    bw[idx] = 1

    location = np.argmax(originalMap)
    [row,col] = np.unravel_index(location,(height,width))
    blobs = bw==1
    ConnectedComponent = measure.label(blobs)
    CompLabel =  ConnectedComponent[row,col]
    PixelList = ConnectedComponent==CompLabel

    mask = np.ones((height,width));
    mask[PixelList] = 0;

    return mask

if __name__ == '__main__':

    test_fn = "data/LSP/test_joints.csv"
    test_dl = np.array([l.strip() for l in open(test_fn).readlines()])

    mini_batch_loader = MiniBatchLoader(IMAGE_DIR_PATH, TEST_BATCH_SIZE, MyFcn.IN_SIZE)

    # get model
    myfcn = pickle.load(open('result/myfcn_epoch_200.model', 'rb'))
    myfcn = myfcn.to_gpu()

    sum_accuracy = 0
    sum_loss     = 0
    test_data_size = 1000
    ests = np.zeros((test_data_size, 14, 2)).astype(np.float32)
    ests2 = np.zeros((test_data_size, 14, 2)).astype(np.float32)

    for i in range(0, test_data_size, TEST_BATCH_SIZE):
        raw_x, raw_t, crop = mini_batch_loader.load_data(test_dl[i:i+TEST_BATCH_SIZE])
        x = Variable(cuda.to_gpu(raw_x))
        t = Variable(cuda.to_gpu(raw_t))
        myfcn.train = False
        pred = myfcn(x, t)
        sum_loss     += myfcn.loss.data * TEST_BATCH_SIZE
        #sum_accuracy += myfcn.accuracy * TEST_BATCH_SIZE

        #_/_/_/ max location _/_/_/
        hmap = cuda.to_cpu(pred.data[0])
        joints = np.zeros((14,2))
        for j in range(1,15):
            one_joint_map = hmap[j,:,:]
            maxi = np.argmax(one_joint_map)
            joints[j-1,:] = np.unravel_index(maxi,(224,224))

        iniJoints = np.copy(joints)
        
        #_/_/_/ compute score of (left,right) (arm,leg) _/_/_/
        leftArmDist = np.linalg.norm(joints[9,:]-joints[10,:]) + np.linalg.norm(joints[10,:]-joints[11,:])
        rightArmDist = np.linalg.norm(joints[6,:]-joints[7,:]) + np.linalg.norm(joints[7,:]-joints[8,:])
        leftLegDist = np.linalg.norm(joints[3,:]-joints[4,:]) + np.linalg.norm(joints[4,:]-joints[5,:]) \
        + np.linalg.norm(joints[3,:]-joints[9,:])
        rightLegDist = np.linalg.norm(joints[0,:]-joints[1,:]) + np.linalg.norm(joints[1,:]-joints[2,:]) \
        + np.linalg.norm(joints[2,:]-joints[8,:])

        #_/_/_/ mask _/_/_/
        alpha = 0.1
        if leftArmDist > rightArmDist:  
            for originalIdx in [9,8,7,10,11,12]:
                msk = createMask( hmap[originalIdx,:,:] , alpha)
                for dst in list(set(range(1,15)) - set([originalIdx])):
                    hmap[dst,:,:] = hmap[dst,:,:] * msk
        else:
            for originalIdx in [10,11,12,9,8,7]:
                msk = createMask( hmap[originalIdx,:,:] , alpha)
                for dst in list(set(range(1,15)) - set([originalIdx])):
                    hmap[dst,:,:] = hmap[dst,:,:] * msk

        if leftLegDist > rightLegDist:  
            for originalIdx in [3,2,1,4,5,6]:
                msk = createMask( hmap[originalIdx,:,:] , alpha)
                for dst in list(set(range(1,15)) - set([originalIdx])):
                    hmap[dst,:,:] = hmap[dst,:,:] * msk
        else:
            for originalIdx in [4,5,6,3,2,1]:
                msk = createMask( hmap[originalIdx,:,:] , alpha)
                for dst in list(set(range(1,15)) - set([originalIdx])):
                    hmap[dst,:,:] = hmap[dst,:,:] * msk

        for j in range(1,15):
            one_joint_map = hmap[j,:,:]
            maxi = np.argmax(one_joint_map)
            joints[j-1,:] = np.unravel_index(maxi,(224,224))
        
        # swap leg
        iniDist = np.linalg.norm(joints[0,:]-joints[1,:]) + np.linalg.norm(joints[1,:]-joints[2,:])\
                  + np.linalg.norm(joints[3,:]-joints[4,:]) + np.linalg.norm(joints[4,:]-joints[5,:])
        swap23 = np.linalg.norm(joints[0,:]-joints[1,:]) + np.linalg.norm(joints[1,:]-joints[3,:])\
                  + np.linalg.norm(joints[2,:]-joints[4,:]) + np.linalg.norm(joints[4,:]-joints[5,:])
        swap14 = np.linalg.norm(joints[0,:]-joints[4,:]) + np.linalg.norm(joints[4,:]-joints[2,:])\
                  + np.linalg.norm(joints[3,:]-joints[1,:]) + np.linalg.norm(joints[1,:]-joints[5,:])
        swap05 = np.linalg.norm(joints[5,:]-joints[1,:]) + np.linalg.norm(joints[1,:]-joints[2,:])\
                  + np.linalg.norm(joints[3,:]-joints[4,:]) + np.linalg.norm(joints[4,:]-joints[0,:])
        
        mini = min(iniDist, swap23, swap14, swap05)
        if iniDist == mini:
            pass
        elif swap23 == mini:
            joints[[1,4],:] = joints[[4,1],:]
            joints[[0,5],:] = joints[[5,0],:]
        elif swap14 == mini:
            joints[[1,4],:] = joints[[4,1],:]
        elif swap05 == mini:
            joints[[0,5],:] = joints[[5,0],:]

        # swap arm
        iniDist = np.linalg.norm(joints[6,:]-joints[7,:]) + np.linalg.norm(joints[7,:]-joints[8,:])\
                  + np.linalg.norm(joints[9,:]-joints[10,:]) + np.linalg.norm(joints[10,:]-joints[11,:])
        swap23 = np.linalg.norm(joints[6,:]-joints[7,:]) + np.linalg.norm(joints[7,:]-joints[9,:])\
                  + np.linalg.norm(joints[8,:]-joints[10,:]) + np.linalg.norm(joints[10,:]-joints[11,:])
        swap14 = np.linalg.norm(joints[6,:]-joints[10,:]) + np.linalg.norm(joints[10,:]-joints[8,:])\
                  + np.linalg.norm(joints[9,:]-joints[7,:]) + np.linalg.norm(joints[7,:]-joints[11,:])
        swap05 = np.linalg.norm(joints[11,:]-joints[7,:]) + np.linalg.norm(joints[7,:]-joints[8,:])\
                  + np.linalg.norm(joints[9,:]-joints[10,:]) + np.linalg.norm(joints[10,:]-joints[6,:])
        
        mini = min(iniDist, swap23, swap14, swap05)
        if iniDist == mini:
            pass
        elif swap23 == mini:
            joints[[8,9],:] = joints[[9,8],:]
        elif swap14 == mini:
            joints[[7,10],:] = joints[[10,7],:]
        elif swap05 == mini:
            joints[[6,11],:] = joints[[11,6],:]
        
        #_/_/_/ revert to original coordinate _/_/_/
        joints[:,0] = joints[:,0] * crop[3] / 224
        joints[:,1] = joints[:,1] * crop[2] / 224
        joints[:,0] = joints[:,0] + crop[1]
        joints[:,1] = joints[:,1] + crop[0]
        ests[i,:,:] = joints
        
        '''
        joints[:,[0,1]] = joints[:,[1,0]]
        joints = joints.astype(np.int32)
        joints = [tuple(p) for p in joints]
        img = cv2.imread('data/LSP/images/'+test_dl[i].split(',')[0])
        for j, joint in enumerate(joints):
            cv2.circle(img, joint, 5, (0, 0, 255), -1)
            cv2.putText(img, '%d' % j, joint, cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                       (255, 255, 255))
        cv2.imwrite('map/'+str(i)+'swap.jpg',img)'''

        # store iniJoints
        iniJoints[:,0] = iniJoints[:,0] * crop[3] / 224
        iniJoints[:,1] = iniJoints[:,1] * crop[2] / 224
        iniJoints[:,0] = iniJoints[:,0] + crop[1]
        iniJoints[:,1] = iniJoints[:,1] + crop[0]
        ests2[i,:,:] = iniJoints
        '''
        iniJoints[:,[0,1]] = iniJoints[:,[1,0]]
        iniJoints = iniJoints.astype(np.int32)
        iniJoints = [tuple(p) for p in iniJoints]
        img = cv2.imread('data/LSP/images/'+test_dl[i].split(',')[0])
        for j, joint in enumerate(iniJoints):
            cv2.circle(img, joint, 5, (0, 0, 255), -1)
            cv2.putText(img, '%d' % j, joint, cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                   (255, 255, 255))
        cv2.imwrite('map/'+str(i)+'ini.jpg',img)        '''

    sio.savemat('map/ests.mat', {'ests':ests})
    sio.savemat('map/ests2.mat', {'ests2':ests2})
 
    print("test mean loss {a}, accuracy {b}".format(a=sum_loss/test_data_size, b=test_data_size))
    sys.stdout.flush()



    

