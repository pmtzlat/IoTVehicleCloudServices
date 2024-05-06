# -*- coding: utf-8 -*-
"""
Created on Sun Apr 28 15:03:55 2024

@author: saruc
"""
import os
import signal
import subprocess
import time
import threading
import json
import random
from datetime import datetime

import requests
import copy
from math import acos, cos, radians, sin
import paho.mqtt.client as mqtt

global current_speed
global currentRouteDetailedSteps
global vehicleControlCommands
global current_ldr
global current_leds_st
global current_leds
global sleeptime
global indentationForPrint1
global indentationForPrint2
global printDelimiter
global prevAngle
global commandNum
global vehicle_plate
global current_position
global distanceToObject
global STATE_TOPIC, PLATE_ASSIGNMENT_TOPIC, PLATE_REQUEST_TOPIC, ROUTE_ASSIGNMENT_TOPIC, CLIENT_NOTIFICATIONS_TOPIC
global event_message
global routes

routes = []
event_message = ''
ROUTE_ASSIGNMENT_TOPIC = ''
STATE_TOPIC = ''
PLATE_ASSIGNMENT_TOPIC = ''
PLATE_REQUEST_TOPIC = ''
current_leds = ''
current_leds_st = []
current_position = {}
vehicle_plate = ''
lock = threading.Lock()
distanceToObject = 0.0
current_speed = 0.0
current_steering = 90.0
previous_speed = 0.0
prevAngle = 0.0
current_ldr = 0.0
sleeptime = 3
commandNum = 0
indentationForPrint1 = '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t'
indentationForPrint2 = '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t'
printDelimiter = '______________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________'


def routes_manager(origin_address="Toronto", destination_address="Montreal"):
    global currentRouteDetailedSteps
    global vehicleControlCommands

    google_maps_api_key = "AIzaSyCCPgOomH8zSoErdqUKlOcb5Jf1BtThREk"
    # print("Asignando una ruta al vehiculo")
    url = "https://maps.googleapis.com/maps/api/directions/json?origin=" + origin_address + "&destination=" + \
          destination_address + "&key=" + google_maps_api_key
    # print("URL: {}".format(url))
    payload = {}
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    # current_route = response.text
    # print("La ruta es: {}".format(response.text))

    steps = response.json()["routes"][0]["legs"][0]["steps"]
    # for i in steps:
    # print(i)

    # print(len(steps))
    currentRouteDetailedSteps = get_detailed_steps(steps)
    getCommands(currentRouteDetailedSteps)
    # print("He acabado de asignar los comandos al vehiculo")


def get_detailed_steps(steps):
    detailedSteps = []  # Lista de pasos detallados de la ruta

    # Iteración sobre los pasos de la ruta a seguir por el vehículo
    for idx, step in enumerate(steps, start=1):
        print("Step duration: ", step["duration"]["value"])
        if step["duration"]["value"] == 0:
            step["duration"]["value"] = 1
        stepSpeed = (step["distance"]["value"] / 1000) / (step["duration"]["value"] / 3600)  # Velocidad en km/h
        # stepDistance = step["distance"]["value"]
        # stepTime = step["duration"]["value"]

        try:
            stepManeuver = step["maneuver"]  # Maniobra del paso de la ruta
        except:
            stepManeuver = "Straight"  # Si no hay maniobra, se considera que el paso es recto

        # Subpasos del paso de la ruta (polilínea)
        substeps = decode_polyline(step["polyline"]["points"])

        # Iteración sobre los subpasos del paso de la ruta
        for index in range(len(substeps) - 1):
            p1 = {"latitude": substeps[index][0], "longitude": substeps[index][1]}
            p2 = {"latitude": substeps[index + 1][0], "longitude": substeps[index + 1][1]}

            # Cálculo de la distancia entre los puntos p1 y p2
            points_distance = distance(p1, p2)

            if points_distance > 0.001:
                substep_duration = points_distance / step["duration"]["value"]  # Duración del subpaso

                # Creación de un nuevo paso detallado
                new_detailed_step = {
                    "Origin": p1,
                    "Destination": p2,
                    "Speed": stepSpeed,
                    "Time": substep_duration,
                    "Distance": points_distance,
                    "Maneuver": stepManeuver
                }

                # print(new_detailed_step)

                # Agregar el nuevo paso detallado a la lista
                detailedSteps.append(new_detailed_step)

    # print("La ruta tiene {} pasos".format(len(detailedSteps)))

    return detailedSteps


