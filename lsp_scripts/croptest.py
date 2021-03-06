import numpy as np
import cv2 

#_/_/_/ xs: read image & joint _/_/_/  
img = cv2.imread('data/LSP/images/im00489.jpg')
line = 'im00489.jpg,0.0,-24.0428222474,0.0,-24.0428222474,0.0,-24.0428222474,142.208841219,151.1135902,119.14554136,181.864656679,120.807761169,223.598246901,0.0,-24.0428222474,0.0,-24.0428222474,0.0,-24.0428222474,157.584374459,109.379999978,175.720379883,123.68696334,179.015137005,145.652010825,147.165818152,101.157948419,136.183294409,84.6841628049'
datum = line.split(',')
joints = np.asarray([int(float(p)) for p in datum[1:]])         


joints = joints.reshape((len(joints) / 2, 2))





#_/_/_/ flip _/_/_/
if np.random.randint(2) != 3:
	datum[0] = 'flip'+datum[0]
	img = np.fliplr(img)
	joints[:,0] = img.shape[1] - joints[:,0]
	joints = list(zip(joints[:,0], joints[:,1]))

	joints[0], joints[5] = joints[5], joints[0] #ankle
	joints[1], joints[4] = joints[4], joints[1] #knee
	joints[2], joints[3] = joints[3], joints[2] #hip
	joints[6], joints[11] = joints[11], joints[6] #wrist
	joints[7], joints[10] = joints[10], joints[7] #elbow
	joints[8], joints[9] = joints[9], joints[8] #shoulder

joints = np.array(joints).flatten()
joints = joints.reshape((len(joints) / 2, 2))

delete = []
for v in range(len(joints)):
	if  joints[v,0] < 0 or joints[v,1] < 0 or joints[v,0] > img.shape[1] or joints[v,1] > img.shape[0]:
		delete.append(v)

#_/_/_/ image cropping _/_/_/
visible_joints = joints.copy()
print(visible_joints)
visible_joints = np.delete(visible_joints, (delete), axis=0)
print(visible_joints)
visible_joints = visible_joints.astype(np.int32)
print(visible_joints)
x, y, w, h = cv2.boundingRect(np.asarray([visible_joints.tolist()]))
print(visible_joints)
print('{} {} {} {}'.format(x,y,w,h))

inf, sup = 1.5, 2.0
r = sup - inf
pad_w_r = np.random.rand() * r + inf  # inf~sup
pad_h_r = np.random.rand() * r + inf  # inf~sup
x -= (w * pad_w_r - w) / 2
y -= (h * pad_h_r - h) / 2
w *= pad_w_r
h *= pad_h_r

#_/_/_/ shifting _/_/_/
x += np.random.rand() * 5 * 2 - 5
y += np.random.rand() * 5 * 2 - 5

x, y, w, h = [int(z) for z in [x, y, w, h]]
x = np.clip(x, 0, img.shape[1] - 1)
y = np.clip(y, 0, img.shape[0] - 1)
w = np.clip(w, 1, img.shape[1] - (x + 1))
h = np.clip(h, 1, img.shape[0] - (y + 1))
img = img[y:y + h, x:x + w]   

joints = np.asarray([(j[0] - x, j[1] - y) for j in joints])


#_/_/_/ resize _/_/_/
orig_h, orig_w, _ = img.shape
joints[:,0] = joints[:,0] / float(orig_w) * 224
joints[:,1] = joints[:,1] / float(orig_h) * 224
img = cv2.resize(img, (224, 224),interpolation=cv2.INTER_NEAREST)
mean = np.array([113.970, 110.130, 103.804])
#xs[i, :, :, :] = ((img - mean)/255).transpose(2, 0, 1)

joints = joints.astype(np.int32)

joints = [tuple(p) for p in joints]
for j, joint in enumerate(joints):
	cv2.circle(img, joint, 5, (0, 0, 255), -1)
cv2.imwrite(datum[0],img)
