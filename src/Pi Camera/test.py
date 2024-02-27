import cv2
import time
import os
import pandas as pd
from datetime import datetime
import numpy as np
import imutils
import dropbox
from picamera.array import PiRGBArray
from picamera import PiCamera

# Initialize the Pi Camera
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 30
raw_capture = PiRGBArray(camera, size=(640, 480))

# Load the Haar cascade classifier for face detection
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

# Initialize Dropbox client
access_token = 'token here'
dbx = dropbox.Dropbox(access_token)

# Initialize variables
first_frame = None
status_list = [None, None]
times = []
df = pd.DataFrame(columns=["Start", "End"])

# Define the directory path for the captured folder
captured = "Pi Camera/captured"
if not os.path.exists(captured):
    os.makedirs(captured)
    os.makedirs(os.path.join(captured, "colorframe"))
    os.makedirs(os.path.join(captured, "deltaframe"))
    os.makedirs(os.path.join(captured, "grayframe"))
    os.makedirs(os.path.join(captured, "thresholdframe"))
    os.makedirs(os.path.join(captured, "video"))

# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'H264')
out = None
#out = cv2.VideoWriter(os.path.join(captured, 'output.avi'), fourcc, 20.0, (640, 480))

start_time = time.time()
flag = 1

mode = int(input("Enter 1 for Motion Detection, 2 for Intrusion Detection: "))

# Function to upload a file to Dropbox
def upload_to_dropbox(local_file_path, dropbox_file_path):
    with open(local_file_path, 'rb') as f:
        dbx.files_upload(f.read(), dropbox_file_path)

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
            cv2.putText(frame, "Motion Detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            # Start recording if not already recording
            if out is None:  
                print("Started Recording Intrusion Video")
                out = cv2.VideoWriter(os.path.join(captured, "video", f'video_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.avi'), fourcc, 20.0, (640, 480))
    else:
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=5)
        for (x, y, w, h) in faces:
            frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            status = 1
            
            cv2.putText(frame, "Unauthorized person", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            # Start recording if not already recording
            if out is None:  
                print("Started Recording Motion Video")
                out = cv2.VideoWriter(os.path.join(captured, "video", f'video_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.avi'), fourcc, 20.0, (640, 480))

    status_list.append(status)
    status_list = status_list[-2:]

    if status_list[-1] == 1 and status_list[-2] == 0:
        times.append(datetime.now())
        start_time = time.time()

        # Debug output
        print("Capturing frame...")

        print("Intruder has Entered")
        color_frame_path = os.path.join(captured, "colorframe", f"intruder_color_frame_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")
        cv2.imwrite(color_frame_path, frame)
        upload_to_dropbox(color_frame_path, f'/Pi_Camera_Frames/colorframe/{os.path.basename(color_frame_path)}')
        print("Color Frame captured!")

        gray_frame_path = os.path.join(captured, "grayframe", f"intruder_gray_frame_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")
        cv2.imwrite(gray_frame_path, gray)
        upload_to_dropbox(gray_frame_path, f'/Pi_Camera_Frames/grayframe/{os.path.basename(gray_frame_path)}')
        print("Gray Frame captured!")

        delta_frame_path = os.path.join(captured, "deltaframe", f"intruder_delta_frame_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")
        cv2.imwrite(delta_frame_path, delta_frame)
        upload_to_dropbox(delta_frame_path, f'/Pi_Camera_Frames/deltaframe/{os.path.basename(delta_frame_path)}')
        print("Delta Frame captured!")

        threshold_frame_path = os.path.join(captured, "thresholdframe", f"intruder_thresh_frame_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg")
        cv2.imwrite(threshold_frame_path, thresh_frame)
        upload_to_dropbox(threshold_frame_path, f'/Pi_Camera_Frames/thresholdframe/{os.path.basename(threshold_frame_path)}')
        print("Threshold Frame captured!")

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
    
    #out.write(frame)
    if out is not None:
        out.write(frame)

    # Wait for keyPress for 1 millisecond
    key = cv2.waitKey(1) & 0xFF

    # If "q" is pressed on the keyboard, 
    # exit this loop
    if key == ord('q'):
        if status == 1:
            times.append(datetime.now())
        break

    # Example: Save a frame to Dropbox
    file_name = f'frame_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.jpg'
    local_file_path = os.path.join(captured, file_name)
    cv2.imwrite(local_file_path, frame)
    dropbox_file_path = f'/Pi_Camera_Frames/{file_name}'
    upload_to_dropbox(local_file_path, dropbox_file_path)

    # Clear the stream in preparation for the next frame
    raw_capture.truncate(0)

# Initialize an empty DataFrame
df = pd.DataFrame()

# Save data to CSV file
for i in range(0, len(times), 2):
    df = df.append({"Start": times[i], "End": times[i + 1]}, ignore_index=True)
df.to_csv("Data Time.csv")

# Release resources
#out.release()
if out is not None:
    out.release()
    
# Close down windows
cv2.destroyAllWindows()