import json
from bson import ObjectId
from flask import Flask, request, jsonify
import requests

#orion_url = "http://localhost:1026/v2/entities"
orion_url = "http://150.140.186.118:1026/v2/entities"
entitiesFirstTime = {}

app = Flask(__name__)

@app.route('/receive_context_data', methods=['POST'])
def receive_context_data():
    global entitiesFirstTime
    try:
        dataReceived = request.get_json()
        data = dataReceived['data']
        if(data['id'] not in entitiesFirstTime):
            postEntityRoute(data)
            entitiesFirstTime[data['id']] = 1 
            return jsonify({'status': 'success', 'message': 'Entity posted'})
        else:
            patchEntityRoute(data['id'],data)
            return jsonify({'status': 'success', 'message': 'Entity patched'})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"status": "error"})

def handle_response(response, success_status_code=200):
    """Handle response from requests and check for errors."""
    if response.status_code == success_status_code:
        return response.json()
    else:
        print(f"Request failed with status code {response.status_code}: {response.text}")
        response.raise_for_status()

# GET route to retrieve entities by ID
def getEntityRoute(entityId):
    try:
        with app.app_context():
            params = {"id": entityId}
            response = requests.get(orion_url + '/' + entityId, params=params, headers={"Accept": "application/json"})

            entities = handle_response(response)

            if entities:
                print(f"Entity: {entities}")
                return jsonify({'message': f'Entity with ID {entityId} received', 'data': entities})
            else:
                print("No entities found with the specified criteria")
                return jsonify({'message': f'No entities found with ID {entityId}'}), 404

    except requests.RequestException as e:
        print(f"Request failed: {str(e)}")
        return jsonify({'message': 'Error occurred during get'}), 500


def postEntityRoute(entityData):
    try:
        with app.app_context():
            # Send a POST request to the Orion Context Broker
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            response = requests.post(orion_url, headers=headers, data=json.dumps(entityData))

            if response.status_code == 201:
                return jsonify({'message': 'Entity created successfully'})
            else:
                return jsonify({'message': f'Failed to create entity. Status code: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500
    

def patchEntityRoute(entityId, updateData):
    try:
        with app.app_context():
           
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            updateData.pop('id')
            updateData.pop('type')
            payload = {}
            # Update the entity with the provided data
            for key, value in updateData.items():
                if isinstance(value, ObjectId):
                    value = str(value)
                payload[key] = {'value': value}

            # Update the entity in the MongoDB collection
            response = requests.patch(orion_url+'/'+entityId+'/attrs', headers=headers, data=json.dumps(payload))

            return jsonify({'message': f'Entity with ID {entityId} partially updated', 'data': payload})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'message': 'Error occurred during update'}), 500


# DELETE route to remove entities by ID
def deleteEntityRoute(entityId):
    try:
        with app.app_context():
            params = {"id": entityId}
            response = requests.delete(orion_url + '/' +entityId, params=params, headers = {"Accept": "application/json",})
            entities = handle_response(response)

            if entities:
                print(f"Entity: {entities}")
                return jsonify({'message': f'Entity with ID {entityId} received', 'data': entities})
            else:
                print("No entities found with the specified criteria")
                return jsonify({'message': f'No entities found with ID {entityId}'}), 404

    except requests.RequestException as e:
        print(f"Request failed: {str(e)}")
        return jsonify({'message': 'Error occurred during get'}), 500

if __name__ == '__main__':
    # Run the Flask app on port 5004
    app.run(port=5004)