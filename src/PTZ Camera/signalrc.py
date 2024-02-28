import requests
import json
from signalrcore.hub_connection_builder import HubConnectionBuilder

eventHubUrl = "http://http://130.240.105.144:33001/hubs/eventHub" # Url of event hub signalR
apiUrl = "http://http://130.240.105.144:5000/v3/"  # Url of the EventHub API

def main():
   hub_connection = HubConnectionBuilder()\
       .with_url(eventHubUrl,
                 options={
                     "access_token_factory": authenticateConnection
                 })\
       .build()

   hub_connection.on_open(lambda: print(
       "connection opened and handshake received ready to send messages"))
   hub_connection.on_close(lambda: print("connection closed"))
   hub_connection.on("Event", print)
   hub_connection.start()


def authenticateConnection():
   # Get Bearer token
   headers = {
       "Content-Type": "application/json"
   }
   body = json.dumps({
       "grant_type": "client_credentials",
       "auth_id": "admin",
       "auth_secret": "admin"
   })
   authTokenResponse = requests.post(
       apiUrl + "auth/token", headers=headers, data=body)
   authToken = authTokenResponse.json()["access_token"]

   # Initiate connection details to obtain EndpointID
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
       apiUrl + "events/connections", headers=headers, data=body)
   endpointID = endpointIDResponse.json()["EndpointID"]

   return endpointID

if __name__ == "__main__":
   main()