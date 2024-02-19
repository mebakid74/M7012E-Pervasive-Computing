import cv2
import numpy as np
import requests

# Function to control the camera
def control_camera(pan, tilt):
    url = "http://130.240.105.144/cgi-bin/aw_ptz"
    command = "#APC{}{}".format(pan, tilt)
    params = {
        "cmd": command,
        "res": 1
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("Command sent successfully")
            print("Response:", response.status_code)
        else:
            print("Failed to send command. Status code:", response.status_code)
    except Exception as e:
        print("An error occurred while controlling the camera:", e)

# Function to detect and track humans
def detect_and_track_human():
    # Load pre-trained Haar cascade classifier for full body detection
    human_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    url = "http://130.240.105.144/cgi-bin/mjpeg?resolution=1920x1080&framerate=30&quality=1"
    stream = requests.get(url, stream=True)
    video_bytes = bytes()

    try:
        for chunk in stream.iter_content(chunk_size=1024):
            video_bytes += chunk
            a = video_bytes.find(b'\xff\xd8')
            b = video_bytes.find(b'\xff\xd9')
            if a != -1 and b != -1:
                jpg = video_bytes[a:b+2]
                video_bytes = video_bytes[b+2:]
                frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)

                if frame is None:
                    print("Failed to decode frame")
                    continue

                # Convert frame to grayscale for human detection
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Detect humans
                humans = human_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

                # Draw rectangles around detected humans
                for (x, y, w, h) in humans:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

                # Display frame with human detection
                cv2.imshow('Human Detection', frame)

                # Break the loop if 'q' is pressed
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except Exception as e:
        print("An error occurred:", e)

    # Release video capture and close all windows
    cv2.destroyAllWindows()

if __name__ == "__main__":
    detect_and_track_human()