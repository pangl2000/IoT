import os
import random
import aiohttp
import asyncio
import itertools
from flask import Flask, jsonify, request
import schedule
import time
import datetime
import cv2

from ultralytics import YOLO
import supervision as sv
import numpy as np
import warnings
import torch
warnings.simplefilter(action='ignore', category=FutureWarning)

ZONE_POLYGON = np.array([
    [0, 0],
    [1, 0],
    [1, 1],
    [0, 1]
])

app = Flask(__name__)

# Shared variable to store the dynamic data
shared_dynamic_data = {'name': None}

# Current folder
current_script_directory = os.path.dirname(os.path.realpath(__file__))

# Navigate to the parent folder
parent_folder = os.path.abspath(os.path.join(current_script_directory, os.pardir))
parent_of_parent = os.path.abspath(os.path.join(parent_folder, os.pardir))

# Specify the file name you want to access in the parent folder
file_in_parent_folder = os.path.join(parent_of_parent, 'GitRepo_LargeFiles')
subfilePan = os.path.join(file_in_parent_folder, 'Pan')
subfile = os.path.join(subfilePan, 'Fakers')

pause_flag_0 = False
pause_flag_5 = False
violationTracked = False
crowdFlowObservedIDs = []
transportStationIDs = []
for i in range(1,33):
    crowdFlowObservedIDs.append("urn:ngsild:CrowdFlowObserved:Station:"+str(i))
    transportStationIDs.append("urn:ngsild:TransportStation:Station:"+str(i))

transportStationNames = ["Ermou",
                        "Agiou Nikolaou",
                        "Zaimi",
                        "Old Arsakeio",
                        "Pyrosvestiou Square",
                        "Favierou",
                        "Maratou",
                        "Kourtesi",
                        "Fillppa",
                        "1st Cemetery",
                        "Anthoupoli",
                        "OGA",
                        "Aretha to University",
                        "Aretha",
                        "Intracom",
                        "Kotroni",
                        "Mihaniki Kalliergeia",
                        "Mihaniki Kalliergeia 2",
                        "Koridalleos",
                        "Psistaria",
                        "Bissarionos",
                        "Proastio",
                        "Mandreka",
                        "Tofalos Stadium",
                        "Haradros River",
                        "University of Patras Chancellors Office",
                        "Polytechnio",
                        "Conference Center",
                        "Physics Department",
                        "Geology Department",
                        "Medicine",
                        "Hospital"]

tSlocations = [ [38.24674692664068, 21.73598679633868],
                [38.24758985475257, 21.737535367031022],
                [38.24902222935668, 21.739305624967397],
                [38.250230270712024, 21.740810116383948],
                [38.25168834237874, 21.74273898930706],
                [38.25303006552498, 21.744066682766164],
                [38.2552359603907, 21.74591878456181],
                [38.257312205684094, 21.74801002744799],
                [38.25880554830628, 21.75061789742214],
                [38.260978875703046, 21.752348744111824],
                [38.261362722360786, 21.753829900052864],
                [38.26467030130779, 21.754750337049213],
                [38.266083069968, 21.756725673266818],
                [38.2669037276182, 21.75758606932094],
                [38.26946462223079, 21.758252269487343],
                [38.2709601921641, 21.75870100955657],
                [38.27312923195606, 21.760069226877345],
                [38.274935564361776, 21.762233737852593],
                [38.2769257058954, 21.764604917853518],
                [38.27785469703166, 21.76559210109097],
                [38.27909220240962, 21.76707233421115],
                [38.28046811582278, 21.768750287981504],
                [38.28217119203374, 21.771219124397756],
                [38.28438597032206, 21.772710045166257],
                [38.286147677506634, 21.774788784038343],
                [38.286200499007656, 21.78605393759909],
                [38.287957277337824, 21.786551680608497],
                [38.289797915897964, 21.78494487258972],
                [38.29171454261186, 21.786995974703636],
                [38.29367831146375, 21.790510240924757],
                [38.294454365685155, 21.791879869420182],
                [38.29649522541104, 21.795133184452613]]

# Iterator for cycling through the values
#values_iterator = itertools.cycle(['5', '20', '15'])
random_values = [0, 2, 5, 8, 11, 15, 19, 23]

