import json
import os
import random
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import paho.mqtt.client as mqtt
from telemetry_register_interface import register_telemetry
from vehicle_api_operations_interface import register_vehicle, delete_vehicle
from routes_api_operations_interface import assign_route, complete_route
import logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
CORS(app)

global connected_vehicles, available_plates, STATE_TOPIC, PLATE_REQUEST_TOPIC, pois
global CLIENT_NOTIFICATIONS_TOPIC, ROUTE_ASSIGNMENT_TOPIC, client


# connected_vehicles tiene que guardar vehiculos de esta forma:
# connected_vehicles = {'<id>': {'Plate': '0000BBB', 'Route': {'Origin': 'Getafe', 'Destination': 'Mostoles'} } }
# o de esta:
# connected_vehicles = [ {'id': 'foo', 'Plate': '0000BBB', 'Route': {'Origin': 'Getafe', 'Destination': 'Mostoles'} }
# (prefiero la primera)
# si un coche no tiene ruta asignada, no tiene la key 'Route'

@app.route('/routes/send', methods=['POST'])
def send_route():
    params = request.get_json()
    plate = params.get("plate")
    origin = params.get("origin")
    destination = params.get("destination")

    if not (plate and origin and destination):
        return jsonify({"error": "Missing parameters"}), 400

    route = {"Origin": origin, "Destination": destination, "plate": plate}
    assign_result = assign_route(route)
    if assign_result.json().get('result') == "Vehicle busy":
        app.logger.info("Error assigning route")
        return jsonify({"Result": "Vehicle busy"}), 202
    elif assign_result.json().get('result') != "Route assigned":
        app.logger.info("Error assigning route")
        return jsonify({"Result": "Route could not be sent"}), 500

    route = {"Origin": origin, "Destination": destination}
    ROUTE_ASSIGNMENT_TOPIC = f"/fic/vehicles/{plate}/route_assignment"
    client.publish(ROUTE_ASSIGNMENT_TOPIC, payload=json.dumps(route), qos=1, retain=False)

    return jsonify({"Result": "Route successfully sent"}), 201


def on_connect(client, userdata, flags, rc):
    global STATE_TOPIC, PLATE_REQUEST_TOPIC, CLIENT_NOTIFICATIONS_TOPIC, ROUTE_ASSIGNMENT_TOPIC
    if rc == 0:
        print("Connected to MQTT Broker!")
        STATE_TOPIC = "/fic/vehicles/+/car_state"
        client.subscribe(STATE_TOPIC)
        print("Subscribed to ", STATE_TOPIC)
        PLATE_REQUEST_TOPIC = "/fic/vehicles/+/plate_request"
        client.subscribe(PLATE_REQUEST_TOPIC)
        print("Subscribed to ", PLATE_REQUEST_TOPIC)
        CLIENT_NOTIFICATIONS_TOPIC = "/fic/vehicles/+/client_notifications"
        client.subscribe(CLIENT_NOTIFICATIONS_TOPIC)
        print("Subscribed to ", CLIENT_NOTIFICATIONS_TOPIC)

    else:
        print("Connection failed with result code ", rc)


def on_message(client, userdata, msg):
    global index_vehicle, connected_vehicles, available_plates

    topic = msg.topic.split('/')
    print(f'Message received: {topic[-1]}')

    if topic[-1] == "plate_request":
        input_data = msg.payload.decode()
        input_data = json.loads(input_data)
        request_data = {"vehicle_id": input_data["vehicle_id"]}
        vehicle_id = input_data["vehicle_id"]
        print(f'Vehicle {request_data} has requested a plate.')  # this line is printed

        response = register_vehicle(request_data)
        vehicle_plate = json.loads(response.text)['Plate']

        if vehicle_plate is None:
            print('No plate available')
            return

        print(vehicle_plate)
        plate_json = '{"Plate": "' + vehicle_plate + '"}'
        print(f'Publishing plate {vehicle_plate} to topic /fic/vehicles/{vehicle_id}/plate_assignment'
              f'\nConnected vehicles: {connected_vehicles}')
        client.publish("/fic/vehicles/" + vehicle_id + "/plate_assignment", payload=plate_json, qos=1,
                       retain=False)



    elif topic[-1] == "car_state":
        str_received_telemetry = msg.payload.decode()
        telemetry = json.loads(str_received_telemetry)
        print(telemetry)
        register_telemetry(telemetry)

    # caso en el que el coche envia el mensaje de que ha completado la ruta - el topic se llamará 'client_notifications'
    elif topic[-1] == "client_notifications":
        print('Received client notification!')
        route_completion_info = json.loads(msg.payload.decode())

        # my payload format: {"ID": "foo", "Plate": "1234BBC", "Event": "Route Completed", "Timestamp": 1703593978}

        vehicle_id = route_completion_info["vehicle_id"]
        plate = route_completion_info['Plate']
        event = route_completion_info['Event']
        timestamp = route_completion_info['time_stamp']

        if event == "Vehicle Disconnected":
            if deleteVehicle(vehicle_id, plate):
                print(f'Vehicle {vehicle_id} has disconnected and been deleted successfully.')

        # elimino la ruta del vehiculo
        if event == "Route Completed":
            if completeRoute(plate):
                print(f'Vehicle {plate} has completed its route.')
            # en la bdd no elimino la matrícula de la ruta para tener un historial de las rutas completadas


