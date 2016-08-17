# import the necessary packages
import httplib2
import sys
from apiclient.discovery import build
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
import os.path
from googleapiclient.http import MediaFileUpload

from pyimagesearch.tempimage import TempImage
from picamera.array import PiRGBArray
from picamera import PiCamera
import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2
import traceback
import pycurl
from urllib.parse import urlencode


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True,
    help="path to the JSON configuration file")
ap.add_argument("-n", "--noIFTTT", help="this prevents triggering an event on IFTTT.com",
    action="store_true")
args = vars(ap.parse_args())

# filter warnings, load the configuration and initialize the Google Drive client
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
#client = client.DocsClient()
client_id = conf["gdrive_clientid"]
client_secret = conf["gdrive_secret"]
scope = conf["gdrive_scope"]

useIFTTT = True
if args["noIFTTT"]:
    useIFTTT = False
IFTTT_path = conf["IFTTT_path"]

if conf["use_googledrive"]:

    # connect to google drive OAuth2 and start the session authorization process
    flow = OAuth2WebServerFlow(client_id, client_secret, scope)

    # create Storage object that holds credentials
    # If the file does not exist, it is created.
    storage = Storage('credentials.dat')

    # The get() function returns the credentials for the Storage object. If no
    # credentials were found, None is returned.
    credentials = storage.get()

    # If no credentials are found or the credentials are invalid due to
    # expiration, new credentials need to be obtained from the authorization
    # server. The oauth2client.tools.run_flow() function attempts to open an
    # authorization server page in your default web browser. The server
    # asks the user to grant your application access to the user's data.
    # If the user grants access, the run_flow() function returns new credentials.
    # The new credentials are also stored in the supplied Storage object,
    # which updates the credentials.dat file.
    if credentials is None or credentials.invalid:
            credentials = tools.run_flow(flow, storage, tools.argparser.parse_args())

    # Create an httplib2.Http object to handle our HTTP requests, and authorize it
    # using the credentials.authorize() function.
    http = httplib2.Http()
    http = credentials.authorize(http)

    # The apiclient.discovery.build() function returns an instance of an API service
    # object can be used to make API calls. The object is constructed with
    # methods specific to the calendar API. The arguments provided are:
    #   name of the API ('calendar')
    #   version of the API you are using ('v3')
    #   authorized httplib2.Http() object that can be used for API calls
    service = build('drive', 'v3', http=http)

    try:
            # Test connection
            request = service.files().list(pageSize=1)
            response = request.execute()
            response = None
            request = None
            print("[SUCCESS] Google Drive account connected")
    except AccessTokenRefreshError:
            print('The credentials have been revoked or expired, please re-run'
                  'the application to re-authorize')


# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
camera.vflip = True
camera.hflip = True
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