# NO SE TOCA
def decode_polyline(polyline_str):
    '''Pass a Google Maps encoded polyline string; returns list of lat/lon pairs'''
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}

    # Coordinates have variable length when encoded, so just keep
    # track of whether we've hit the end of the string. In each
    # while loop iteration, a single coordinate is decoded
    while index < len(polyline_str):
        # Gather lat/lon changes, store them in a dictionary to apply them later
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0

            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break

            if (result & 1):
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = (result >> 1)

        lat += changes['latitude']
        lng += changes['longitude']

        coordinates.append((lat / 100000.0, lng / 100000.0))

    return coordinates


def distance(p1, p2):
    p1Latitude = p1["latitude"]
    p1Longitude = p1["longitude"]
    p2Latitude = p2["latitude"]
    p2Longitude = p2["longitude"]
    # print("Calculando la distancia entre ({}, {}) y ({}, {})".format(p1["latitude"], p1["longitude"], p2["latitude"], p2["longitude"]))

    earth_radius = {"km": 6371.0087714, "mile": 3959}
    result = earth_radius["km"] * acos(
        cos((radians(p1Latitude))) * cos(radians(p2Latitude)) * cos(radians(p2Longitude) - radians(p1Longitude)) +
        sin(radians(p1Latitude)) * sin(radians(p2Latitude)))

    # print("La distancia calculada es: {}".format(result))

    return result


def getCommands(currentRouteDetailedSteps):
    global vehicleControlCommands

    vehicleControlCommands = []

    for index, detailedStep in enumerate(currentRouteDetailedSteps, start=1):
        # print("Generando el comando {} para el paso {}".format(index, detailedStep))
        if (detailedStep["Maneuver"].upper() == "STRAIGHT" or detailedStep["Maneuver"].upper() == "RAMP-LEFT"
                or detailedStep["Maneuver"].upper() == "RAMP-RIGHT" or detailedStep["Maneuver"].upper() == "MERGE"
                or detailedStep["Maneuver"].upper() == "MANEUVER-UNSPECIFIED"):
            steeringAngle = 90.0

        if detailedStep["Maneuver"].upper() == "TURN-LEFT":
            steeringAngle = 135.0

        if detailedStep["Maneuver"].upper() == "UTURN-LEFT":
            steeringAngle = 180.0

        if detailedStep["Maneuver"].upper() == "TURN_SHARP-LEFT":
            steeringAngle = 105.0

        if detailedStep["Maneuver"].upper() == "TURN_SLIGHT-LEFT":
            steeringAngle = 150.0

        if detailedStep["Maneuver"].upper() == "TURN-RIGHT":
            steeringAngle = 45.0

        if detailedStep["Maneuver"].upper() == "UTURN-RIGHT":
            steeringAngle = 0.0

        if detailedStep["Maneuver"].upper() == "TURN-SHARP-RIGHT":
            steeringAngle = 15.0

        if detailedStep["Maneuver"].upper() == "TURN-SLIGHT-RIGHT":
            steeringAngle = 60.0

        newCommand = {"SteeringAngle": steeringAngle, "Speed": detailedStep["Speed"], "Time": detailedStep["Time"]}
        vehicleControlCommands.append(newCommand)

    # for i in range(50):
    # print(vehicleControlCommands[i])


