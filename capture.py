#!/usr/bin/env python3

import socket
import struct
import numpy as np
import cv2

cap = cv2.VideoCapture(0)

sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Parameters for ShiTomasi corner detection
feature_params = dict( maxCorners = 100,
                        qualityLevel = 0.01,
                        minDistance = 7,
                        blockSize = 7 )

# Parameters for lucas kanade optical flow
lk_params = dict( winSize  = (50,50),
                   maxLevel = 2,
                   criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

# Create some random colors
color = np.random.randint(254,255,(100,3))

# Take first frame and find corners in it
ret, old_frame = cap.read()
old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)
p0 = cv2.goodFeaturesToTrack(old_gray, mask = None, **feature_params)

# Create a mask image for drawing purposes
mask = np.zeros_like(old_frame)

# Create an array to calculate moving average
history = []

while(1):
    # Capture frame
    ret,frame = cap.read()
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_gray = cv2.flip(frame_gray, 1)

    # Calculate optical flow
    p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **lk_params)

    # Select good points
    good_new = p1[st==1]
    good_old = p0[st==1]

    # Find corners deviation
    delta = good_new - good_old

    # Find deviation magnitude for each corner
    magnitude = np.sqrt(delta[:,0]**2 + delta[:,1]**2)

    # Only corners with magnitude greater than
    threshold = 8
    # will be taken to account

    delta = delta[magnitude > threshold, :]

    # Handle empty array
    if not delta.any():
        mean = np.zeros(2)
    else:
        mean = delta.mean(axis=0)

    # Apply moving average of last
    n = 3
    # frames

    history.append(mean)
    if len(history) > n:
        history.pop(0)

    mean = np.array(history).mean(axis=0)
    x, y = mean

    # Send data over network to our gaming application
    data = b'joystick1\r\n' + struct.pack('>ff', x / 30, y / 30)
    sock.sendto(data, ('127.0.0.1', 38228))

    # Paint hint
    img = frame_gray.copy()
    img = cv2.line(img, (550, 350), (int(550+x*4), int(350+y*4)), color[0].tolist(), 2)

    print(x, y)

    cv2.imshow('frame', img)
    k = cv2.waitKey(30) & 0xff
    if k == 27:
        break

    # Now update the previous frame and previous points
    old_gray = frame_gray.copy()
    p0 = cv2.goodFeaturesToTrack(old_gray, mask = None, **feature_params)


cv2.destroyAllWindows()
cap.release()