# allow the camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print("[INFO] warming up...")
timestamp = datetime.datetime.now()
time.sleep(conf["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0
dispMode = 0

# capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    # check FPS
    frameTimeDelta = (datetime.datetime.now() - timestamp).total_seconds()
    fps = 1 / frameTimeDelta if frameTimeDelta > 0 else 0

    # grab the raw NumPy array representing the image and initialize
    # the timestamp and occupied/unoccupied text
    frame = f.array
    timestamp = datetime.datetime.now()
    text = "Unoccupied"

    # resize the frame, convert it to grayscale, and blur it
    frame = imutils.resize(frame, width=500)  #width was 500
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    # if the average frame is None, initialize it
    if avg is None:
        print("[INFO] starting background model...")
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue

    # accumulate the weighted average between the current frame and
    # previous frames, then compute the difference between the current
    # frame and running average
    cv2.accumulateWeighted(gray, avg, 0.5)
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

    # threshold the delta image, dilate the thresholded image to fill
    # in holes, then find contours on thresholded image
    thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255,
        cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    #OpenCV2.4 code:  (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]

    # loop over the contours
    for c in cnts:
        # if the contour is too small, ignore it
        if cv2.contourArea(c) < conf["min_area"]:
            continue

        # compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = "Occupied"

    # draw the text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    cv2.putText(frame, "Room Status: {}".format(text), (10, 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
        0.35, (0, 0, 255), 1)
    cv2.putText(frame, "FPS: {}".format(fps), (10, 60),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # check to see if the room is occupied
    if text == "Occupied":
        # check to see if enough time has passed between uploads
        if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
            # increment the motion counter
            motionCounter += 1

            # check to see if the number of frames with consistent motion is
            # high enough
            if motionCounter >= conf["min_motion_frames"]:
                # check to see if google drive should be used
                if conf["use_googledrive"]:
                    # write the image to temporary file
                    t = TempImage()
                    #cv2.imwrite(t.path, frame)
                    cv2.imwrite(t.path, f.array)  # capture full size img

                    # upload the image to Dropbox and cleanup the tempory image
                    #print("[UPLOAD] {}".format(ts))
                    #path = "{base_path}/{timestamp}.jpg".format(
                    #    base_path=conf["dropbox_base_path"], timestamp=ts)
                    #client.put_file(path, open(t.path, "rb"))

                    # upload the image to google
                    print("[UPLOAD] {}".format(ts))
                    #path = "{base_path}/{timestamp}.jpg".format(
                                        #        base_path=conf["gdrive_base_path"], timestamp=ts)
                    #CODE TO UPLOAD THE FILE HERE
                    gdriveImageID = 0
                    try:
                        http = httplib2.Http()
                        http = credentials.authorize(http)
                        service = build('drive', 'v3', http=http)
                        gdrive_filename = "motion_{timestamp}.jpg".format(timestamp=ts)
                        media = MediaFileUpload(t.path, mimetype='image/jpeg')
                        uploadBody = {
                            'name': gdrive_filename,
                            'description': 'Motion detected',
                            'mimeType': 'image/jpeg',
                            'parents': [
                                "0B9M2ehh0drEDdUtSRnJtbjBWUE0"
                            ]
                        }
                        request = service.files().create(body=uploadBody, media_body=media)
                        response = request.execute()
                        gdriveImageID = response.get('id')
                    except Exception as ex:
                        template = "An exception of type {0} occured. Arguments:\n{1!r}"
                        message = template.format(type(ex).__name__, ex.args)
                        print(message)
                        print(traceback.format_exc())

                    # Send Trigger to IFTT Maker
                    if useIFTTT:
                        curl = pycurl.Curl()
                        curl.setopt(curl.URL, IFTTT_path)
                        imgLink = ""
                        if gdriveImageID:
                            imgLink = "https://drive.google.com/file/d/{imageID}/view".format(imageID=gdriveImageID)
                        post_data = {'value1': "{timestamp}".format(timestamp=ts), 'value2': imgLink}
                        postfields = urlencode(post_data)
                        curl.setopt(curl.POSTFIELDS, postfields)
                        curl.perform()
                        curl.close()

                    t.cleanup()

                # update the last uploaded timestamp and reset the motion
                # counter
                lastUploaded = timestamp
                motionCounter = 0

    # otherwise, the room is not occupied
    else:
        motionCounter = 0

    # check to see if the frames should be displayed to screen
    if conf["show_video"]:

                # display the security feed
                if dispMode == 1:
                        cv2.imshow("Security Feed", gray)
                elif dispMode == 2:
                        cv2.imshow("Security Feed", thresh)
                else:
                        cv2.imshow("Security Feed", frame)

        # display the security feed
        #cv2.imshow("Security Feed", frame)
        #cv2.imshow("Security Feed", gray)
        #cv2.imshow("Security Feed", thresh)
                key = cv2.waitKey(1) & 0xFF

        # if the 't' key is pressed, cycle video type...
                if key == ord('t'):
                        dispMode = dispMode + 1
                        if dispMode > 2:
                                dispMode = 0

        # if the `q` key is pressed, break from the loop
                if key == ord("q"):
                        break

    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)

