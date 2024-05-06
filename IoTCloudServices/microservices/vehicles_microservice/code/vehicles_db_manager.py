import os

import mysql.connector as mysql


def connect_database():
    mydb = mysql.connect(
        host=os.getenv('DBHOST'),
        user=os.getenv('DBUSER'),
        password=os.getenv('DBPASSWORD'),
        database=os.getenv('DBDATABASE')
    )
    return mydb


def get_active_vehicles():
    try:
        mydb = connect_database()
        queryString = 'SELECT plate FROM vehicles WHERE status = 1;'
        with mydb.cursor() as mycursor:
            mycursor.execute(queryString)
            plates = [{"Plate": plate[0]} for plate in mycursor.fetchall()]
        return plates
    except Exception as e:
        print(f'Error in get_active_vehicles: {e}')
        return ''

def get_vehicle_plate(vehicle_id):
    mydb = connect_database()
    with mydb.cursor() as mycursor:
        mycursor.execute('SELECT plate FROM vehicles WHERE vehicle_id = %s ORDER BY plate ASC LIMIT 1;', (vehicle_id,))
        existing_plate = mycursor.fetchone()
        if existing_plate:
            return existing_plate
        return ""


def register_new_vehicle(vehicle_id, app):
    try:
        app.logger.debug('Registering new vehicle in db...')
        mydb = connect_database()

        with mydb.cursor() as mycursor:

            existing_plate = get_vehicle_plate(vehicle_id);

            if existing_plate:
                app.logger.debug(f'Vehicle {vehicle_id} already has plate ( {existing_plate[0]} )!')
                return existing_plate[0]

            mycursor.execute(
                'SELECT plate, is_assigned FROM available_plates WHERE is_assigned = 0 ORDER BY plate ASC LIMIT 1;')
            available_plate = mycursor.fetchone()

            if available_plate:
                app.logger.debug(f'Plate found for vehicle {vehicle_id}: {available_plate[0]}')
                mycursor.execute('INSERT INTO vehicles (vehicle_id, plate) VALUES (%s, %s);',
                                 (vehicle_id, available_plate[0]))
                mycursor.execute('UPDATE available_plates SET is_assigned = 1 WHERE plate = %s;', (available_plate[0],))
                mydb.commit()
                return available_plate[0]
            else:
                app.logger.debug(f'No plate found for vehicle {vehicle_id}')
                return ""

    except Exception as e:
        app.logger.debug(f'Error in register_new_vehicle for vehicle id {vehicle_id}: {e}')
        return ""


