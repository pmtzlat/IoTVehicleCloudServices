FROM python:3.11.1

WORKDIR /etc/usr/src/app

COPY ./code .

RUN pip install -r requirements.txt

CMD ["python", "vehicles_manager_api.py"]
