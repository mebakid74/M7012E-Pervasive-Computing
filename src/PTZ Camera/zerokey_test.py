import cv2
import numpy as np
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import queue
import math
import json
from signalrcore.hub_connection_builder import HubConnectionBuilder

# pip install signalrcore
# something is very wrong in this code + need to define borders, and somehow utilize signalrcore which i dont think i did for now
# https://stackoverflow.com/questions/56207448/efficient-quaternions-to-euler-transformation
def quat_to_euler(w, x, y, z):
    ysqr = y * y
    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + ysqr)
    X = math.degrees(math.atan2(t0, t1))
    #X = math.atan2(t0, t1)
    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    Y = math.degrees(math.asin(t2))
    #Y = math.asin(t2)
    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (ysqr + z * z)
    Z = math.degrees(math.atan2(t3, t4))
    #Z = math.atan2(t3, t4)
    return [X, Y, Z]

class SignalRClient:
    def __init__(self):
        self.addr = {
            "urlEH": "http://130.240.105.144:33001/hubs/eventHub", # 130.240.114.115
            "urlApi": "http://130.240.105.144:5000/v2/", #130.240.114.115
            "macPerson": "D5:6D:EF:33:77:14"
        }
        self.client = HubConnectionBuilder()\
               .with_url(self.addr["urlEH"],
                options={
                     "access_token_factory": self.authenticateConnection
        }).build()
        self.client.on_open(lambda: print("connection opened"))
        self.client.on_close(lambda: print("connection closed"))
        self.client.on("Event", self.onCallback)
        self.latestPerson = [0, 0, 0, 0, 0, 0]

    def start(self):
        self.client.start()

    def authenticateConnection(self):
        headers = { "Content-Type": "application/json" }
        body = json.dumps({
            "grant_type": "client_credentials",
            "auth_id": "LocalAdmin",
            "auth_secret": "DefaultSecret"
        })
        authTokenResponse = requests.post(self.addr["urlApi"]+ "auth/token", headers=headers, data=body) 
        authToken = authTokenResponse.json()["access_token"]
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + authToken
        }
        body = json.dumps({
        "QualityOfService": {
            "MaxUpdateRate": 20,
            "MaxThroughput": 10240,
            "AutotuneConnectionParameters": False
        },
        "Mode": "read",
        "Filters": [{"FilterTemplate": "position_events"}]
        })
        endpointIDResponse = requests.post(
            self.addr["urlApi"] + "events/connections", headers=headers, data=body)
        endpointID = endpointIDResponse.json()["EndpointID"]
        return endpointID

    def onCallback(self, e):
        d = json.loads(e[0])
        if d["Source"]["MAC"] == self.addr["macPerson"]:
            angle = d["Content"]["Orientation"]
            self.latestPerson = d["Content"]["Position"] + quat_to_euler(angle[0], angle[1], angle[2], angle[3])

        data = {
            "sensor_x": self.latestPerson[0],
            "sensor_y": self.latestPerson[1],
            "sensor_z": self.latestPerson[2],
        }
        update_data(data)

class RelayWebServer(BaseHTTPRequestHandler):
    queue = None

    def log_message(self, format, *args): pass
    
    def do_GET(self):
        pos = str(RelayWebServer.queue.get())
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes(pos, 'utf-8'))

def update_data(data):
    global border_min_x, border_max_x, border_min_y, border_max_y, border_min_z, border_max_z, sensor_x, sensor_y, sensor_z
    # Assuming data contains sensor coordinates
    sensor_x = data["sensor_x"]
    sensor_y = data["sensor_y"]
    sensor_z = data["sensor_z"]

    # Implement the update logic for border limits
    # For example:
    border_min_x = sensor_x - 10  # Adjust with appropriate values
    border_max_x = sensor_x + 10
    border_min_y = sensor_y - 10
    border_max_y = sensor_y + 10
    border_min_z = sensor_z - 10
    border_max_z = sensor_z + 10


def startHost():
    print("Hosting")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

dataQueue = queue.Queue(maxsize=1)

ip = "130.240.105.144" # "130.240.114.121"
port = 8081

server = HTTPServer((ip, port), RelayWebServer)
RelayWebServer.queue = dataQueue
client = SignalRClient()

t1 = threading.Thread(target=client.start)
t2 = threading.Thread(target=startHost)
t1.start()
t2.start()
