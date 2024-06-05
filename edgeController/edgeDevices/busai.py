import datetime
import torch
TORCH_VERSION = ".".join(torch.__version__.split(".")[:2])
CUDA_VERSION = torch.__version__.split("+")[-1]
print("torch: ", TORCH_VERSION, "; cuda: ", CUDA_VERSION)

import os
HOME = os.getcwd()
print(HOME)

"""## Install YOLOv5"""

from IPython import display
display.clear_output()

import ultralytics
ultralytics.checks()

import detectron2
print("detectron2:", detectron2.__version__)

import supervision as sv
print("supervision", sv.__version__)

"""## Download data"""
# Current folder
current_script_directory = os.path.dirname(os.path.realpath(__file__))

# Navigate to the parent folder
parent_folder = os.path.abspath(os.path.join(current_script_directory, os.pardir))
parent_of_parent = os.path.abspath(os.path.join(parent_folder, os.pardir))

# Specify the file name you want to access in the parent folder
file_in_parent_folder = os.path.join(parent_of_parent, 'GitRepo_LargeFiles')
subfile = os.path.join(file_in_parent_folder, 'bus-raspberry')

SUBWAY_VIDEO_PATH = os.path.join(subfile, 'iot_bus.mp4')
YOLO_PATH = os.path.join(file_in_parent_folder, 'yolov8s.pt')

from ultralytics import YOLO
model = YOLO(YOLO_PATH)

import asyncio
import numpy as np
import supervision as sv
import cv2
import requests
import pandas as pd
import threading
import time
import random
import sys
from flask import Flask, request

ids = sys.argv[1:]

# Check if ids are provided
if ids:
    print("Received ids:", ids)
else:
    print("No ids provided.")

crowdflowid = ids[0]
vehicleid= ids[1]

Favierou_vid = 0
video_ended_event = threading.Event()

app = Flask(__name__)

@app.route('/video_ended', methods=['POST'])
def handle_request():
    global Favierou_vid
    data = request.get_json()
    # Use request.args to get query parameters from the URL
    favierou_vid_param = data['favierou_vid']

    if favierou_vid_param is not None:
        Favierou_vid = int(favierou_vid_param)
        print("\n")
        print("\n")
        print(Favierou_vid)
        print("\n")
        print("\n")
        if Favierou_vid == 1:
            video_ended_event.set()
        return 'Request handled successfully'
    else:
        # Handle the case where 'favierou_vid' parameter is not provided
        return 'Missing "favierou_vid" parameter', 400

class StoppableThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

