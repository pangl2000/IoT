from datetime import timedelta, timezone
import os
from flask import Flask,jsonify
import datetime as dt
from pymongo import MongoClient
import json
from bson import json_util
from flask_restful import Api, Resource, reqparse
from collections import defaultdict
import requests

app = Flask(__name__)

api=Api(app)

# MongoDB configuration
mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri)

# Select the database
db = client["externalDB"]

# Select the collection within the database
collection = db['collection_of_historical_data']

parser = reqparse.RequestParser()
parser.add_argument('data', type=dict, help='Data to be posted or patched', required=True)

class EntityResourceMultipleInstances(Resource):
    def get(self, entity_id):
        data = list(collection.find({'id': entity_id}))
        if not data:
            return None 
            #return jsonify({'message': f'Entity with ID {entity_id} not found'}), 404
        json_doc = json.loads(json_util.dumps(data))
        return jsonify({'message': f'Entity with ID {entity_id} received', 'data': json_doc})

class EntityResource(Resource):
    def get(self, entity_id, version):
        data = collection.find_one({'id': entity_id, 'version': version})
        json_doc = json.loads(json_util.dumps(data))
        if not data:
            return jsonify({'message': f'Entity with ID {entity_id} and version {version} not found'}), 404
        return jsonify({'message': f'Entity with ID {entity_id} and version {version} received', 'data': json_doc})

    def post(self, entity_id, version):
        args = parser.parse_args()
        data = args['data']

        if collection.find_one({'id': entity_id, 'version': version}):
            return jsonify({'message': f'Entity with ID {entity_id} and version {version} already exists'}), 409

        json_doc = json.loads(json_util.dumps(data))
        collection.insert_one(json_doc)
        return jsonify({'message': 'Entity posted successfully'})

    def patch(self, entity_id, version):
        args = parser.parse_args()
        update_data = args['data']

        existing_entity = collection.find_one({'id': entity_id, 'version': version})
        if not existing_entity:
            return jsonify({'message': f'Entity with ID {entity_id} and version {version} not found'}), 404

        # Update the entity with the provided data
        for key, value in update_data.items():
            if key in existing_entity:
                existing_entity[key] = value

        existing_entity.pop('id', None)
        existing_entity.pop('type', None)
        existing_entity.pop('version', None)

        # Update the entity in the MongoDB collection
        json_document = json.loads(json_util.dumps(existing_entity))
        collection.update_one({'id': entity_id, 'version': version}, {'$set': json_document})
        return jsonify({'message': f'Entity with ID {entity_id} and version {version} partially updated', 'data': existing_entity})
    
    def delete(self, entity_id, version):
        existing_entity = collection.find_one({'id': entity_id, 'version': version})
        if not existing_entity:
            return jsonify({'message': f'Entity with ID {entity_id} and version {version} not found'}), 404

        entityObjectId = existing_entity['_id']
        collection.delete_one({'_id': entityObjectId})

        existing_entity.pop('id', None)
        existing_entity.pop('version', None)
        # Delete the entity in the MongoDB collection
        json_doc = json.loads(json_util.dumps(existing_entity))
        return jsonify({'message': f'Entity with ID {entity_id} and version {version} deleted', 'data': json_doc})

