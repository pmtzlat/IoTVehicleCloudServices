import requests
import os

def register_vehicle(data):
     host = os.getenv('VEHICLES_MICROSERVICE_ADDRESS')
     port = os.getenv('VEHICLES_MICROSERVICE_PORT')
     return requests.post('http://' + host + ':' + port +
    '/vehicles/register', json=data)

def delete_vehicle(data):
     host = os.getenv('VEHICLES_MICROSERVICE_ADDRESS')
     port = os.getenv('VEHICLES_MICROSERVICE_PORT')
     requests.post('http://' + host + ':' + port +
    '/vehicles/delete', json=data)

