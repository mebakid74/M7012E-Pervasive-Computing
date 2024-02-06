# Import the necessary packages
from picamera.array import PiRGBArray
from picamera import PiCamera
import argparse
import datetime
import imutils
import json
import time
import cv2
import uuid
import os

# Define the TempImage class for handling temporary images
class TempImage:
    def __init__(self, basePath="./", ext=".jpg"):
        # Construct the file path
        self.path = "{base_path}/{rand}{ext}".format(base_path=basePath,
            rand=str(uuid.uuid4()), ext=ext)

    def cleanup(self):
        # Remove the file
        os.remove(self.path)

# Construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="path to the JSON configuration file")
args = vars(ap.parse_args())

# Load the configuration
conf = json.load(open(args["conf"]))

# Initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

# Allow the camera to warm up
print("[INFO] Warming up...")
time.sleep(conf["camera_warmup_time"])

# Initialize variables for motion detection
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

# Capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    # Grab the raw NumPy array representing the image and initialize
    # the timestamp and occupied/unoccupied text
    frame = f.array
    timestamp = datetime.datetime.now()
    text = "Unoccupied"
    
    # Resize the frame, convert it to grayscale, and blur it
    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    
    # If the average frame is None, initialize it
    if avg is None:
        print("[INFO] Starting background model...")
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue
    
    # Accumulate the weighted average between the current frame and
    # previous frames, then compute the difference between the current
    # frame and running average
    cv2.accumulateWeighted(gray, avg, 0.5)
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
    
    # Threshold the delta image, dilate the thresholded image to fill
    # in holes, then find contours on thresholded image
    thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    
    # Loop over the contours
    for c in cnts:
        # If the contour is too small, ignore it
        if cv2.contourArea(c) < conf["min_area"]:
            continue
        # Compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = "Occupied"
    
    # Draw the text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    cv2.putText(frame, "Room Status: {}".format(text), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
    
    # Check to see if the room is occupied
    if text == "Occupied":
        # Check to see if enough time has passed between uploads
        if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
            # Increment the motion counter
            motionCounter += 1
            # Check to see if the number of frames with consistent motion is
            # high enough
            if motionCounter >= conf["min_motion_frames"]:
                # Check to see if dropbox should be used
                if conf["use_dropbox"]:
                    # Write the image to a temporary file
                    t = TempImage()
                    cv2.imwrite(t.path, frame)
                    # Upload the image to Dropbox and cleanup the temporary image
                    print("[UPLOAD] {}".format(ts))
                    path = "/{base_path}/{timestamp}.jpg".format(
                        base_path=conf["dropbox_base_path"], timestamp=ts)
                    client.files_upload(open(t.path, "rb").read(), path)
                    t.cleanup()
                # Update the last uploaded timestamp and reset the motion counter
                lastUploaded = timestamp
                motionCounter = 0
    
    # Display the frame
    cv2.imshow("Security Feed", frame)
    key = cv2.waitKey(1) & 0xFF
    # If the `q` key is pressed, break from the loop
    if key == ord("q"):
        break
    
    # Clear the stream in preparation for the next frame
    rawCapture.truncate(0)

# Clean up the camera and close any open windows
cv2.destroyAllWindows()