video_info = sv.VideoInfo.from_video_path(SUBWAY_VIDEO_PATH)
print("video_info", video_info)
# initiate polygon zone
polygon = np.array([
    [0, 1920],
    [0, 1920//2],
    [1080, 1920//2],
    [1080, 1920]
])
zone = sv.PolygonZone(polygon=polygon, frame_resolution_wh=video_info.resolution_wh)

# initiate annotators
box_annotator = sv.BoxAnnotator(thickness=4, text_thickness=4, text_scale=2)
zone_annotator = sv.PolygonZoneAnnotator(zone=zone, color=sv.Color.white(), thickness=6, text_thickness=6, text_scale=4)
max=0

z_1 = [False]
m=0
max_people = 0
processing_video = False 

def send_data(locations):
    edge_controller_url = 'http://localhost:5002/receive_bus_data' 
    data = {"locations": locations[0]['Location'], "vehicleid":vehicleid, "crowdflowid": crowdflowid, "busnumber": "601"}

    try:
        response = requests.post(edge_controller_url, json=data)
        response.raise_for_status()
        print("Data sent successfully to context broker.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to context broker: {e}")

def send_to_station(max_people ,station_info):
    station_url = 'http://localhost:5001/receive_data'
    data = {"vehicleid": vehicleid, "station_name": station_info[0][0]['Station'], "station_location": station_info[1][0]["Station's Location"]}
    print(data)
    try:
        response = requests.post(station_url, json=data)
        response.raise_for_status()
        print("Data sent successfully to station.")

    except requests.exceptions.RequestException as e:
        print(f"Error sending data to station: {e}")
    
    edge_controller_crowd_url = 'http://localhost:5002/receive_crowd_data' 
    crowdFlowSplitted = crowdflowid.split(':')
    idNumber = crowdFlowSplitted[-1]
    crowd_data = {'id': crowdflowid, 'value': max_people, 'dateObserved': datetime.datetime.now().isoformat(),
                   'station':station_info[0][0]['Station'], 'entityName': f"Bus {idNumber}"}

    try:
        response = requests.post(edge_controller_crowd_url, json=crowd_data)
        response.raise_for_status()
        print("Data sent successfully to station.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to station: {e}")

def read_locations(file_path, start_row=None, end_row=None, skip_value=None):
    try:
        use_cols = [1]
        skiprows = range(1, start_row) if start_row else None
        nrows = end_row - start_row + 1 if start_row and end_row else None

        df = pd.read_excel(file_path, usecols=use_cols, skiprows=skiprows, nrows=nrows)
        df1 = pd.read_excel(file_path, usecols=[2], skiprows=skiprows, nrows=nrows)

        if skip_value is not None:
            df = df[~df.iloc[:, 0].apply(lambda x: str(x) == str(skip_value))]
            df1 = df1[~df1.iloc[:, 0].apply(lambda x: str(x) == str(skip_value))]

        locations = df.to_dict(orient='records')
        stations = df1.to_dict(orient='records')

        if not df.empty:
            if not df1.empty:
                df2 = pd.read_excel(file_path, usecols=[3], skiprows=skiprows, nrows=nrows)
                st_loc = df2.to_dict(orient='records')
                return locations, [stations, st_loc]
            else:
                return locations, False
        else:
            if start_row + 1<123:
                #print("No valid locations found in row {}. Trying next row.".format(start_row))
                return read_locations(
                    file_path=os.path.join(subfile, "Routes.xlsx"),
                    start_row=start_row + 1,
                    end_row=end_row+1,
                    skip_value="-"
                )
            else:
                return locations, False
    except Exception as e:
        print(f"Error reading locations from Excel: {e}")
        return [], False

def process_frame(frame: np.ndarray, _) -> np.ndarray:
    global z_1, max, m
    results = model(frame, imgsz=1280, agnostic_nms = True, classes=[0])[0]
    detections = sv.Detections.from_yolov8(results)
    #detections = detections[detections.class_id == 0]
    zone.trigger(detections=detections)

    box_annotator = sv.BoxAnnotator(thickness=4, text_thickness=4, text_scale=2)
    labels = [f"{model.names[class_id]} {confidence:0.2f}" for _, confidence, class_id, _ in detections]
    frame = box_annotator.annotate(scene=frame, detections=detections, labels=labels)
    frame = zone_annotator.annotate(scene=frame)
    z = zone.trigger(detections=detections)
    if m==0:
        max=sum(z)
        m=1
    if sum(z)>max:
        max= sum(z)
    if len(z_1) == len(z):
        for i,k in enumerate(z_1):
            if z[i]==False and z_1[i]==True:
                max=max-1
            if z[i]==True and z_1[i]==False:
                max=max+1

    print("Detections", max )
    z_1= z

    additional_info_text = f"People inside: {max}"

    cv2.putText(frame, additional_info_text, (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 6, cv2.LINE_AA)

    #sv.show_frame_in_notebook(frame, (16, 16))
    return frame, max

cap = cv2.VideoCapture(SUBWAY_VIDEO_PATH)

if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

def faker(station, location):
    global max_people
    random_integer = random.randint(-30, 30)

    if max_people + random_integer>=0:
        max_people +=random_integer
    else:
        max_people=0
    send_data(location)
    send_to_station(int(max_people), station)
    print(max_people)

def start_video(station, location):
    cap = cv2.VideoCapture(SUBWAY_VIDEO_PATH)
    global processing_video, max_people
    frame_counter = 0
    send_to_station(int(max_people), station)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    while processing_video:
        ret, frame = cap.read()

        if not ret:
            print("Video has ended.")
            break

        frame_counter += 1

        if frame_counter % 20 == 0:
            processed_frame, max = process_frame(frame, None)

            cv2.imshow("Video", processed_frame)

            # Check if the user pressed 'q' to exit the loop
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        if frame_counter == 20:
            frame_counter = 0

    if max_people + max>=0:
        max_people +=max
    else:
        max_people=0

    send_to_station(int(max_people), station)
    send_data(location)

    print(max_people)

    cap.release()
    cv2.destroyAllWindows()

def start_flask_app():
    app.run(threaded=True, port=5000)

# Start the Flask app on a different thread
flask_thread = threading.Thread(target=start_flask_app)
flask_thread.start()

def update_locations():
    global row, processing_video, video_ended_event
    row = 1

    while True:
        excel_file_path = os.path.join(subfile, "Routes.xlsx")
        result = read_locations(
            file_path=excel_file_path,
            start_row=row,
            end_row=row,
            skip_value="-"
        )

        if result is not None:
            locations, station = result
            print(locations)
            send_data(locations)
            t=1
            if station:
                t=3
                print("station[0]", station[0])
                if station[0] == [{'Station': 'Ermou'}]:
                    print(station)
                    processing_video = True

                    # Start video processing thread
                    video_thread = StoppableThread(target=start_video, args=(station, locations))
                    video_thread.start()
                    video_thread.stop()
                    # Wait for the video processing thread to finish
                    video_thread.join()

                    processing_video = False
                elif station[0] == [{'Station': 'Favierou'}]:
                    faker(station, locations)
                    video_ended_event.wait()
                    video_ended_event.clear() 
                elif station[0] == [{'Station': 'Hospital'}]:
                    faker(station, locations)
                    row = 0
                else:
                    faker(station, locations)

            row += 1
        else:
            print("Error reading locations. Stopping update.")
            break
        time.sleep(t)

# Start the location update thread
locations_thread = threading.Thread(target=update_locations)
locations_thread.start()

locations_thread.join() 

# Release video capture and close all windows
cap.release()
cv2.destroyAllWindows()
