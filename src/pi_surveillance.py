import pyimgage.tempimgage import tempimage
from picamera.array import PiRBGArray
from picamera import PiCAmera
import argparse
impot warnings
import datetime
import imutils
import json
import time
import cv2
import dropbox


# Construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="path to the JSON configuration file")
args = vars(ap.parse_args())

# Filter warnings, load the configuration and initialize the Dropbox client
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None