# -------------------------------------------------
def vehicle_controller():
    global currentRouteDetailedSteps
    global vehicleControlCommands
    global current_speed
    global previous_speed
    global prevAngle, commandNum
    global routes

    print("Ejecutando el hilo de control del vehiculo")
    while True:
        j = 0
        if len(routes) > 0:
            print(f'Origin: {routes[0]["Origin"]}')
            print(f'Destination: {routes[0]["Destination"]}')
            origin_address = routes[0]["Origin"]
            destination_address = routes[0]["Destination"]
            routes_manager(origin_address, destination_address)
            # print("Los comandos del vehiculo son: {}".format(vehicleControlCommands))

            i = 0
            prevObstacle = False
            commandNum = 0
            while len(vehicleControlCommands) > 0:

                lock.acquire()
                obstacle = distanceToObject < 10.0
                if obstacle:

                    if obstacle != prevObstacle:
                        print('\nObstace found!')
                        current_speed = 0.0
                        print('CS = ' + str(current_speed) + ', SA = ' + str(current_steering) + '\n')
                    prevObstacle = obstacle
                    lock.release()
                    continue
                prevObstacle = obstacle
                lock.release()

                lock.acquire()
                # print("\nCOMANDO Nº: " + str(i) +'. \nCommand speed: '  + str(vehicleControlCommands[0]['Speed']) + ', Angle: ' + str(vehicleControlCommands[0]['SteeringAngle']) + '.')
                toPrint = '\n'
                printIt = False
                previous_speed = current_speed
                prevAngle = current_steering
                if (vehicleControlCommands[0]["Speed"] != current_speed):
                    toPrint += 'Cambiando speed a ' + str(vehicleControlCommands[0]["Speed"]) + '. '
                    printIt = True
                if (vehicleControlCommands[0]["SteeringAngle"] != current_steering):
                    toPrint += 'Cambiando angle a ' + str(vehicleControlCommands[0]["SteeringAngle"]) + '. '
                    printIt = True
                lock.release()
                commandNum += 1
                executeCommand(vehicleControlCommands[0], currentRouteDetailedSteps[i])

                lock.acquire()
                toPrint += '\n\n\tResult:\n\tCS = ' + str(current_speed) + ', SA = ' + str(
                    current_steering) + '\n\nExecuting command ' + str(commandNum) + ' for ' + str(
                    vehicleControlCommands[0]["Time"]) + ' time units (unknown) ...\n'
                if printIt:
                    print(printDelimiter)
                    print(toPrint)
                lock.release()

                vehicleControlCommands.pop(0)
                # time.sleep(0.5) #para dar tiempo a lo que se imprime para poder ver mejor el funcionamiento del programa

                i += 1
                # if i == 5: break

            if len(routes) > 0:
                del routes[0]

            print('Moving to next route...')



        else:
            # elif len(routes) == 0 and len(vehicleControlCommands) == 0:
            print(len(routes))
            vehicle_stop()
            time.sleep(10)


def executeCommand(command, step):
    global current_steering
    global current_speed
    global current_position

    lock.acquire()
    current_steering = command["SteeringAngle"]
    current_speed = command["Speed"]
    time.sleep(command["Time"])
    current_position = step["Destination"]
    lock.release()
    # print(current_steering, current_speed, current_position)
    # print("EXECUTING...")


def vehicle_stop():
    global vehicleControlCommands
    global currentRouteDetailedSteps
    global current_steering
    global current_speed
    global current_leds_st
    global current_leds
    global current_ldr
    global current_obstacle_distance
    global event_message
    lock.acquire()
    vehicleControlCommands = []
    currentRouteDetailedSteps = []
    current_steering = 90.0
    current_speed = 0
    current_leds = '[{"Light": "Front", "Color":"White", "Intensity":0.0, "Blinking": "False"},' \
                   '{"Light": "Front", "Color":"White", "Intensity": 0.0, "Blinking": "False"},' \
                   '{"Light": "Back", "Color":"Red", "Intensity":0.0, "Blinking": "False"},' \
                   '{"Light": "Back", "Color": "Red", "Intensity":0.0, "Blinking": "False"}]'
    current_leds_st = json.loads(current_leds)
    current_ldr = 0.0
    current_obstacle_distance = 0.0
    event_message = "Route Completed"
    lock.release()

    print("Vehicle stopped")


