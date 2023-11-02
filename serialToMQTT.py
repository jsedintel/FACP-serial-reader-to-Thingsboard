import serial
import time
import json
import paho.mqtt.client as mqtt
from collections import OrderedDict

# Initialize MQTT
client = mqtt.Client()
client.username_pw_set(username="", password="") #Ingresan su nombre de usuario y contraseña asociados a MQTT
client.tls_set()
client.connect("URLBrokerMQTT",1883) #Ingresan la URL y el puerto asociado a su broker MQTT de la forma ("URL", puerto)
client.loop_start()

# Event counter
event_counter = 1

from collections import OrderedDict

from collections import OrderedDict

def parse_serial_data(data):
    metadata = {}
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
            metadata[key.strip()] = value.strip()

        if len(lines) > 1:
            metadata['Additional_Metadata'] = lines[1].strip()

    except Exception as e:
        print(f"An error occurred while parsing: {e}")
        return None

    # Create an ordered dictionary with fields in the desired order
    event_data = OrderedDict([
        ("ID_Evento_Ocurrido", f"ClientePrueba1234-{event_counter:09d}"),
        ("ID_Panel", "Edwards-IO1000-001"),
        ("ID_Evento", ID_Evento),
        ("Fecha", Fecha),
        ("Metadata", metadata)
    ])

    return event_data




# Initialize serial port
ser = serial.Serial()
ser.port = 'COM3'
ser.baudrate = 9600
ser.bytesize = serial.EIGHTBITS
ser.parity = serial.PARITY_NONE
ser.stopbits = serial.STOPBITS_ONE
ser.xonxoff = False

ser.open()

if ser.is_open:
    print("Serial port is open.")
else:
    print("Failed to open serial port.")
    exit(1)

buffer = ""

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
                    parsed_data['ID_Evento_Ocurrido'] = f"ClientePrueba1234-{event_counter:09d}"
                    parsed_data['ID_Panel'] = "Edwards-IO1000-001"
                    event_counter += 1
                    client.publish("FACP/Eventos/ClientePrueba1234", json.dumps(parsed_data))
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