# Define the endpoint to receive data
@app.route('/receive_data', methods=['POST'])
async def receive_data():
    global transportStationNames
    global transportStationIDs
    global pause_flag_0
    global pause_flag_5
    global violationTracked
    try:
        # Get the data from the POST request
        data = request.get_json()
        if(data['station_name'] == transportStationNames[0]):
            # Set the pause flag based on the received data
            pause_flag_0 = True
        else:
            pause_flag_0 = False

        if(data['station_name']  == transportStationNames[5]):
            pause_flag_5 = True
        else:
            pause_flag_5 = False

        if(data['station_name'] == transportStationNames[12]):
            await post_to_edge_controller({'tvid': "urn:ngsild:TrafficViolation:IllegalParking:1",
                                            'datetime': datetime.datetime.now().isoformat(),
                                            'plate': "_",
                                            'stationName': "Intracom",
                                            'location': tSlocations[14]},
                                            "http://localhost:5002/receive_violation_data")
            await post_to_edge_controller({'id': transportStationIDs[14],
                                            'vID': None,
                                            "dtLastReported": None,
                                            'cFOID': crowdFlowObservedIDs[14],
                                            "dtLastObserved": datetime.datetime.now().isoformat(),
                                            'location': tSlocations[14],
                                            'name': transportStationNames[14],
                                            'tVid': "_"},"http://localhost:5002/receive_station_data")
            
        index = transportStationNames.index(data['station_name'])
        # Set the shared dynamic data based on received data
        set_shared_dynamic_data(data)

        tVid = "_"
        if index == 14 and violationTracked == True:
            tVid = "urn:ngsild:TrafficViolation:IllegalParking:1"
        # Identify transportStationID with the vehicleID received and post
        dataToPost = {'id': transportStationIDs[index], 
                      'vID': data['vehicleid'],
                      "dtLastReported": datetime.datetime.now().isoformat(), 
                      'cFOID': None, 
                      "dtLastObserved":  None, 
                      'location': tSlocations[index], 
                      'name': data['station_name'],
                      'tVid': tVid}
        # Post the received data to the edge controller
        await post_to_edge_controller(dataToPost, 'http://localhost:5002/receive_station_data')

        print(dataToPost)
        # Respond to the original request
        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Function to set the shared dynamic data based on received data
def set_shared_dynamic_data(data):
    # Example: Set the 'value' key from received data to the shared variable
    global shared_dynamic_data
    shared_dynamic_data = {'name': data['station_name']}

# Function to post data to the edge controller
async def post_to_edge_controller(data, url):
    edge_controller_url = url  # Adjust the URL as needed
    async with aiohttp.ClientSession() as session:
        async with session.post(edge_controller_url, json=data) as response:
            response.raise_for_status()

# Function to post data to a different endpoint every 5 seconds
async def post_periodically_async():
    # Use the shared dynamic data
    global random_values
    global crowdFlowObservedIDs
    global transportStationIDs
    global transportStationNames
    global tSlocations
    global pause_flag_0
    global pause_flag_5
    global violationTracked

    edge_controller_url = 'http://localhost:5002/receive_crowd_data'  # Adjust the URL as needed
    second_endpoint_url = 'http://localhost:5002/receive_station_data'

    #dynamic_value = next(values_iterator)

    async with aiohttp.ClientSession() as session:
        tasks = []

        for j in range(0, 32):
            if (j == 0) and pause_flag_0:
                tasks.append(run_when_paused(session))
                continue  # Skip the rest of the loop for j = 5 if paused

            if (j == 5) and pause_flag_5:
                tasks.append(run_when_paused(session))
                continue  # Skip the rest of the loop for j = 5 if paused

            # Get the next value from the cycle
            dynamic_data = {'id': crowdFlowObservedIDs[j], 'value': random.choice(random_values),
                            'dateObserved': datetime.datetime.now().isoformat(), 'station': None, 
                            'entityName': transportStationNames[j]}

            # Add the task to the list
            tasks.append(post_async(session, edge_controller_url, dynamic_data))

            tVid = "_"    
            if j == 14 and violationTracked == True : tVid = "urn:ngsild:TrafficViolation:IllegalParking:1"
            
            # (+) add for loop for all transportStationIDs (and cFOIDs)
            tasks.append(post_async(session, second_endpoint_url, {'id': transportStationIDs[j],
                                                                   'vID': None,
                                                                   "dtLastReported": None,
                                                                   'cFOID': crowdFlowObservedIDs[j],
                                                                   "dtLastObserved": datetime.datetime.now().isoformat(),
                                                                   'location': tSlocations[j],
                                                                   'name': transportStationNames[j],
                                                                   'tVid': tVid}))

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

# Function to perform an asynchronous POST request
async def post_async(session, url, data):
    async with session.post(url, json=data) as response:
        response.raise_for_status()

