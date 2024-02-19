#set ıntıal posıtıon of camera
import requests

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
control_camera("86BB", "76BF")