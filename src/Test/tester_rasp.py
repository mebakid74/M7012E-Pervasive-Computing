import cv2
import time
import pandas
from datetime import datetime

import smtplib
import threading
from email.mime.text import MIMEText

# Load the Haar cascade for face detection
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

# Email configuration
gmail_user = "your_email@gmail.com"
gmail_pwd = "your_password"
smtp_ssl_host = 'smtp.gmail.com'
smtp_ssl_port = 465
sender = 'your_email@gmail.com'
targets = ['recipient_email@gmail.com']

# Initialize variables
first_frame = None
status_list = [None, None]
times = []
etime = []
df = pandas.DataFrame(columns=["Start", "End"])

# Initialize the Pi camera
camera = cv2.VideoCapture(0)  # Use the primary camera (index 0)

# Adjust camera settings (optional)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Set frame width
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # Set frame height

start_time = time.time()
flag = 1
mode = int(input("Enter 1 for Motion Detection, 2 for Intrusion Detection: "))

def mail():
    # Email content
    msg = MIMEText('Intrusion is occurring')
    msg['Subject'] = 'Security Alert'
    msg['From'] = sender
    msg['To'] = ', '.join(targets)

    # Send email
    server = smtplib.SMTP_SSL(smtp_ssl_host, smtp_ssl_port)
    server.login(gmail_user, gmail_pwd)
    server.sendmail(sender, targets, msg.as_string())
    server.quit()

while True:
    # Capture frame-by-frame
    check, frame = camera.read()
    status = 0
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    
    if mode == 1:
        # Motion Detection
        if first_frame is None:
            first_frame = gray
            continue

        delta_frame = cv2.absdiff(first_frame, gray)
        thresh_frame = cv2.threshold(delta_frame, 30, 255, cv2.THRESH_BINARY)[1]
        thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

        (cnts, _) = cv2.findContours(thresh_frame.copy(),
                                    cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in cnts:
            if cv2.contourArea(contour) < 10000:
                continue
            status = 1
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
    else:
        # Face Detection
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=5)

        for x, y, w, h in faces:
            frame = cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
            status = 1

    status_list.append(status)
    status_list = status_list[-2:]
    


    if status_list[-1] == 1 and status_list[-2] == 0:
        times.append(datetime.now())
        start_time = time.time()
        print("Enter")
        cv2.imwrite("intruder.jpg", frame)
        flag = 0

    if status_list[-1] == 0 and status_list[-2] == 1:
        times.append(datetime.now())
        flag = 1
        print("exit")

    elapsed_time = time.time() - start_time

    if elapsed_time > 3 and flag == 0:
        print("intruder")
        if len(etime) == 0:
            etime.append(time.time())
            t1 = threading.Thread(target=mail, args=())
            t1.start()

        else:
            etime.append(time.time())
        emailtimelapse = etime[-1]-time.time()
        if emailtimelapse > 50000:
            mail()
        flag = 1
        # Display the resulting frames
    cv2.imshow("Frame", frame)  # Original frame with detections
    cv2.imshow("Gray Frame", gray)  # Gray frame
    cv2.imshow("Delta Frame", delta_frame)  # Delta frame
    cv2.imshow("Threshold Frame", thresh_frame)  # Threshold frame


    # Display the resulting frame
    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1)

    if key == ord('q'):
        if status == 1:
            times.append(datetime.now())
        break

print(status_list)
print(times)

# Save the detected times to a CSV file
for i in range(0, len(times), 2):
    df = df.append({"Start": times[i], "End": times[i+1]}, ignore_index=True)

df.to_csv("Intrusion_Times.csv")

# Release the camera and close all windows
camera.release()
cv2.destroyAllWindows()