# __________________________________________________
def environment_simulator():
    global current_speed
    global current_ldr
    global vehicleControlCommands
    global distanceToObject
    global sleeptime
    global indentationForPrint1
    global printDelimiter

    current_obstacle_distance = 0.0  # Valor inicial de distancia al obstáculo

    while True:
        # Simular la luz del entorno
        lock.acquire()
        current_ldr = simulate_ldr(current_ldr)

        lock.release()
        # print("Luz", current_ldr)

        # Simular la distancia al obstáculo
        current_obstacle_distance = simulate_obstacle(current_obstacle_distance)

        # print("Obstaculo", current_obstacle_distance)

        # Determinar si el vehículo debe frenar
        '''def pick_random_number():
            numbers = [5, 15]
            return random.choice(numbers

        current_obstacle_distance = pick_random_number()'''
        print(printDelimiter)
        print('\n' + indentationForPrint1 + 'Current LDR: ' + str(current_ldr) + '\n' +
              indentationForPrint1 + 'Obstacle distance: ' + str(current_obstacle_distance) + '\n')

        lock.acquire()
        distanceToObject = current_obstacle_distance
        lock.release()

        # Esperar un tiempo antes de la próxima simulación
        time.sleep(sleeptime)


def simulate_ldr(current_ledr):
    # print("Simulando la luz del entorno")
    if current_ledr > 0.0:
        current_ledr += random.uniform(-300.0, 300.0)
        if current_ledr < 0.0:
            current_ledr = 0.0

    else:
        current_ledr = random.uniform(0.0, 3000.0)

    return current_ledr


def simulate_obstacle(current_obstacle_distance_p):
    # print("Simulando la distancia de obstaculos")
    if current_obstacle_distance_p > 0.0:
        current_obstacle_distance_p += random.uniform(-5.0, 5.0)
        if current_obstacle_distance_p < 0.0:
            current_obstacle_distance_p = 0.0

    else:
        current_obstacle_distance_p = random.uniform(0.0, 50.0)
        # current_obstacle_distance = random.uniform(0.0, 15.0)

    return current_obstacle_distance_p


def printLights(lights, status):
    global indentationForPrint2, printDelimiter, current_speed, current_steering, current_ldr, commandNum

    def format_light_info(light_info):
        # Extract values from the input dictionary
        color = light_info.get('Color', 'None')
        intensity = light_info.get('Intensity', 0.0)
        blinking = light_info.get('Blinking', 'None')
        orientation = light_info.get('Orientation', 'None')
        light = light_info.get('Light', 'None')

        # Format the string
        formatted_string = f'{light} {orientation} light: Color: {color}, Intensity: {intensity}, Blinking: {blinking}'

        return formatted_string

    print(printDelimiter)
    print('\n' + indentationForPrint2 + 'Change of state in lights after command ', commandNum, ':\n',
          indentationForPrint2, 'previous speed:', previous_speed,
          ', current: ', current_speed, '\n', indentationForPrint2, 'previous angle:', prevAngle,
          ', current: ', current_steering, '\n', indentationForPrint2, 'Light levels: ',
          current_ldr, '\n', indentationForPrint2, 'Status: \t ', status, '\n')

    for i in lights:
        print(indentationForPrint2 + format_light_info(i))

        # print(i)
    print()


