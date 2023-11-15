# serialToMQTT Gateway
Este script de Python se hizo con la finalidad de obtener vía una tarjeta SA 232 conectada al panel de control de alarma de incendio (FACP por sus siglas en inglés) modelo Edward's IO1000 para parsearlo y convertirlo a MQTT.

## Eventos
Se caracterizan por ser la forma de expresión de un FACP cuando necesitan dar a conocer la ocurrencia de una situación, ya sea desde la activación de alguna alarma en casos de emergencia a como eventos de mantenimiento, informando que se realizaron cambios en el panel o que alguien manipuló alguna alarma. Se caracterizan por poseer un código que especifica el tipo de evento ocurrido así como metadata adicional acorde al evento como el ID del sensor activado y la metadata asociada a él. Un ejemplo de cómo se ve un evento, utilizando al FACP Edward’s IO1000 como ejemplo, luce así mediante la conexión serial:

“
PULL ACT | 12:06:56 10/20/2023 L:1 D:126
Sala de pruebas


PROB ACT | 12:07:13 10/20/2023     E:045
Silencio Senales


MON ACT  | 12:07:13 10/20/2023     E:042
Reinicio


PULL RST | 12:07:35 10/20/2023 L:1 D:126
Sala de pruebas


PROB RST | 12:07:35 10/20/2023     E:045
Silencio Senales


MON RST  | 12:07:35 10/20/2023     E:042
Reinicio
“

Donde cada evento inicia y termina con una nueva linea, también luego de la fecha, lo que incluye corresponde a metadata asociada al evento. En el primer evento, nos menciona con “PULL ACT” que alguien activó una estación manual de alarma de emergencia, “L:1” hace referencia a en qué lazo eléctrico dentro del panel se encuentra la estación manual, “D:126” corresponde al identificador que posee dentro de la conexión eléctrica y finalmente “Sala de pruebas”, corresponde a la metadata asociada por el ingeniero a cargo de configurar el panel con el dispositivo en cuestión. 
En el segundo evento, con “PROB ACT” nos menciona que alguien activó el botón de silenciar las señales sonoras o visuales, en este caso, correspondería a las activadas previamente debido a la activación de la estación manual. Ya que son comandos del panel y no están asociados con la instalación electrica, posee el código “E:045” indicando a cuál comando dentro del panel se  refiere y finalmente posee “Silencio Senales” que es la metadata asociada al evento. 
Seguidamente, “MON ACT” hace referencia a presionar el botón de reinicio dentro del panel, ya que es necesario para que vuelva a su ciclo normal luego de la activación de una alarma, “E:042” hace referencia al código dentro del panel y “Reinicio” se refiere a la metadata asociada al evento. 
Finalmente, despues de acá se repiten los mismos eventos previamente explicados solo que con su versión “RST” que se refiere, en el caso del evento de silenciar las alarmas y la activación de la estación manual a que fueron reestablecidos exitosamente y en el caso del reinicio, a que ha finalizado.

## Estructura de los tópicos de MQTT
Esta estructura será la forma en la que los FACP registrarán la información en la nube para que los dispositivos encargados de realizar el monitoreo puedan acceder a la información de los mismos con una estructura ordenada.
Un esquema de tópicos bien pensado facilita la administración, asegura que se puedan tomar decisiones rápidas en tiempo real y permite aplicar medidas de seguridad como el control de acceso basado en roles.
Con el esquema propuesto, se busca que cada cliente junto con su correspondiente cantidad de FACPs asociados de las marcas correspondientes sea diferenciado uno de otro, así como un identificador único por evento ocurrido para hacer posible diferenciar cada evento particular de otro.

Esquema de Tópicos Sugerido
FACP: Para definir que se está monitoreando páneles de control de alarma de incendios.
FACP
Eventos: Para definir que se está monitoreando eventos de páneles de control de alarmas de incendios.
FACP/Eventos
ID_Cliente: Para diferenciar entre múltiples clientes.
FACP/Eventos/ID_Cliente

Metadados necesarios dentro del mensaje (Utilizando JSON)
ID_Evento_Ocurrido: Esto corresponde a un identificador único asociado no al tipo de evento en sí, si no al evento único ocurrido en ese momento para diferenciarlo de sus similares.
ID_Evento: Esto corresponde a un identificador único asociado al evento ocurrido.
ID_Panel: Esto servirá para verificar la información asociada al panel del cliente, ya que puede tener más de 1 como su modelo, ubicación y cual de sus páneles se está comunicando.
Fecha: Corresponde a la fecha del evento suministrada por el evento.
Metadatos del evento: Los eventos siempre contienen metadatos asociados al mismo.

### Ejemplo tópico
Este representa un ejemplo de un evento parseado y enviado exitosamente a través de MQTT:
Evento inicialmente recibido mediante conexión serial:

“
MON ACT  | 12:07:13 10/20/2023     E:042
Reinicio
“

Evento enviado al tópico FACP/Eventos/ClientePrueba1234:

{
  "ID_Evento_Ocurrido": "ClientePrueba1234-000000002",
  "ID_Panel": "Edwards-IO1000-001",
  "ID_Evento": "MON RST",
  "Fecha": "13:01:58 10/20/2023",
  "Metadata": "E: 042 | Aditional_metadata: Reinicio"
}

