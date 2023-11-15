import serial
import time
import json
import paho.mqtt.client as mqtt
from collections import OrderedDict

#Global variables
MQTT_username="Test1234"  #Ingresan su nombre de usuario asociados a MQTT
MQTT_password="Test1234"  #Ingresan su contraseña asociados a MQTT
MQTT_URL="c4e2607e9758412696b75708d95794bb.s1.eu.hivemq.cloud"   #Ingresa la URL asociado a su broker MQTT
MQTT_port=8883  ##Ingresa el puerto asociado a su broker MQTT
USB_port="COM3" #Cambiar por el puerto actual en uso del serial a USB
ID_Cliente="ClientePrueba1234"  #Cambiar por ID actual del cliente
ID_FACP="Edwards-IO1000-001"    #Cambiar por el ID actual del FACP

# Initialize MQTT
client = mqtt.Client()
client.username_pw_set(username=MQTT_username, password=MQTT_password)
client.tls_set()
client.connect(MQTT_URL,MQTT_port) 
client.loop_start()

# Event counter
event_counter = 1

def parse_serial_data(data):
    metadata = ""
    try:
        lines = list(filter(None, data.strip().split('\n')))
        if not lines:
            return None

        primary_data = lines[0].split('|')
        if len(primary_data) < 2:
            print(f"Invalid data received: {data}")
            return None

        ID_Evento = primary_data[0].strip()
        time_date_metadata = primary_data[1].strip().split()
        Fecha = f"{time_date_metadata[0]} {time_date_metadata[1]}"

        for meta in time_date_metadata[2:]:
            key, value = meta.split(':')
            metadata = metadata + key.strip()+ ": " + value.strip() + " | "

        if len(lines) > 1:
            metadata = metadata + 'Additional_Metadata: ' + lines[1].strip()

    except Exception as e:
        print(f"An error occurred while parsing: {e}")
        return None

    # Create an ordered dictionary with fields in the desired order
    event_data = OrderedDict([
        ("ID_Evento_Ocurrido", ID_Cliente+f"-{event_counter:09d}"),
        ("ID_Panel", ID_FACP),
        ("ID_Evento", ID_Evento),
        ("Fecha", Fecha),
        ("Metadata", metadata)
    ])

    return event_data




# Initialize serial port
ser = serial.Serial()
ser.port = USB_port 
ser.baudrate = 9600
ser.bytesize = serial.EIGHTBITS
ser.parity = serial.PARITY_NONE
ser.stopbits = serial.STOPBITS_ONE
ser.xonxoff = False

try:
    ser.open()
    if ser.is_open:
        print("Serial port is open.")
    else:
        print("Failed to open serial port.")
        exit(1)
except:
    print("Unexpected error ocurred opening the port.")
    exit(1)

buffer = ""
try:
    while True:
        if ser.in_waiting > 0:
            incoming_line = ser.readline().decode('utf-8').strip()
            print(f"Received Line: '{incoming_line}'")  # Debugging statement
            
            if not incoming_line:
                print("Detected empty line, attempting to parse buffer.")  # Debugging statement
                parsed_data = parse_serial_data(buffer)
                
                if parsed_data is not None:
                    print(f"Parsed Data: {parsed_data}")  # Debugging statement
                    parsed_data['ID_Evento_Ocurrido'] = ID_Cliente+f"-{event_counter:09d}"
                    parsed_data['ID_Panel'] = ID_FACP
                    event_counter += 1
                    client.publish("FACP/Eventos/"+ID_Cliente, json.dumps(parsed_data))
                else:
                    print("Parsed data is None, skipping MQTT publish.")  # Debugging statement
                
                buffer = ""
            else:
                buffer += incoming_line + "\n"

        time.sleep(0.1)

except KeyboardInterrupt:
    ser.close()
    client.loop_stop()
    client.disconnect()
    print("Serial port and MQTT client closed.")

