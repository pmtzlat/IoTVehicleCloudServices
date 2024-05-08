import requests
import os

def assign_route(data):
     host = os.getenv('ROUTES_MICROSERVICE_ADDRESS')
     port = os.getenv('ROUTES_MICROSERVICE_PORT')
     return requests.post('http://' + host + ':' + port +
    '/routes/assign', json=data)

def complete_route(data):
     host = os.getenv('ROUTES_MICROSERVICE_ADDRESS')
     port = os.getenv('ROUTES_MICROSERVICE_PORT')
     requests.post('http://' + host + ':' + port +
    '/routes/complete/', json=data)