async def run_when_paused(session):
    global shared_dynamic_data
    global transportStationNames
    global pause_flag_5
    global violationTracked

    edge_controller_url = 'http://localhost:5002/receive_crowd_data'  # Adjust the URL as needed
    second_endpoint_url = 'http://localhost:5002/receive_station_data'

    stationName = shared_dynamic_data['name']

    if(stationName == transportStationNames[0]):
        await post_async(session, edge_controller_url, {'id': crowdFlowObservedIDs[0], 'value': 10,
                                                'dateObserved': datetime.datetime.now().isoformat(), 'station': None,
                                                'entityName': transportStationNames[0]})
        await post_async(session, second_endpoint_url, {'id': transportStationIDs[0],
                                                                'vID': None,
                                                                "dtLastReported": None,
                                                                'cFOID': crowdFlowObservedIDs[0],
                                                                "dtLastObserved": datetime.datetime.now().isoformat(),
                                                                'location': tSlocations[0],
                                                                'name': transportStationNames[0],
                                                                'tVid': "_"})
        
    if(stationName == transportStationNames[5]):
        frame_width = 852
        frame_height = 480

        #cap = cv2.VideoCapture(0)
        VIDEO_PATH =  os.path.join(subfile, "prytan.mp4")
        #YOLO_PATH = os.path.join(subfile, "crowdhuman_yolo5m.pt")
        YOLO_PATH = os.path.join(subfile, "yolov8l.pt")

        cap = cv2.VideoCapture(VIDEO_PATH)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

        if not cap.isOpened():
            print("Error: Could not open video.")

        model1 = YOLO(YOLO_PATH)
        #model = torch.hub.load('ultralytics/yolov5', 'custom', path=YOLO_PATH)

        box_annotator = sv.BoxAnnotator(
            thickness=1,
            text_thickness=1,
            text_scale=0.5,
            text_padding=1
        )

        zone_polygon = (ZONE_POLYGON * np.array([round((4/5)*frame_width), frame_height])).astype(int)
        zone = sv.PolygonZone(polygon=zone_polygon, frame_resolution_wh=tuple([frame_width, frame_height]))
        zone_annotator = sv.PolygonZoneAnnotator(
            zone=zone, 
            color=sv.Color.red(),
            thickness=1,
            text_thickness=2,
            text_scale=1
        )

        frame_counter = 0
        bus_detection = False

        while True:
            ret, frame = cap.read()

            if not ret:
                print("Video has ended.")
                break

            if(frame_counter % 300 == 0):  # Process every 300 frames
                # # Yolo 5
                # result = model(frame)
                # detections = sv.Detections.from_yolov5(result)
                # labels = [
                #     f"{model.model.names[class_id]} {confidence:0.2f}"
                #     for _, confidence, class_id, _
                #     in detections
                # ]
                # detections_0 = detections[detections.class_id == 0]
                # frame = box_annotator.annotate(
                #     scene=frame,
                #     detections=detections_0,
                #     labels=labels
                # )

                # Yolo 8
                result1 = model1(frame, agnostic_nms = True, classes=[0])[0]
                detections1 = sv.Detections.from_yolov8(result1)    
                labels1 = [
                    f"{model1.model.names[class_id1]} {confidence1:0.2f}"
                    for _, confidence1, class_id1, _
                    in detections1
                ]
                frame = box_annotator.annotate(
                    scene=frame, 
                    detections=detections1,
                    labels=labels1
                )

                # # Bus detection
                # result1 = model1(frame, agnostic_nms = True, classes=[5])[0]
                # detections1 = sv.Detections.from_yolov8(result1)    
                # labels1 = [
                #     f"{model1.model.names[class_id1]} {confidence1:0.2f}"
                #     for _, confidence1, class_id1, _
                #     in detections1
                # ]
                # frame = box_annotator.annotate(
                #     scene=frame, 
                #     detections=detections1,
                #     labels=labels1
                # )
                # if(len(detections1)!=0): bus_detection = True
                # else: bus_detection = False
                
                await post_async(session, edge_controller_url, {'id': crowdFlowObservedIDs[5], 'value': len(detections1),
                                                                'dateObserved': datetime.datetime.now().isoformat(),
                                                                'station': None,
                                                                'entityName': transportStationNames[5]})
                zone.trigger(detections=detections1)
                frame = zone_annotator.annotate(scene=frame)
                await post_async(session, second_endpoint_url, {'id': transportStationIDs[5],
                                                                'vID': None,
                                                                "dtLastReported": None,
                                                                'cFOID': crowdFlowObservedIDs[5],
                                                                "dtLastObserved": datetime.datetime.now().isoformat(),
                                                                'location': tSlocations[5],
                                                                'name': transportStationNames[5],
                                                                'tVid': "_"})
            
            cv2.imshow("yolov8", frame)

            if (cv2.waitKey(1) == ord('q')):
                break

            frame_counter += 1
        
        pause_flag_5 = False
        await post_async(session, "http://localhost:5000/video_ended", {'favierou_vid': 1})
        await post_async(session, "http://localhost:5002/receive_violation_data", {
                                                                                'tvid': "urn:ngsild:TrafficViolation:IllegalParking:1",
                                                                                'datetime': datetime.datetime.now().isoformat(),
                                                                                'plate': "AXR1056",
                                                                                'stationName': "Intracom",
                                                                                'location': tSlocations[14]})
        await post_async(session, second_endpoint_url, {'id': transportStationIDs[14],
                                                        'vID': None,
                                                        "dtLastReported": None,
                                                        'cFOID': crowdFlowObservedIDs[14],
                                                        "dtLastObserved": datetime.datetime.now().isoformat(),
                                                        'location': tSlocations[14],
                                                        'name': transportStationNames[14],
                                                        'tVid': "urn:ngsild:TrafficViolation:IllegalParking:1"})
        violationTracked = True
        
        cap.release()
        cv2.destroyAllWindows()

# Schedule the periodic job
schedule.every(5).seconds.do(lambda: asyncio.run(post_periodically_async()))

# Function to run the scheduled jobs
def run_scheduled_jobs():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    # Run the Flask app on port 5001 in a separate thread
    from threading import Thread
    Thread(target=app.run, kwargs={'port': 5001}).start()

    # Run the scheduled jobs in the main thread
    run_scheduled_jobs()
