-Simulacion

Creacion puerto virtual para conexion local
sudo socat PTY,link=/tmp/virtual-serial,rawer,echo=0 PTY,echo=0 &

Creacion de puerto virtual para acceder mediante la red en 
el puerto 12345 en la direccion "/tmp/virtual-serial"
sudo socat PTY,link=/tmp/virtual-serial,rawer TCP-LISTEN:12345,reuseaddr

------------------------------------
-Creacion de servicio del script para el SO

Al archivo "serial_to_mqtt.service" modificarle la configuracion WorkingDirectory 
a la carpeta que contiene el main, que contiene la carpeta "config" con los archivos
de configuracion ".yaml" y el ExecStart a la direccion donde esta el archivo
ejecutable del programa llamado probablemente "main"

Seguidamente copiar el archivo "serial_to_mqtt.service" a la direccion 
/etc/systemd/system mediante el comando:
sudo cp direccion/del/archivo/serial_to_mqtt.service /etc/systemd/system

Luego darle los permisos correspondientes con el comando:
sudo chmod 644 /etc/systemd/system/myservice.service

Luego ejecutar los siguientes comandos para poner a correr el servicio:
sudo systemctl daemon-reload
sudo systemctl start serial_to_mqtt.service

Por ultimo ejecutar el siguiente comando para verificar que 
todo este funcionando de forma correcta:
sudo systemdctl status serial_to_mqtt.service

-------------------------------------
-Compilar la aplicacion

Para compilar la aplicacion en caso de algun cambio, solo se 
debe acceder al entorno virtual de pithon de 
este proyecto y compilarlo mediante la libreria pyinstaller

Primero se debe acceder al entorno virtual de la aplicacion mediante:
cd direccion/del/proyecto/FACP_Scripts

Luego se activa el entorno virtual:
source .venv/bin/activate

Despues se compila la aplicacion mediante:
pyinstaller main.py

La aplicacion queda lista en la direccion "./dist/main" en un archivo con nombre "main" 
(La carpeta _internal tambien se requiere en la misma direccion junto con el ejecutable
 para que funcione correctamente)

Finalmente se deben copiar a la misma direccion de la aplicacion "main" los archivos 
".yaml" para brindar las configuraciones necesarias para que funcione correctamente
ya que se eliminan con cada vez que se corre el pyinstaller