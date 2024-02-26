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

# Function to detect and track humans using YOLO
def detect_and_track_human():
    # Load YOLO
    net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

    # Capture video stream
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

                # Perform object detection using YOLO
                blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
                net.setInput(blob)
                outs = net.forward(output_layers)

                # Process the detected objects
                class_ids = []
                confidences = []
                boxes = []
                for out in outs:
                    for detection in out:
                        scores = detection[5:]
                        class_id = np.argmax(scores)
                        confidence = scores[class_id]
                        if confidence > 0.5:
                            # Object detected
                            center_x = int(detection[0] * frame.shape[1])
                            center_y = int(detection[1] * frame.shape[0])
                            w = int(detection[2] * frame.shape[1])
                            h = int(detection[3] * frame.shape[0])
                            x = int(center_x - w / 2)
                            y = int(center_y - h / 2)
                            boxes.append([x, y, w, h])
                            confidences.append(float(confidence))
                            class_ids.append(class_id)

                # Apply non-max suppression to remove redundant overlapping boxes
                indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

                # Draw rectangles around detected objects
                font = cv2.FONT_HERSHEY_PLAIN
                colors = np.random.uniform(0, 255, size=(len(boxes), 3))
                if len(indexes) > 0:
                    for i in indexes.flatten():
                        x, y, w, h = boxes[i]
                        label = str(classes[class_ids[i]])
                        confidence = confidences[i]
                        color = colors[i]
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        cv2.putText(frame, label + " " + str(round(confidence, 2)), (x, y + 30), font, 3, color, 3)

                # Display frame with object detection
                cv2.imshow('Object Detection', frame)

                # Break the loop if 'q' is pressed
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except Exception as e:
        print("An error occurred:", e)

    # Release video capture and close all windows
    cv2.destroyAllWindows()

if __name__ == "__main__":
    detect_and_track_human()
