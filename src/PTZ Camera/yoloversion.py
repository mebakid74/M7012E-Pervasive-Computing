import cv2
import argparse
import numpy as np
import imutils
import sys
import threading
from controller import Controller
import requests
sys.path.insert(0, 'mebakid74/Raspberry-Pi-Home-Security-System-M7012E/src/PTZ Camera')


# controller.rotate(180, 140)
controller = Controller()

ap = argparse.ArgumentParser()
ap.add_argument('-c', '--config', required=True,
                help = 'mebakid74/Raspberry-Pi-Home-Security-System-M7012E/src/PTZ Camera/yolov3.cfg')
ap.add_argument('-w', '--weights', required=True,
                help = 'mebakid74/Raspberry-Pi-Home-Security-System-M7012E/src/PTZ Camera/yolov3.weights')
ap.add_argument('-cl', '--classes', required=True,
                help = 'mebakid74/Raspberry-Pi-Home-Security-System-M7012E/src/PTZ Camera/yolov3.txt')
args = ap.parse_args()

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
        color = (0, 255, 0) # green
        cv2.rectangle(img, (x, y), (x_plus_w, y_plus_h), color, 2)
        cv2.putText(img, label, (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

net = cv2.dnn.readNet(args.weights, args.config)

conf_threshold = 0.3
nms_threshold = 0.4

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
        print("An error occurred:", e)

# Example: Sending the command to set pan to 7FFF and tilt to 7FFF
#control_camera("86BB", "76BF")





cap = cv2.VideoCapture(controller.kitchenCameraURL) 

while True:
    ret, frame = cap.read()
    
    if not ret:
        break

    frame = imutils.resize(frame, width=min(400, frame.shape[1]))

    Width = frame.shape[1]
    Height = frame.shape[0]
    scale = 0.00392

    blob = cv2.dnn.blobFromImage(frame, scale, (256,256), (0,0,0), True, crop=False)

    net.setInput(blob)

    outs = net.forward(get_output_layers(net))

    class_ids = []
    confidences = []
    boxes = []

    for detection in outs[0]:
        scores = detection[5:]
        class_id = np.argmax(scores)
        confidence = scores[class_id]
        if class_id == 0 and confidence > conf_threshold:
            center_x = int(detection[0] * Width)
            center_y = int(detection[1] * Height)
            w = int(detection[2] * Width)
            h = int(detection[3] * Height)
            x = center_x - w / 2
            y = center_y - h / 2
            class_ids.append(class_id)
            confidences.append(float(confidence))
            boxes.append([x, y, w, h])
            break

    indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)

    for i in indices:
        try:
            box = boxes[i]
        except:
            i = i[0]
            box = boxes[i]

        x = box[0]
        y = box[1]
        w = box[2]
        h = box[3]
        draw_prediction(frame, class_ids[i], round(x), round(y), round(x+w), round(y+h))

    cv2.imshow("object detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break




cap.release()
cv2.destroyAllWindows()