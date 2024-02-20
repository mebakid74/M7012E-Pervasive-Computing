import cv2
import time
import pandas
from datetime import datetime
import numpy as np
import threading
from email.mime.text import MIMEText
import smtplib
from picamera.array import PiRGBArray
from picamera import PiCamera

# Importing MotionModel from your custom model file
from model import MotionModel

# Initialize the MotionModel
model = MotionModel()

# Load the Haar cascade classifier for face detection
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

"""
gmail_user = "rakeshranjan8792@gmail.com"
gmail_pwd = "rakranjan"
"""

# Initialize variables
first_frame = None
status_list = [None, None]
times = []
etime = []
df = pandas.DataFrame(columns=["Start", "End"])

# Open the video capture device
video = cv2.VideoCapture(0)
start_time = time.time()
flag = 1

mode = int(input("Enter 1 for Motion Detection, 2 for Intrusion Detection: "))

"""
# Function to send email
def send_email():
    smtp_ssl_host = 'smtp.gmail.com'
    smtp_ssl_port = 465
    username = 'rakeshranjan8792@gmail.com'
    password = 'rakranjan'
    sender = 'rakeshranjan8792@gmail.com'
    targets = ['rakesh.emperor@gmail.com']

    msg = MIMEText('Intrusion is occurring')
    msg['Subject'] = 'Security Alert'
    msg['From'] = sender
    msg['To'] = ', '.join(targets)

    server = smtplib.SMTP_SSL(smtp_ssl_host, smtp_ssl_port)
    server.login(username, password)
    server.sendmail(sender, targets, msg.as_string())
    server.quit()
"""

# Main loop
while True:
    check, frame = video.read()
    
    #status = 0
    frame = imutils.resize(frame, width=500)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
   
    if first_frame is None:
        print("Starting background model...")
        first_frame = gray.copy().astype("float")
        
        continue

    # toggle alpha to how quickly the background average is updated
    # higher alpha = quicker updates to the background image
    # Update the background model using accumulated weighted averages
    cv2.accumulateWeighted(gray, first_frame, 0.075)    
    
    # Calculate the absolute difference between the current frame and the background
    delta_frame = cv2.absdiff(gray, cv2.convertScaleAbs(first_frame))

    """
    # Threshold the difference to obtain binary image
    thresh_frame = cv2.threshold(delta_frame, 30, 255, cv2.THRESH_BINARY)[1]
    thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)
    """

    # thresholded difference
    thresh_frame = cv2.threshold(delta_frame, 5, 255, cv2.THRESH_BINARY)[1]

    # dilated difference (close the gaps)
    thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

    # Find contours in the thresholded image
    image, contours, hierarchy = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Check the contours with the motion detection model
    contours_meta, _ = model.compare_frame(gray, first_frame)
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
            frame = cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
            status = 1

    # Handling elapsed time and sending email if needed
    status_list.append(status)
    status_list = status_list[-2:]

    if status_list[-1] == 1 and status_list[-2] == 0:
        times.append(datetime.now())
        start_time = time.time()
        print("Intruder has Entered")
        cv2.imwrite("intruder.jpg", frame)
        flag = 0

    if status_list[-1] == 0 and status_list[-2] == 1:
        times.append(datetime.now())
        flag = 1
        print("Intruder has Exited")

    elapsed_time = time.time() - start_time

    """
    if elapsed_time > 3 and flag == 0:
        print("Intruder has been Detected")
        if len(etime) == 0:
            etime.append(time.time())
            t1 = threading.Thread(target=send_email, args=())
            t1.start()

        else:
            etime.append(time.time())
        email_timelapse = etime[-1] - time.time()
        if email_timelapse > 50000:
            send_email()
        flag = 1
    """

    if elapsed_time > 3 and flag == 0:
        print("Intruder has been Detected")
        flag = 1

    # Display frames
    cv2.imshow('all', grid)
    cv2.imshow("Gray Frame", gray)
    cv2.imshow("Delta Frame", delta_frame)
    cv2.imshow("Threshold Frame", thresh_frame)
    cv2.imshow("Color Frame", frame)

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
video.release()
cv2.destroyAllWindows()