def getLightState(status):
    normal = [{"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Left", "Light": "Front"},
              {"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Right", "Light": "Front"},
              {"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Left", "Light": "Back"},
              {"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Right", "Light": "Back"}]

    turningLeft = [{"Color": "Yellow", "Intensity": 100.0, "Blinking": "True", "Orientation": "Left", "Light": "Front"},
                   {"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Right", "Light": "Front"},
                   {"Color": "Yellow", "Intensity": 100.0, "Blinking": "True", "Orientation": "Left", "Light": "Back"},
                   {"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Right", "Light": "Back"}]

    turningRight = [{"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Left", "Light": "Front"},
                    {"Color": "Yellow", "Intensity": 100.0, "Blinking": "True", "Orientation": "Right",
                     "Light": "Front"},
                    {"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Left", "Light": "Back"},
                    {"Color": "Yellow", "Intensity": 100.0, "Blinking": "True", "Orientation": "Right",
                     "Light": "Back"}]

    brakeStart = [{"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Left", "Light": "Front"},
                  {"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Right", "Light": "Front"},
                  {"Color": "Red", "Intensity": 50.0, "Blinking": "None", "Orientation": "Left", "Light": "Back"},
                  {"Color": "Red", "Intensity": 50.0, "Blinking": "None", "Orientation": "Right", "Light": "Back"}]

    brakeEnd = [{"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Left", "Light": "Front"},
                {"Color": "None", "Intensity": 0.0, "Blinking": "None", "Orientation": "Right", "Light": "Front"},
                {"Color": "Red", "Intensity": 100.0, "Blinking": "None", "Orientation": "Left", "Light": "Back"},
                {"Color": "Red", "Intensity": 100.0, "Blinking": "None", "Orientation": "Right", "Light": "Back"}]

    lowLight = [{"Color": "White", "Intensity": 100.0, "Blinking": "None", "Orientation": "Left", "Light": "Front"},
                {"Color": "White", "Intensity": 100.0, "Blinking": "None", "Orientation": "Right", "Light": "Front"},
                {"Color": "Red", "Intensity": 50.0, "Blinking": "None", "Orientation": "Left", "Light": "Back"},
                {"Color": "Red", "Intensity": 50.0, "Blinking": "None", "Orientation": "Right", "Light": "Back"}]

    states = {
        'Normal': normal,
        'Turning left': turningLeft,
        'Turning right': turningRight,
        'Brake start': brakeStart,
        'Brake end': brakeEnd,
        'Low light': lowLight
    }

    return states[status]


def led_controller():
    global current_ldr
    global current_steering
    global current_speed
    global previous_speed
    global current_obstacle_distance
    global current_leds_st
    global vehicleControlCommands
    global sleeptime, indentationForPrint2, prevAngle
    d2 = 0
    c = 0
    status = 'Normal'
    while True:
        prevStatus = status
        lock.acquire()

        if current_speed == 0.0:
            if current_speed < previous_speed:
                if status == 'Brake end':
                    status = 'Normal'
                elif status == 'Brake start':
                    status = 'Brake end'
                else:
                    status = 'Brake start'
            else:
                status = 'Normal'
        else:
            if current_steering > 100:
                status = 'Turning left'
            elif current_steering < 80:
                status = 'Turning right'
            else:
                if c == 0:
                    c += 1
                elif current_speed < previous_speed:
                    if status == 'Brake end':
                        status = 'Normal'
                    elif status == 'Brake start':
                        status = 'Brake end'
                    else:
                        status = 'Brake start'


                elif current_ldr > 1500:
                    status = 'Low light'
                else:
                    status = 'Normal'

        # print(indentationForPrint2 + str(d2))

        current_leds_st = getLightState(status)
        if status != prevStatus:
            printLights(current_leds_st, status)
        if status != ('Brake start' or 'Brake end'):
            previous_speed = current_speed
        prevAngle = current_steering

        lock.release()


def get_host_name():
    bashCommandName = 'echo $HOSTNAME'
    host = subprocess \
               .check_output(['bash', '-c', bashCommandName]) \
               .decode("utf-8")[0:-1]
    return host


def on_connect(client, userdata, flags, rc):
    global PLATE_ASSIGNMENT_TOPIC, PLATE_REQUEST_TOPIC, ROUTE_ASSIGNMENT_TOPIC

    if rc == 0:
        PLATE_ASSIGNMENT_TOPIC = "/fic/vehicles/" + get_host_name() + "/plate_assignment"
        ROUTE_ASSIGNMENT_TOPIC = "/fic/vehicles/" + get_host_name() + "/route_assignment"
        print("Connected to MQTT Broker!")
        PLATE_REQUEST_TOPIC = "/fic/vehicles/" + get_host_name() + "/plate_request"
        payload = {"vehicle_id": get_host_name()}
        client.publish(PLATE_REQUEST_TOPIC, payload= json.dumps(payload),
                       qos=1, retain=False)
        print(f"Subscribed to {PLATE_ASSIGNMENT_TOPIC}")
        client.subscribe(PLATE_ASSIGNMENT_TOPIC)
        print(f"Subscribed to {ROUTE_ASSIGNMENT_TOPIC}")
        client.subscribe(ROUTE_ASSIGNMENT_TOPIC)

    else:
        print(f"Connection failed with result code {rc}")


