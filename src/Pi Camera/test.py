import cv2
import time
import os
import pandas as pd
from datetime import datetime
import numpy as np
import imutils
from picamera.array import PiRGBArray
from picamera import PiCamera

# Initialize the camera
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 30
raw_capture = PiRGBArray(camera, size=(640, 480))

# Load the Haar cascade classifier for face detection
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

# Initialize variables
first_frame = None
status_list = [None, None]
times = []
df = pd.DataFrame(columns=["Start", "End"])

# Define the directory path for the captured folder
captured = "Pi Camera/captured"
if not os.path.exists(captured):
    os.makedirs(captured)

# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))

start_time = time.time()
flag = 1

mode = int(input("Enter 1 for Motion Detection, 2 for Intrusion Detection: "))

# Main loop
for frame in camera.capture_continuous(raw_capture, format="bgr", use_video_port=True):
    frame = frame.array
    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if first_frame is None:
        print("Starting background model...")
        first_frame = gray.copy().astype("float")
        raw_capture.truncate(0)
        continue

    delta_frame = cv2.absdiff(first_frame.astype(np.uint8), gray)
    thresh_frame = cv2.threshold(delta_frame, 30, 255, cv2.THRESH_BINARY)[1]
    thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

    status = 0

    if mode == 1:
        (cnts, _) = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in cnts:
            if cv2.contourArea(contour) < 10000:
                continue
            status = 1
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)

    else:
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=5)
        for (x, y, w, h) in faces:
            frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            status = 1

    status_list.append(status)
    status_list = status_list[-2:]

    if status_list[-1] == 1 and status_list[-2] == 0:
        times.append(datetime.now())
        start_time = time.time()
        print("Intruder has Entered")
        image_path = os.path.join(captured, f"intruder_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")
        cv2.imwrite(image_path, frame)

        out.write(frame)

        flag = 0

    if status_list[-1] == 0 and status_list[-2] == 1:
        times.append(datetime.now())
        flag = 1
        print("Intruder has Exited")

    elapsed_time = time.time() - start_time

    if elapsed_time > 3 and flag == 0:
        print("Intruder has been Detected")
        flag = 1

    cv2.imshow("Gray Frame", gray)
    cv2.imshow("Delta Frame", delta_frame)
    cv2.imshow("Threshold Frame", thresh_frame)
    cv2.imshow("Color Frame", frame)
    
    out.write(frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        if status == 1:
            times.append(datetime.now())
        break

    raw_capture.truncate(0)

# Save data to CSV file
for i in range(0, len(times), 2):
    df = df.append({"Start": times[i], "End": times[i + 1]}, ignore_index=True)
df.to_csv("Times.csv")

# Release resources
out.release()
cv2.destroyAllWindows()