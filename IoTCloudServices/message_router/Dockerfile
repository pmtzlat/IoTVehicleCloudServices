FROM python:3.11.1

WORKDIR /etc/usr/src/app

COPY ./code/* /etc/usr/src/app

RUN pip install -r requirements.txt

CMD ["python", "message_router.py"]
