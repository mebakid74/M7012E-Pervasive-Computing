# Import the necessary packages
from imutils.video import VideoStream
import argparse
import datetime
import imutils
import time
import cv2

# Construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument ("-v", "--video", help="path to the video file") 
ap.add_argument("-a", "--min-area", type=int, default=500, help="minimum area size")
args = vars(ap.parse_args())

# If the video argument is None, then we are reading from webcam
if args.get("video", None) is None:
    vs = VideoStream(src=0).start()
    time.sleep(2.0)

# Otherwise, we are reading from a video file
else:
    vs = cv2.VideoCApture(args["video"])

# Initialize the first frame in the video stream
firstFrame = None

# Loop over the frames of the video
while True:

    # Grab the current frame and initialize the occupied/unoccupied text
    frame = vs.read()
    frame = frame if args.get("video", None) is None else frame[1]
    text = "Unoccupied"

    # If the frame could not be grabbed, then we have reached the end of the video
    if frame is None:
        break

    # Resize the frame, convert it to grayscale and blur it
    frame = imutils.resize(frame, width=500)
    gray = cv2.ctColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)


    # If the first frame is None, initialize it 
    if firstFrame is None:
        firstFrame = gray
        continue

    # Compute the absolute difference between the current frame and first frame
    frameDelta = cv2.absdiff(firstFrame, gray)
    thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY) [1]

    # Dilate hte threshold image to fill in holes, then find contours on threshold image
    thresh = cv2.dilate(thresh, None, iterations=2)
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)

    # Loop over the contours
    for c in cnts:
        # If the contour is too small, ignore it
        if cv2.contourArea(c) < args["min_area"]:
            continue

        # Compute the bounding box for the contour, draw it on the frame and update the text
        (x, y, w, h) = cv2.boundRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = "Authorized person"

        # Draw the text and timestamp on the frame
        cv2.putText(frame, "Room Status: {}".format(text), (10,20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FRONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # Show the frame and record if the user presses a key
        cv2.imshow("Security Feed", frame)
        cv2.imshow("Thresh", thresh)
        cv2.imshow("Frame Delta", frameDelta)
        key = cv2.waitkey(1) & 0xFF

        # If the "q" key is pressed, break the loop
        if key == ord("q"):
            break

        # Cleanup the camera and close any open window
        vs.stop() if args.get("video", None) is None else vs.release()
        cv2.destroyAllWindows()
        