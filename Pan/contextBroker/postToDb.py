import requests
import connexion
from flask import jsonify, request
from bson import ObjectId

# FIWARE Context Broker endpoint
orion_url = "http://localhost:1026/v2/entities"

app = connexion.App(__name__, specification_dir='./')
app.add_api('swagger.yml', resolver=connexion.RestyResolver('api'))


# GET route to retrieve entities by ID
@app.route('/get_entity', methods=['GET'])
def getEntityRoute():
    entityId = request.args.get('id')
    try:
        params = {
            "id": entityId,
        }
        response = requests.get(orion_url + '/' + entityId, params=params, headers = {"Accept": "application/json",})
        
        if response.status_code == 200:
            entities = response.json()
            if entities:
                print(f"Entity: {entities}")
            else:
                print("No entities found with the specified criteria")
        else:
            print(f"Failed to retrieve entities with status code {response.status_code}: {response.text}")
        return jsonify({'message': f'Entity with ID {entityId} received', 'data': entities})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'message': 'Error occurred during get'}), 500


@app.route('/post_entity', methods=['POST'])
def postEntityRoute():
    entity_data = request.json
    try:
        # Send a POST request to the Orion Context Broker
        response = requests.post(orion_url, json=entity_data)

        if response.status_code == 201:
            return jsonify({'message': 'Entity created successfully'})
        else:
            return jsonify({'message': f'Failed to create entity. Status code: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500
    

@app.route('/update_entity', methods=['PATCH'])
def patchEntityRoute():

    entityId = str(request.args.get('entityId'))

    try:
        params = {
            "id": entityId,
        }

        response = requests.get(orion_url, params=params, headers = {"Accept": "application/json",})
        
        if response.status_code == 200:
            entities = response.json()
            if entities:
                entity_id = entities[0]["id"]
                print(f"Entity ID: {entity_id}")
            else:
                print("No entities found with the specified criteria")
        else:
            print(f"Failed to retrieve entities with status code {response.status_code}: {response.text}")

        payload = {}
        update_data = request.get_json()

        # Update the entity with the provided data
        for key, value in update_data.items():
            if isinstance(value, ObjectId):
                value = str(value)
            payload[key] = {'value': value}

        print(payload)
        # Update the entity in the MongoDB collection
        response = requests.patch(orion_url + '/' + entity_id + '/attrs', json=payload, headers={'Content-Type': 'application/json'})

        return jsonify({'message': f'Entity with ID {entityId} partially updated', 'data': payload})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'message': 'Error occurred during update'}), 500


# DELETE route to remove entities by ID
@app.route('/delete_entity', methods=['DELETE'])
def deleteEntityRoute():
    entityId = request.args.get('id')
    try:
        params = {
            "id": entityId,
        }
        response = requests.delete(orion_url + '/' +entityId, params=params, headers = {"Accept": "application/json",})
        entities = {}
        if response.status_code == 200:
            entities = response.json()
            if entities:
                print(f"Entity: {entities}")
            else:
                print("No entities found with the specified criteria")
        else:
            print(f"Failed to retrieve entities with status code {response.status_code}: {response.text}")
        return jsonify({'message': f'Entity with ID {entityId} deleted', 'data': entities})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'message': 'Error occurred during delete'}), 500


if __name__ == '__main__':
    app.run(port=5000)
