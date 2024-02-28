import cv2
import argparse
import numpy as np
import imutils
import threading
import requests

# Define PTZ camera parameters
CAMERA_URL = "http://130.240.105.144/cgi-bin/aw_ptz"
COMMAND_TEMPLATE = "%43APC{pan}{tilt}"

# Define object detection parameters
CONF_THRESHOLD = 0.3
NMS_THRESHOLD = 0.4

# Define authorized person's Zerokey sensor information
AUTHORIZED_PERSON_MAC = "F8:8A:6C:0A:56:49"


# Load YOLO model
def load_yolo(weights, config):
    net = cv2.dnn.readNet(weights, config)
    return net


def get_output_layers(net):
    layer_names = net.getLayerNames()
    try:
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
    except:
        output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
    return output_layers


def draw_prediction(img, class_id, x, y, x_plus_w, y_plus_h):
    if class_id == 0:
        label = 'person'
        color = (0, 255, 0)  # green
        cv2.rectangle(img, (x, y), (x_plus_w, y_plus_h), color, 2)
        cv2.putText(img, label, (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


def detect_objects(frame, net):
    confidences = []
    boxes = []
    Width = frame.shape[1]
    Height = frame.shape[0]
    scale = 0.00392
    blob = cv2.dnn.blobFromImage(frame, scale, (256, 256), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(get_output_layers(net))
    for detection in outs[0]:
        scores = detection[5:]
        class_id = np.argmax(scores)
        confidence = scores[class_id]
        if class_id == 0 and confidence > CONF_THRESHOLD:
            center_x = int(detection[0] * Width)
            center_y = int(detection[1] * Height)
            w = int(detection[2] * Width)
            h = int(detection[3] * Height)
            x = center_x - w / 2
            y = center_y - h / 2
            confidences.append(float(confidence))
            boxes.append([x, y, w, h])
            break
    return confidences, boxes


def control_camera(pan, tilt):
    command = COMMAND_TEMPLATE.format(pan=pan, tilt=tilt)
    params = {"cmd": command, "res": "1"}
    try:
        response = requests.post(CAMERA_URL, params=params)
        if response.status_code == 200:
            print("Person detection successfully")
        else:
            print("Failed to adjust camera. Status code:", response.status_code)
    except requests.RequestException as e:
        print("Error detection:", e)


# Method to check if the person detected matches the authorized person
def is_authorized_person(mac_address):
    # Implement your logic here to determine if the person is authorized
    # You can use the sensor data to perform authorization checks
    # For now, just return True to authorize all detections
    return True
    #return mac_address == AUTHORIZED_PERSON_MAC

def main(args):
    # Load YOLO model
    net = load_yolo(args.weights, args.config)

    # Initialize camera
    cap = cv2.VideoCapture('http://130.240.105.144/cgi-bin/mjpeg?resolution=1920x1080&framerate=30&quality=1')

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = imutils.resize(frame, width=min(400, frame.shape[1]))

        confidences, boxes = detect_objects(frame, net)

        for i, conf in enumerate(confidences):
            box = boxes[i]
            x, y, w, h = box
            draw_prediction(frame, 0, round(x), round(y), round(x + w), round(y + h))

            # Adjust camera to keep the object (person) in view
            object_center_x = x + w / 2
            object_center_y = y + h / 2
            pan_angle = 90 - (object_center_x / frame.shape[1]) * 180
            tilt_angle = 90 - (object_center_y / frame.shape[0]) * 180
            control_camera(pan_angle, tilt_angle)

            # Extract MAC address from the sensor data
            sensor_data = "[2024-02-27T10:52:01.2499] |I| rf_cmd_update_position: Node: F8:8A:6C:0A:56:49 seq: 1713 pos: -2.57510,3.40790,0.12585 vel: 0.00000,0.00000,0.00000 rot: 0.03202,-0.61422,-0.78848,-0.00182"
            mac_address = sensor_data.split("Node: ")[1].split(" ")[0]

            # Check if the detected person is authorized
            if is_authorized_person(mac_address):
                label = 'Authorized'
                color = (0, 255, 0)  # Green for authorized persons
            else:
                label = 'Unauthorized'
                color = (0, 0, 255)  # Red for unauthorized persons

            # Convert coordinates to integers
            x, y, w, h = int(x), int(y), int(w), int(h)

            # Draw bounding box and label
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label, (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Adjust camera to keep the object (person) in view
            object_center_x = x + w / 2
            object_center_y = y + h / 2
            pan_angle = 90 - (object_center_x / frame.shape[1]) * 180
            tilt_angle = 90 - (object_center_y / frame.shape[0]) * 180
            control_camera(pan_angle, tilt_angle)

        cv2.imshow("Object Detection and PTZ Control", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--config', required=True,
                    help='mebakid74/Raspberry-Pi-Home-Security-System-M7012E/src/PTZ Camera/yolov3.cfg')
    ap.add_argument('-w', '--weights', required=True,
                    help='mebakid74/Raspberry-Pi-Home-Security-System-M7012E/src/PTZ Camera/yolov3.weights')
    ap.add_argument('-cl', '--classes', required=True,
                    help='mebakid74/Raspberry-Pi-Home-Security-System-M7012E/src/PTZ Camera/yolov3.txt')
    args = ap.parse_args()

    main(args)