def deleteVehicle(vehicle_id, plate):
    request_data = {"vehicle_id": vehicle_id, "plate": plate}
    return delete_vehicle(request_data)


def completeRoute(plate):
    request_data = {"vehicle_plate": plate}
    return complete_route(request_data)


def mqtt_listener():
    global client
    client = mqtt.Client()
    client.username_pw_set(username="fic_server", password="fic_password")
    client.on_connect = on_connect
    client.on_message = on_message
    MQTT_SERVER = os.getenv("MQTT_SERVER_ADDRESS")
    MQTT_PORT = int(os.getenv("MQTT_SERVER_PORT"))
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    client.loop_forever()


if __name__ == '__main__':
    global client
    # MQTT_SERVER = os.getenv("MQTT_SERVER_ADDRESS")
    # MQTT_PORT = int(os.getenv("MQTT_SERVER_PORT"))
    # schedule_route_assignment()
    HOST = os.getenv('HOST')
    PORT = os.getenv('PORT')
    mqtt_thread = threading.Thread(target=mqtt_listener, daemon=True)
    mqtt_thread.start()

    app.run(host=HOST, port=PORT, debug=True)
    print('message_router running indefinitely')

'''def schedule_route_assignment():
    global client
    unrouted_vehicle_id = getVehicleIDWithNoRoute()
    if unrouted_vehicle_id is not None:
        new_route = generate_route()
        ROUTE_ASSIGNMENT_TOPIC = f"/fic/vehicles/{unrouted_vehicle_id}/route_assignment"
        client.publish(ROUTE_ASSIGNMENT_TOPIC, payload=json.dumps(new_route), qos=1, retain=False)
        print(f"Published new route assignment to {unrouted_vehicle_id}")
        connected_vehicles[unrouted_vehicle_id]['Route'] = new_route

    threading.Timer(60.0, schedule_route_assignment).start()'''

'''def getVehicleIDWithNoRoute():
    no_route_vehicles = [vehicle_id for vehicle_id, vehicle_info in connected_vehicles.items() if
                         'Route' not in vehicle_info]
    if no_route_vehicles:
        return random.choice(no_route_vehicles)
    else:
        return None'''

'''def generate_route():  # returns None if none are found
    origin = random.choice(pois)
    destination = random.choice(pois)
    while origin == destination:
        destination = random.choice(pois)
    return {'Origin': origin, 'Destination': destination}'''

# index_vehicle = 0
'''pois = ["Ayuntamiento de Leganes", "Ayuntamiento de Getafe",
        "Ayuntamiento de Alcorcón", "Ayuntamiento de Móstoles",
        "Universidad Carlos III de Madrid - Campus de Leganés",
        "Universidad Carlos III de Madrid - Campus de Getafe",
        "Universidad Carlos III de Madrid - Campus de Puerta de Toledo",
        "Universidad Carlos III de Madrid - Campus de Colmenarejo",
        "Ayuntamiento de Navalcarnero", "Ayuntamiento de Arroyomolinos",
        "Ayuntamiento de Carranque", "Ayuntamiento de Alcalá de Henares",
        "Ayuntamiento de Guadarrama", "Ayuntamiento de la Cabrera",
        "Ayuntamiento de Aranjuez"]'''
