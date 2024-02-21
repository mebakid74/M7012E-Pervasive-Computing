import cv2
import time
import os
import pandas
from datetime import datetime
import numpy as np
import threading
from email.mime.text import MIMEText
import smtplib
from picamera.array import PiRGBArray
from picamera import PiCamera

# Importing MotionModel from your custom model file
#from model import MotionModel

# Initialize the MotionModel
#model = MotionModel()

# Initialize the camera
camera = PiCamera()

# Set the camera resolution
camera.resolution = (640, 480)

# Set the number of frames per second
camera.framerate = 30

# Generates a 3D RGB array and stores it in rawCapture
raw_capture = PiRGBArray(camera, size=(640, 480))

# Load the Haar cascade classifier for face detection
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

# Create kernel for morphological operation. You can tweak
# the dimensions of the kernel.
# e.g. instead of 20, 20, you can try 30, 30
kernel = np.ones((20, 20), np.uint8)

# Initialize variables
first_frame = None
status_list = [None, None]
times = []
etime = []
df = pandas.DataFrame(columns=["Start", "End"])

# Open the video capture device
#video = cv2.VideoCapture(0)

# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))

start_time = time.time()
flag = 1

mode = int(input("Enter 1 for Motion Detection, 2 for Intrusion Detection: "))

avg = None

# Define the directory path for the captured folder
captured = "Pi Camera/captured"

# Check if the captured folder exists, if not, create it
if not os.path.exists(captured):
    os.makedirs(captured)

# Main loop
while True:
    # check, frame = video.read()
    frame = np.empty((480, 640, 3), dtype=np.uint8)
    camera.capture(frame, 'bgr', use_video_port=True)

    # status = 0
    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if avg is None:
        print("Starting background model...")
        avg = gray.copy().astype("float")

        continue

    # toggle alpha to how quickly the background average is updated
    # higher alpha = quicker updates to the background image
    # Update the background model using accumulated weighted averages
    cv2.accumulateWeighted(gray, avg, 0.075)

    # Calculate the absolute difference between the current frame and the background
    delta_frame = cv2.absdiff(gray, cv2.convertScaleAbs(first_frame))

    # threshold difference
    thresh_frame = cv2.threshold(delta_frame, 5, 255, cv2.THRESH_BINARY)[1]

    # dilated difference (close the gaps)
    thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

    # Find contours in the threshold image
    # image, contours, hierarchy = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    _, contours, _ = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Check the contours with the motion detection model
    contours_meta, _ = model.compare_frame(gray, avg)
    contour_check = model.check_contours(contours_meta)

    # Loop over the contours
    for contour in contours:
        if cv2.contourArea(contour) < 10000:
            continue
        status = 1

        (x, y, w, h) = cv2.boundingRect(contour)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)

    # If motion is detected by the model, set status to 1
    if contour_check:
        status = 1

    if mode == 2:
        # Intrusion Detection
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=5)

        for (x, y, w, h) in faces:
            frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            status = 1

    # Handling elapsed time and sending email if needed
    status_list.append(status)
    status_list = status_list[-2:]

    if status_list[-1] == 1 and status_list[-2] == 0:
        times.append(datetime.now())
        start_time = time.time()
        print("Intruder has Entered")

        # Specify the full path where you want to save the image
        image_path = os.path.join(captured, f"intruder_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
        cv2.imwrite(image_path, frame)

        #cv2.imwrite("intruder.jpg", frame)
        flag = 0

    if status_list[-1] == 0 and status_list[-2] == 1:
        times.append(datetime.now())
        flag = 1
        print("Intruder has Exited")

    elapsed_time = time.time() - start_time

    if elapsed_time > 3 and flag == 0:
        print("Intruder has been Detected")
        flag = 1

    # Display frames
    #cv2.imshow('all', grid)
    cv2.imshow("Gray Frame", gray)
    cv2.imshow("Delta Frame", delta_frame)
    cv2.imshow("Threshold Frame", thresh_frame)
    cv2.imshow("Color Frame", frame)

    # write the flipped frame
    out.write(frame)

    key = cv2.waitKey(1)

    if key == ord('q'):
        if status == 1:
            times.append(datetime.now())
        break

# Save data to CSV file
for i in range(0, len(times), 2):
    df = df.append({"Start": times[i], "End": times[i + 1]}, ignore_index=True)

df.to_csv("Times.csv")

# Release resources
# video.release()
out.release()
cv2.destroyAllWindows()
