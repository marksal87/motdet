# import the necessary packages
from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import cv2
 
# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
#camera.resolution = (2592, 1944)
camera.resolution = (640, 480)
camera.vflip = True
camera.hflip = True
camera.rotation = 0
camera.start_preview()

rawCapture = PiRGBArray(camera)

 
# allow the camera to warmup
#time.sleep(0.1)
time.sleep(2)
 
# grab an image from the camera
camera.capture(rawCapture, format="bgr")
image = rawCapture.array
 
# display the image on screen and wait for a keypress
cv2.imshow("Image", image)
cv2.waitKey(0)