# Class for returning average people count per station for specific bus
class PeopleAvgPerStationByTimeResource(Resource):
    def get(self, entityId, initYear, initMonth, initDay, initHour, initMinute, initSecond,
            endYear, endMonth, endDay, endHour, endMinute, endSecond, tz_offset):
        tz = timezone(timedelta(minutes=tz_offset))
        # Similar to your existing logic for retrieving data by time
        # ...
        # Get the MongoDB collection
        data = {}
        data2 = []
        try:
            # Bulk request for entity CrowdFlowObserved
            for existing_entity in collection.find({
                                                "dateObserved.value.@value": {
                                                    "$gte": dt.datetime(initYear, initMonth, initDay, 
                                                                        initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
                                                    "$lt": dt.datetime(endYear, endMonth, endDay, 
                                                                        endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
                                                },
                                                "id": entityId
                                                }):
                if existing_entity["name"]["value"] in data:
                    data[existing_entity["name"]["value"]].append(existing_entity)
                else: data[existing_entity["name"]["value"]] = [existing_entity]
                data2.append(existing_entity)

            dataAvg = {}

            c = 1
            for station in data:
                dataAvg[f"{c}.{station}"] = 0

                for entity in data[station]:
                    dataAvg[f"{c}.{station}"] = dataAvg[f"{c}.{station}"] + entity["peopleCount"]["value"]

                dataAvg[f"{c}.{station}"] = dataAvg[f"{c}.{station}"] / float(len(data[station]))
                
                c = c + 1
                
            if len(dataAvg) == 0:
                return jsonify({'message': f'Entity with ID {entityId} or specific DateTime values not found'}), 404
            
            return jsonify({'message': f'Entity with ID {entityId} received', 'data': json.loads(json_util.dumps(dataAvg))})
        
        except Exception as e:
            print(f"Error: {str(e)}")
            return jsonify({'message': 'Error occurred during get'}), 500
        
# Method only for CrowdFlowObserved
class EntitiesByTimeResource(Resource):
    def get(self, entityId, initYear, initMonth, initDay, initHour, initMinute, initSecond,
            endYear, endMonth, endDay, endHour, endMinute, endSecond, tz_offset):
        tz = timezone(timedelta(minutes=tz_offset))
        # Similar to your existing logic for retrieving data by time
        # ...
        # Get the MongoDB collection
        data=[]
        try:
            # Bulk request for entity CrowdFlowObserved
            for existing_entity in collection.find({
                                                "dateObserved.value.@value": {
                                                    "$gte": dt.datetime(initYear, initMonth, initDay, 
                                                                        initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
                                                    "$lt": dt.datetime(endYear, endMonth, endDay, 
                                                                        endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
                                                },
                                                "id": entityId
                                                }):
                data.append([int(existing_entity["peopleCount"]["value"]), existing_entity["dateObserved"]["value"]["@value"]])

            hourly_data = defaultdict(list)

            # Parse datetime strings, group by hour, and accumulate values
            for value, iso_datetime in data:
                dat = dt.datetime.fromisoformat(iso_datetime)
                hour_key = dat.replace(minute=0, second=0, microsecond=0)
                hourly_data[hour_key].append(value)

            # Calculate the average for each hour
            average_data = {hour: sum(values) / len(values) for hour, values in hourly_data.items()}
            
            data_to_send = {}
            for hour, average_value in average_data.items():
                data_to_send[hour.isoformat()] = average_value
        
            if len(data) == 0:
                return jsonify({'message': f'Entity with ID {entityId} or specific DateTime values not found'}), 404
            
            return jsonify({'message': f'Entity with ID {entityId} received', 'data': json.loads(json_util.dumps(data_to_send))})
        
        except Exception as e:
            print(f"Error: {str(e)}")
            return jsonify({'message': 'Error occurred during get'}), 500

# class EntitiesByTimeResource(Resource):
#     def get(self, entityId, entityType, initYear, initMonth, initDay, initHour, initMinute, initSecond,
#             endYear, endMonth, endDay, endHour, endMinute, endSecond, tz_offset):
#         tz = timezone(timedelta(minutes=tz_offset))
#         # Similar to your existing logic for retrieving data by time
#         # ...
#         # Get the MongoDB collection
#         data=[]
#         try:
#             # Bulk request for entity CrowdFlowObserved
#             if entityType == "CrowdFlowObserved":
#                 for existing_entity in collection.find({
#                                                     "dateObserved.value.@value": {
#                                                         "$gte": dt.datetime(initYear, initMonth, initDay, 
#                                                                             initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
#                                                         "$lt": dt.datetime(endYear, endMonth, endDay, 
#                                                                             endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
#                                                     },
#                                                     "id": entityId
#                                                     }):
#                     data.append(existing_entity)

#                 if len(list(collection.find({
#                                         "dateObserved.value.@value": {
#                                             "$gte": dt.datetime(initYear, initMonth, initDay, 
#                                                                 initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
#                                             "$lt": dt.datetime(endYear, endMonth, endDay, 
#                                                                 endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
#                                         },
#                                         "id": entityId
#                                         }
#                                         ))) == 0:
#                     return jsonify({'message': f'Entity with ID {entityId} or specific DateTime values not found'}), 404
            
#             # Bulk request for entity TrafficViolation
#             elif entityType == "TrafficViolation":
#                 for existing_entity in collection.find({
#                                                     "observationDateTime.value.@value": {
#                                                         "$gte": dt.datetime(initYear, initMonth, initDay, 
#                                                                             initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
#                                                         "$lt": dt.datetime(endYear, endMonth, endDay, 
#                                                                             endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
#                                                     },
#                                                     "id": entityId
#                                                     }):
#                     data.append(existing_entity)
                
#                 if len(list(collection.find({
#                                         "observationDateTime.value.@value": {
#                                             "$gte": dt.datetime(initYear, initMonth, initDay, 
#                                                                 initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
#                                             "$lt": dt.datetime(endYear, endMonth, endDay, 
#                                                                 endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
#                                         },
#                                         "id": entityId
#                                         }
#                                         ))) == 0:
#                     return jsonify({'message': f'Entity with ID {entityId} or specific DateTime values not found'}), 404
            
#             # Bulk request for entity TransportStation
#             elif entityType == "TransportStation":
#                 # Search by dateLastReported
#                 for existing_entity in collection.find({
#                                                     "dateLastReported.value": {
#                                                         "$gte": dt.datetime(initYear, initMonth, initDay, 
#                                                                             initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
#                                                         "$lt": dt.datetime(endYear, endMonth, endDay, 
#                                                                             endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
#                                                     },
#                                                     "id": entityId
#                                                     }):
#                     data.append(existing_entity)
                
#                 # Search by dateObserved
#                 for existing_entity2 in collection.find({
#                                                     "dateObserved.value": {
#                                                         "$gte": dt.datetime(initYear, initMonth, initDay, 
#                                                                             initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
#                                                         "$lt": dt.datetime(endYear, endMonth, endDay, 
#                                                                             endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
#                                                     },
#                                                     "id": entityId
#                                                     }):
#                     data.append(existing_entity2)

#                 if (len(list(collection.find({
#                                         "dateLastReported.value": {
#                                             "$gte": dt.datetime(initYear, initMonth, initDay, 
#                                                                 initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
#                                             "$lt": dt.datetime(endYear, endMonth, endDay, 
#                                                                 endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
#                                         },
#                                         "id": entityId
#                                         }
#                                         ))) == 0) and (len(list(collection.find({
#                                         "dateObserved.value": {
#                                             "$gte": dt.datetime(initYear, initMonth, initDay, 
#                                                                 initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
#                                             "$lt": dt.datetime(endYear, endMonth, endDay, 
#                                                                 endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
#                                         },
#                                         "id": entityId
#                                         }
#                                         )))) == 0:
#                     return jsonify({'message': f'Entity with ID {entityId} or specific DateTime values not found'}), 404
            
#             # Bulk request for entity Vehicle
#             elif entityType == "Vehicle":
#                 for existing_entity in collection.find({
#                                                     "observationDateTime.value.@value": {
#                                                         "$gte": dt.datetime(initYear, initMonth, initDay, 
#                                                                             initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
#                                                         "$lt": dt.datetime(endYear, endMonth, endDay, 
#                                                                             endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
#                                                     },
#                                                     "id": entityId
#                                                     }):
#                     data.append(existing_entity)

#                 if len(list(collection.find({
#                                         "observationDateTime.value.@value": {
#                                             "$gte": dt.datetime(initYear, initMonth, initDay, 
#                                                                 initHour, initMinute, initSecond,0,tzinfo=tz).isoformat(),
#                                             "$lt": dt.datetime(endYear, endMonth, endDay, 
#                                                                 endHour, endMinute, endSecond,0,tzinfo=tz).isoformat()
#                                         },
#                                         "id": entityId
#                                         }
#                                         ))) == 0:
#                     return jsonify({'message': f'Entity with ID {entityId} or specific DateTime values not found'}), 404
                
#             else: 
#                 return jsonify({'message': 'Error: Wrong type'}), 400
#             return jsonify({'message': f'Entity with ID {entityId} received', 'data': json.loads(json_util.dumps(data))})
        
#         except Exception as e:
#             print(f"Error: {str(e)}")
#             return jsonify({'message': 'Error occurred during get'}), 500


api.add_resource(EntityResource, '/entity/<string:entity_id>/<string:version>')
api.add_resource(PeopleAvgPerStationByTimeResource, '/avg_people_by_time/<string:entityId>/<int:initYear>/<int:initMonth>/<int:initDay>/<int:initHour>/<int:initMinute>/<int:initSecond>/<int:endYear>/<int:endMonth>/<int:endDay>/<int:endHour>/<int:endMinute>/<int:endSecond>/<int:tz_offset>')
api.add_resource(EntitiesByTimeResource, '/entities_by_time/<string:entityId>/<int:initYear>/<int:initMonth>/<int:initDay>/<int:initHour>/<int:initMinute>/<int:initSecond>/<int:endYear>/<int:endMonth>/<int:endDay>/<int:endHour>/<int:endMinute>/<int:endSecond>/<int:tz_offset>')
api.add_resource(EntityResourceMultipleInstances, '/entities/<string:entity_id>')
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5003)

    