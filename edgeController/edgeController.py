import datetime
import json
import signal
from paho.mqtt import client as mqtt_client
from flask import Flask, request, jsonify
import copy
import aiohttp

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT broker")
        else:
            print("Failed to connect, return code %d\n", rc)
    client = mqtt_client.Client("Pannic")
    client.on_connect = on_connect
    client.connect("150.140.186.118", 1883)
    return client

client = connect_mqtt()

app = Flask(__name__)

async def get_from_endpoint(endpoint):
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint) as response:
            try:
                response.raise_for_status()
                data = await response.json()
                return data
            except aiohttp.ClientResponseError as e:
                print(f"Error fetching data from {endpoint}: {e}")
                return None
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {endpoint}: {e}")
                return None

# Function to post data to another endpoint
async def post_to_endpoint(data, endpoint):
    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, json={'data': data}) as response:
            response.raise_for_status()
    
async def handle_request(data, endpoint):
    try:
        # Edit the data (modify as per your requirements)
        # edited_data = edit_data(data)

        # Asynchronously post the edited data to another endpoint
        await post_to_endpoint(data, endpoint)

        # Respond to the original request
        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/receive_bus_data', methods=['POST'])
async def receive_bus_data():
    global client

    data = request.get_json()

    vid = data['vehicleid']
    vcords = data['locations']
    vplate = "LICENCE PLATE"
    vdatetimeObs = datetime.datetime.now().isoformat()
    vcFOid = data.get('crowdflowid') 
    vBusNumber = data.get('busnumber')

    vehicleData = {
        "id": vid,
        "type": "Vehicle",
        "category": {
            "type": "Property",
            "value": [
                "municipalServices"
            ]
        },
        "license_plate": {
            "type": "Property",
            "value": vplate
        },
        "location": {
            "type": "GeoProperty",
            "value": {
                "type": "Point",
                "coordinates": vcords
            }
        },
        "observationDateTime": {
            "type": "Property",
            "value": {
                "@type": "DateTime",
                "@value": vdatetimeObs
            }
        },
        "vehicleTrackerDevice": {
            "type": "Property",
            "value": "Installed"
        },
        "vehicleType": {
            "type": "Property",
            "value": "bus"
        },
        "description": {
            "type": "Property",
            "value": vBusNumber
        }
    }
    if vcFOid is not None:
        vehicleData["crowdFlowObserved"] = {
            "type": "CrowdFlowObserved",
            "value": vcFOid
        }

    extData = await get_from_endpoint("http://localhost:5003/entities"+'/'+str(vid))
    maxVersion = 0
    if extData is not None:
        maxVersion = int(extData['data'][0]['version'].split(' ')[1])
        for i in range(0,len(extData['data'])):
            if(int(extData['data'][i]['version'].split(' ')[1]) > maxVersion):
                maxVersion = int(extData['data'][i]['version'].split(' ')[1])
    extDataToPost = copy.deepcopy(vehicleData)
    maxVersion = maxVersion + 1
    extDataToPost['version'] = f"Version {maxVersion}"

    # Post to external DB
    await handle_request(extDataToPost, f"http://localhost:5003/entity/{vid}/version {maxVersion}")

    # Publish to MQTT broker
    client.publish(f"json/busstopmonitoring/{vid}", json.dumps(vehicleData))

    # Post to context broker
    result = await handle_request(vehicleData, "http://localhost:5004/receive_context_data")
    return result

@app.route('/receive_station_data', methods=['POST'])
async def receive_station_data():
    global client

    data = request.get_json()

    timeNow = datetime.datetime.now().isoformat()
    tSid = data['id']
    tSlocation = data['location']
    tSname = data['name']
    violationId = data['tVid']

    transportStationData= {
        "id": tSid,
        "type": "TransportStation",
        "name": {
            "type": "String",
            "value": tSname
        },
        "contractingAuthority": {
            "type": "Property",
            "value": "Municipality of Patras"
        },
        "contractingCompany": {
            "type": "Property",
            "value": "Urban Transports of Patras S.A."
        },
        "location": {
            "type": "GeoProperty",
            "value": {
                "type": "Point",
                "coordinates": tSlocation
            }
        },
        "stationType": {
            "type": "Property",
            "value": [
                "bus"
            ]
        },
        "trafficViolation": {
            "type": "TrafficViolation",
            "value": violationId
        }
    }

    cont_resp = await get_from_endpoint(f"http://150.140.186.118:1026/v2/entities/{tSid}")
    if (cont_resp is None or 'error' in cont_resp):
        transportStationData['dateObserved']= {
                "type": "DateTime",
                "value": timeNow
            }
        transportStationData['crowdFlowObserved']= {
                "type": "CrowdFlowObserved",
                "value": "FirstID"
            }
        transportStationData['dateLastReported']= {
                "type": "DateTime",
                "value": timeNow
            }
        transportStationData['vehicleLastReported']= {
                "type": "Vehicle",
                "value": "FirstID"
            }
        
    if(data['vID'] == None):
        cFOid = data['cFOID']
        tSdatetimeObserved = data['dtLastObserved']
        transportStationData['dateObserved']= {
                "type": "DateTime",
                "value": tSdatetimeObserved
            }
        transportStationData['crowdFlowObserved']= {
                "type": "CrowdFlowObserved",
                "value": cFOid
            }

    if(data['cFOID'] == None):
        vid = data['vID']
        tSdatetimeReported = data['dtLastReported']
        transportStationData['dateLastReported']= {
                "type": "DateTime",
                "value": tSdatetimeReported
            }
        transportStationData['vehicleLastReported']= {
                "type": "Vehicle",
                "value": vid
            }
    
    extData = await get_from_endpoint("http://localhost:5003/entities"+'/'+str(tSid))
    maxVersion = 0
    if extData is not None:
        maxVersion = int(extData['data'][0]['version'].split(' ')[1])
        for i in range(0,len(extData['data'])):
            if(int(extData['data'][i]['version'].split(' ')[1]) > maxVersion):
                maxVersion = int(extData['data'][i]['version'].split(' ')[1])
    extDataToPost = copy.deepcopy(transportStationData)
    maxVersion = maxVersion + 1
    extDataToPost['version'] = f"Version {maxVersion}"

    # Post to external DB
    await handle_request(extDataToPost, f"http://localhost:5003/entity/{tSid}/version {maxVersion}")

    # Publish to MQTT broker
    client.publish(f"json/busstopmonitoring/{tSid}", json.dumps(transportStationData))

    # Post to context broker
    result = await handle_request(transportStationData, "http://localhost:5004/receive_context_data")
    return result

