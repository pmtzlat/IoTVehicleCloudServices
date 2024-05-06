
FROM python:3.11.1

WORKDIR /usr/src/app

ADD code /usr/src/app

RUN pip install -r requirements.txt
RUN pip install --upgrade paho-mqtt

CMD ["python", "VehicleDigitalTwin.py"]
