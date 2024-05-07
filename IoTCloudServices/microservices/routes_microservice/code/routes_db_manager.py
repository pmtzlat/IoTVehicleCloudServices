import os
import json
import datetime
import mysql.connector as mysql


def connect_database():
    mydb = mysql.connect(
        host=os.getenv('DBHOST'),
        user=os.getenv('DBUSER'),
        password=os.getenv('DBPASSWORD'),
        database=os.getenv('DBDATABASE')
    )
    return mydb


def get_routes_assigned_to_vehicle(params, app):
    result = []
    try:
        mydb = connect_database()
        with mydb.cursor() as cursor:
            sql = """SELECT origin, destination, plate, time_stamp, completed
                FROM routes 
                WHERE plate = %s 
                ORDER BY time_stamp DESC"""
            vehicle_plate = params["vehicle_plate"]
            query_params = (vehicle_plate,)
            cursor.execute(sql, query_params)
            my_result = cursor.fetchall()
            for origin, destination, plate, time_stamp, completed in my_result:
                item = {"Origin": origin, "Destination": destination, "plate": plate, "completed": completed,
                        "time_stamp": time_stamp}
                result.append(item)
        return result
    except Exception as e:
        app.logger.debug("Error getting the routes assigned to this plate: ", vehicle_plate)
        return None


def assign_new_route(params, app):
    try:
        mydb = connect_database()
        with mydb.cursor() as cursor:
            # Check if there is a route with the same plate and completed = 0
            check_sql = "SELECT * FROM available_plates WHERE plate = %s AND is_assigned = 1"
            cursor.execute(check_sql, (params["vehicle_plate"],))
            assigned_plate = cursor.fetchone()
            if not assigned_plate:
                app.logger.debug("Plate is not assigned to a vehicle")
                return 0
            check_sql = "SELECT * FROM routes WHERE plate = %s AND completed = 0"
            cursor.execute(check_sql, (params["vehicle_plate"],))
            existing_route = cursor.fetchone()
            if existing_route:
                app.logger.debug("Plate is currently assigned to a route")
                return 0  # Indicates that the route was not assigned due to conflict

            # If no conflicting route found, insert the new route
            insert_sql = """
                INSERT INTO routes (origin, destination, plate, time_stamp, completed) 
                VALUES (%s, %s, %s, %s, 0)
            """
            vehicle_plate = params["vehicle_plate"]
            origin = params["Origin"]
            destination = params["Destination"]
            time_stamp = datetime.datetime.now()
            tuples = (origin, destination, vehicle_plate, time_stamp)
            cursor.execute(insert_sql, tuples)
            mydb.commit()
            app.logger.debug(cursor.rowcount, "Route inserted.")
            return 1
    except Exception as e:
        app.logger.debug("ERROR on route insertion!" + str(e))
        app.logger.debug(params)
        return -1


def complete_route(params, app):
    result = True
    try:
        mydb = connect_database()
        with mydb.cursor() as cursor:

            update_sql = """
                            UPDATE routes SET completed = 1 WHERE plate = %s
                        """
            vehicle_plate = params["vehicle_plate"]
            cursor.execute(update_sql)
            mydb.commit()

            app.logger.debug("Success completing route")



    except Exception as e:
        app.logger.debug("ERROR on route insertion!" + str(e))
        app.logger.debug(params)
        result = False

    return result
