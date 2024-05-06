# Instrucción FROM para especificar la imagen base
FROM debian:buster

# Actualizar el paquete e instalar Mosquitto y clientes
RUN apt update && apt upgrade -y && apt install mosquitto mosquitto-clients -y

# Crear archivo de contraseña para Mosquitto
RUN touch /etc/mosquitto/passwd && mosquitto_passwd -b /etc/mosquitto/passwd fic_server fic_password

COPY code/mosquitto.conf /etc/mosquitto/mosquitto.conf

# Ejecutar Mosquitto con la configuración especificada
CMD ["/usr/sbin/mosquitto", "-c", "/etc/mosquitto/mosquitto.conf"]