def on_message(client, userdata, msg):
    global vehicle_plate, routes
    payload = msg.payload.decode()
    topic = (msg.topic).split('/')

    print(f'Message received: {payload} in topic: {topic[-1]}')

    if topic[-1] == "plate_assignment":

        json_config_received = json.loads(payload)

        if json_config_received["Plate"] != "Not Available":
            vehicle_plate = json_config_received["Plate"]
            print(f'Plate assigned: {vehicle_plate}')

    elif topic[-1] == "route_assignment":
        required_route = json.loads(msg.payload.decode())
        print('Received new route: ', required_route)
        lock.acquire()
        routes.append(required_route)
        lock.release()


def getVehicleStatus():
    global vehicle_plate, current_speed, current_steering
    global current_ldr, current_position, distanceToObject, current_leds_st
    #print(f'\nCurrent_position: {current_position}\n')
    vehicle_status = {"vehicle_id": get_host_name(), "vehicle_plate":
        vehicle_plate, "telemetry": {"current_steering": current_steering,
                                     "current_speed": current_speed,
                                     "current_position": json.dumps(current_position),
                                     "current_leds": json.dumps(current_leds_st),
                                     "current_ldr": current_ldr,
                                     "current_obstacle_distance": distanceToObject,
                                     "time_stamp": datetime.now().isoformat()}}
    return vehicle_status


def publish_telemetry(client):
    global STATE_TOPIC
    vehicle_status = getVehicleStatus()
    json_telemetry = json.dumps(vehicle_status)
    client.publish(STATE_TOPIC, payload=json_telemetry, qos=1,
                   retain=False)


def publish_event(client):
    global CLIENT_NOTIFICATIONS_TOPIC, vehicle_plate, event_message

    CLIENT_NOTIFICATIONS_TOPIC = "/fic/vehicles/" + get_host_name() + "/client_notifications"
    lock.acquire()
    event_to_send = {"vehicle_id": get_host_name(), "Plate": vehicle_plate, "Event": event_message,
                     "time_stamp": datetime.now().isoformat()}
    lock.release()
    event_to_send["time_stamp"] = str(event_to_send["time_stamp"])
    client.publish(CLIENT_NOTIFICATIONS_TOPIC, payload=json.dumps(event_to_send), qos=1,
                   retain=False)


def mqtt_communications():
    global vehicle_plate, STATE_TOPIC
    client = mqtt.Client()
    client.username_pw_set(username="fic_server", password="fic_password")
    client.on_connect = on_connect
    client.on_message = on_message
    connection_dict = {"vehicle_plate": vehicle_plate, "status":
        "Off - Unregular Diconnection",
                       "time_stamp": datetime.now().isoformat()}
    STATE_TOPIC = "/fic/vehicles/" + get_host_name() + "/car_state"
    connection_dict["time_stamp"] = str(connection_dict["time_stamp"])
    connection_str = json.dumps(connection_dict)
    client.will_set(STATE_TOPIC, connection_str)
    MQTT_SERVER = os.getenv("MQTT_SERVER_ADDRESS")
    MQTT_PORT = int(os.getenv("MQTT_SERVER_PORT"))
    print(f'mqtt ip: {MQTT_SERVER}, port: {MQTT_PORT}')
    client.connect(MQTT_SERVER, MQTT_PORT, 60)


    client.loop_start()
    while True:
        mqttLoop(client)

    client.loop_stop()


def mqttLoop(client):
    global event_message
    time.sleep(10)
    if len(current_position)>0 :
        publish_telemetry(client)
    if (event_message != ''):
        print('Publishing stoppage...')
        publish_event(client)
        print('Published.')
        lock.acquire()
        event_message = ''
        lock.release()


def main():
    try:


        t1 = threading.Thread(target=mqtt_communications, daemon=True)
        t1.start()
        t2 = threading.Thread(target=vehicle_controller, daemon=True)
        t2.start()
        t3 = threading.Thread(target=environment_simulator, daemon=True)

        t3.start()
        t4 = threading.Thread(target=led_controller, daemon=True)
        t4.start()
        t1.join()
        t2.join()
        t3.join()
        t4.join()

    except Exception as e:
        print(e)
        vehicle_stop()


if __name__ == '__main__':
    main()
