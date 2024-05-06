import json
import os
import random
import threading
import time
from telemetry_register_interface import register_telemetry
from vehicle_register_interface import register_vehicle

import paho.mqtt.client as mqtt

global index_vehicle, connected_vehicles, available_plates, STATE_TOPIC, PLATE_REQUEST_TOPIC, pois
global CLIENT_NOTIFICATIONS_TOPIC, ROUTE_ASSIGNMENT_TOPIC, client

connected_vehicles = {}
# connected_vehicles tiene que guardar vehiculos de esta forma:
# connected_vehicles = {'<id>': {'Plate': '0000BBB', 'Route': {'Origin': 'Getafe', 'Destination': 'Mostoles'} } }
# o de esta:
# connected_vehicles = [ {'id': 'foo', 'Plate': '0000BBB', 'Route': {'Origin': 'Getafe', 'Destination': 'Mostoles'} }
# (prefiero la primera)
# si un coche no tiene ruta asignada, no tiene la key 'Route'

available_plates = ["0001BBB", "0002BBB", "0003BBB", "0004BBB", "0005BBB", "0006BBB", "0007BBB", "0008BBB", "0009BBB",
                    "0010BBB"]
index_vehicle = 0
pois = ["Ayuntamiento de Leganes", "Ayuntamiento de Getafe",
        "Ayuntamiento de Alcorcón", "Ayuntamiento de Móstoles",
        "Universidad Carlos III de Madrid - Campus de Leganés",
        "Universidad Carlos III de Madrid - Campus de Getafe",
        "Universidad Carlos III de Madrid - Campus de Puerta de Toledo",
        "Universidad Carlos III de Madrid - Campus de Colmenarejo",
        "Ayuntamiento de Navalcarnero", "Ayuntamiento de Arroyomolinos",
        "Ayuntamiento de Carranque", "Ayuntamiento de Alcalá de Henares",
        "Ayuntamiento de Guadarrama", "Ayuntamiento de la Cabrera",
        "Ayuntamiento de Aranjuez"]


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


def schedule_route_assignment():
    global client
    unrouted_vehicle_id = getVehicleIDWithNoRoute()
    if unrouted_vehicle_id is not None:
        new_route = generate_route()
        ROUTE_ASSIGNMENT_TOPIC = f"/fic/vehicles/{unrouted_vehicle_id}/route_assignment"
        client.publish(ROUTE_ASSIGNMENT_TOPIC, payload=json.dumps(new_route), qos=1, retain=False)
        print(f"Published new route assignment to {unrouted_vehicle_id}")
        connected_vehicles[unrouted_vehicle_id]['Route'] = new_route

    threading.Timer(60.0, schedule_route_assignment).start()


def getVehicleIDWithNoRoute():
    no_route_vehicles = [vehicle_id for vehicle_id, vehicle_info in connected_vehicles.items() if
                         'Route' not in vehicle_info]
    if no_route_vehicles:
        return random.choice(no_route_vehicles)
    else:
        return None


def generate_route():  # returns None if none are found
    origin = random.choice(pois)
    destination = random.choice(pois)
    while origin == destination:
        destination = random.choice(pois)
    return {'Origin': origin, 'Destination': destination}


def on_message(client, userdata, msg):
    global index_vehicle, connected_vehicles, available_plates

    topic = msg.topic.split('/')
    print(f'Message received: {topic[-1]}')

    # try:

    if topic[-1] == "plate_request":
        input_data = msg.payload.decode()
        input_data = json.loads(input_data)
        request_data = {"vehicle_id": input_data["vehicle_id"]}
        vehicle_id = input_data["vehicle_id"]
        print(f'Vehicle {request_data} has requested a plate.')  # this line is printed
        if request_data["vehicle_id"] in connected_vehicles:
            response = register_vehicle(request_data)
            vehicle_plate = json.loads(response.text)['Plate']

            if vehicle_plate is None:
                print('No plate available')
                return

            plate_json = {"Plate": vehicle_plate}
            plate_json = json.dumps(plate_json)
            print(plate_json)
            client.publish("/fic/vehicles/" + vehicle_id + "/plate_assignment", payload=plate_json, qos=1,
                           retain=False)
            # Te dejo este otro que es el tuyo porque no se de donde salio el config del enunciado
            # client.publish("/fic/vehicles/" + requested_id + "/plate_assignment", payload=plate_json, qos=1, retain=False)
            print(
                f'Vehicle {vehicle_id} already has plate. Sending plate {connected_vehicles[vehicle_id]} to topic /fic/vehicles/{vehicle_id}/plates\n')

        elif len(connected_vehicles) < 10:
            # Creo que esto ya no haria falta
            """vehicle_plate = available_plates[index_vehicle]
            connected_vehicles[requested_id] = {
                'Plate': vehicle_plate}  # inicialmente no hay ruta asignada para el coche
            index_vehicle += 1"""

            response = register_vehicle(request_data)
            vehicle_plate = json.loads(response.text)['Plate']

            if vehicle_plate is None:
                print('No plate available')
                return

            connected_vehicles[vehicle_id] = {
                'Plate': vehicle_plate}

            print(vehicle_plate)
            plate_json = '{"Plate": "' + vehicle_plate + '"}'
            print(f'Publishing plate {vehicle_plate} to topic /fic/vehicles/{vehicle_id}/plate_assignment'
                  f'\nConnected vehicles: {connected_vehicles}')
            client.publish("/fic/vehicles/" + vehicle_id + "/plate_assignment", payload=plate_json, qos=1,
                           retain=False)
        else:
            print("Fleet at capacity!")
            client.publish("/fic/vehicles/" + vehicle_id + "/plate_assignment",
                           payload='{"Plate":"Not Available"}',
                           qos=1, retain=False)


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

        id = route_completion_info["vehicle_id"]
        plate = route_completion_info['Plate']
        event = route_completion_info['Event']
        timestamp = route_completion_info['time_stamp']

        # elimino la ruta del vehiculo
        if id in connected_vehicles:
            if 'Route' in connected_vehicles[id]:
                del connected_vehicles[id]['Route']
                print(f'Vehicle {plate} has completed its route.')


# except Exception as e:
#    print(f'Error in message_router: {e}')


def main():
    global client
    client = mqtt.Client()
    client.username_pw_set(username="fic_server",
                           password="fic_password")
    client.on_connect = on_connect
    client.on_message = on_message
    MQTT_SERVER = os.getenv("MQTT_SERVER_ADDRESS")
    MQTT_PORT = int(os.getenv("MQTT_SERVER_PORT"))

    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    schedule_route_assignment()
    client.loop_forever()
    print('message_router running indefinitely')


main()
