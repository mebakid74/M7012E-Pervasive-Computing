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

# Function to detect and track motion
def detect_and_track_motion():
    url = "http://130.240.105.144/cgi-bin/mjpeg?resolution=1920x1080&framerate=30&quality=1"
    stream = requests.get(url, stream=True)
    video_bytes = bytes()

    # Initial position of camera
    initial_pan = "89BB"
    initial_tilt = "78BF"
    control_camera(initial_pan, initial_tilt)

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

                # Convert frame to grayscale for motion detection
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Apply Gaussian blur to reduce noise
                blurred_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)

                # Initialize background model for motion detection
                if 'background_model' not in locals():
                    background_model = blurred_frame.copy().astype(np.float32)

                # Update background model
                cv2.accumulateWeighted(blurred_frame, background_model, 0.5)
                background_diff = cv2.absdiff(blurred_frame, cv2.convertScaleAbs(background_model))

                # Apply thresholding to detect motion
                _, motion_mask = cv2.threshold(background_diff, 25, 255, cv2.THRESH_BINARY)

                # Find contours of detected motion
                contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Draw green box around detected motion
                for contour in contours:
                    if cv2.contourArea(contour) > 1000:
                        x, y, w, h = cv2.boundingRect(contour)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Display frame with motion detection
                cv2.imshow('Motion Detection', frame)

                # Break the loop if 'q' is pressed
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except Exception as e:
        print("An error occurred:", e)

    # Release video capture and close all windows
    cv2.destroyAllWindows()

if __name__ == "__main__":
    detect_and_track_motion()