@app.route('/receive_crowd_data', methods=['POST'])
async def receive_crowd_data():
    global client

    data = request.get_json()

    cFOid = data['id']
    cFOpc = data['value']
    cFOdatetime = data['dateObserved']
    cFOstation = data['station']
    cFOentityname = data['entityName']
    cFObool = False
    if(int(cFOpc) > 20): cFObool = True
    type_of_measuremnt = cFOid.split(':')[3]
    id_number = cFOid.split(':')[4]

    if type_of_measuremnt != "Bus":
        cFOstation = None
        
    if(cFObool == True and type_of_measuremnt == "Bus"):
        await handle_request({'notify': True, 'message': f'Bus {id_number} is congested'},
                              "http://localhost:5005/forward_notification")

    # Create payload
    crowdFlowObservedData = {
        "id": cFOid,
        "type": "CrowdFlowObserved",
        "congested": {
            "type": "Property",
            "value": cFObool
        },
        "dateObserved": {
            "type": "Property",
            "value": {
                "@type": "DateTime",
                "@value": cFOdatetime
            }
        },
        "peopleCount": {
            "type": "Property",
            "value": cFOpc
        },
        "name":{ 
            "type": "Property",
            "value": cFOstation
        },
        "alternateName":{ 
            "type": "Property",
            "value": cFOentityname
        }
    }

    extData = await get_from_endpoint("http://localhost:5003/entities"+'/'+str(cFOid))
    maxVersion = 0
    if extData is not None:
        maxVersion = int(extData['data'][0]['version'].split(' ')[1])
        for i in range(0,len(extData['data'])):
            if(int(extData['data'][i]['version'].split(' ')[1]) > maxVersion):
                maxVersion = int(extData['data'][i]['version'].split(' ')[1])
    extDataToPost = copy.deepcopy(crowdFlowObservedData)
    maxVersion = maxVersion + 1
    extDataToPost['version'] = f"Version {maxVersion}"
    await handle_request(extDataToPost, f"http://localhost:5003/entity/{cFOid}/version {maxVersion}")

    # Publish to MQTT broker
    client.publish(f"json/busstopmonitoring/{cFOid}", json.dumps(crowdFlowObservedData))

    # Post to context broker
    result = await handle_request(crowdFlowObservedData, "http://localhost:5004/receive_context_data")
    return result

@app.route('/receive_violation_data', methods=['POST'])
async def receive_violation_data():
    global client

    data = request.get_json()

    tVid = data['tvid']
    tVdatetime = data['datetime']
    tVplate = data['plate']
    tVtSname = data['stationName']
    tVcords = data['location']

    trafficViolationData = {
        "id": tVid,
        "type": "TrafficViolation",
        "observationDateTime": {
            "type": "Property",
            "value": {
                "@type": "DateTime",
                "@value": tVdatetime
            }
        },
        "description": {
            "type": "Property",
            "value": "Illegal Parking"
        },
        "vehiclePlate": {
            "type": "Property",
            "value":  tVplate
        },
        "transportStation": {
            "type": "transportStation",
            "value": tVtSname
        },
        "location": {
            "type": "GeoProperty",
            "value": {
                "type": "Point",
                "coordinates": tVcords
            }
        }
    }

    extData = await get_from_endpoint("http://localhost:5003/entities"+'/'+str(tVid))
    maxVersion = 0
    if extData is not None:
        maxVersion = int(extData['data'][0]['version'].split(' ')[1])
        for i in range(0,len(extData['data'])):
            if(int(extData['data'][i]['version'].split(' ')[1]) > maxVersion):
                maxVersion = int(extData['data'][i]['version'].split(' ')[1])
    extDataToPost = copy.deepcopy(trafficViolationData)
    maxVersion = maxVersion + 1
    extDataToPost['version'] = f"Version {maxVersion}"

    # Post to external DB
    await handle_request(extDataToPost, f"http://localhost:5003/entity/{tVid}/version {maxVersion}")

    # Publish to MQTT broker
    client.publish(f"json/busstopmonitoring/{tVid}", json.dumps(trafficViolationData))

    # Post to context broker
    result = await handle_request(trafficViolationData, "http://localhost:5004/receive_context_data")
    return result

def handle_ctrl_c(signal, frame):
    global client
    print("Received Ctrl+C. Cleaning up or executing additional commands...")
    # Add your cleanup or additional commands here
    client.disconnect()
    # For example, you might close database connections, release resources, etc.
    print("Cleanup complete. Exiting.")
    # Exit the application
    exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, handle_ctrl_c)

if __name__ == '__main__':
    # Run the Flask app on port 5002
    app.run(port=5002)