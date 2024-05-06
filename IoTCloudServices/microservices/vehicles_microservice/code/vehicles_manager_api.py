from flask import Flask, request
from flask_cors import CORS
import os
import vehicles_db_manager
import logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
CORS(app)


@app.route('/vehicles/register/', methods=['POST'])
def register_new_vehicle():
    vehicle_data = request.get_json()
    app.logger.debug(f'Vehicle data received: {vehicle_data}')

    if not vehicle_data or 'vehicle_id' not in vehicle_data:
        return {"result": "Error: Wrong data structure"}, 400

    vehicle_id = vehicle_data['vehicle_id']
    app.logger.debug('Registering new vehicle with id {}'.format(vehicle_id))
    result = vehicles_db_manager.register_new_vehicle(vehicle_id, app)

    if result:
        plate = vehicles_db_manager.get_vehicle_plate(vehicle_id)[0]
        app.logger.debug('Success!')
        app.logger.debug(plate[0])
        return {"Plate": plate}, 201
    else:
        app.logger.debug('No plate found')
        return {"Plate": None}, 500


@app.route('/vehicles/retrieve/', methods=['GET'])
def retrieve_vehicles():
    active_vehicles = vehicles_db_manager.get_active_vehicles()

    if active_vehicles:
        return {"Vehicles": active_vehicles}, 201
    else:

        return {"result": "No se encontraron vehículos activos"}, 404


if __name__ == '__main__':
    HOST = os.getenv('HOST')
    PORT = os.getenv('PORT')
    app.run(host=HOST, port=PORT)
