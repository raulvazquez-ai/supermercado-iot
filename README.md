# ENTREGABLE E1: SUPERMERCADO INTELIGENTE (CADENA DE FRÍO)

Este sistema monitoriza las cámaras frigoríficas de un supermercado para asegurar la cadena de frío mediante sensores de temperatura y contacto en las puertas.

# EXPLICACIONES SENSORES: 

Para dotar de máximo realismo a la generación de datos (Componente C1), los simuladores no se limitan a emitir valores aleatorios. Implementan una máquina de 
estados y un motor que calcula una **media móvil local** interna para reaccionar a su propio entorno físico.

A continuación, se detalla el comportamiento de cada tipo de sensor:

1. Comportamiento Global (Ruido, Desgaste y Mantenimiento)
Todos los sensores comparten una base termodinámica:
  * **Ruido Gaussiano:** A cada lectura se le aplica un ruido gaussiano sobre su valor base para simular la imperfección natural de los componentes electrónicos.
  * **Fallos Catastróficos (1%):** En cada ciclo, hay una probabilidad de que el sensor pierda conexión o se rompa, emitiendo un valor de error de `-999.0` y cambiando 
  su estado a `fallo`.
  * **Auto-Recuperación (10%):** Si un sensor falla o se degrada, el sistema simula la intervención del equipo de mantenimiento, existiendo un 10% de probabilidad por 
  ciclo de que sea reparado, restaurando su estado a `normal` y reseteando sus desviaciones (drift).

2. Cámaras Frigoríficas (Carnicería y Congelados)
Simulan el desgaste mecánico de los motores de refrigeración basándose en su temperatura:
  * **Humedad Relativa:** Se inyecta de forma independiente con su propio ruido gaussiano (ej. 85% en carnicería, 60% en congelados).
  * **Estrés Térmico (`is_degraded`):** El sensor vigila su propia media móvil. Si la cámara supera el umbral crítico (7°C en carnicería o -15°C en congelados), la 
  probabilidad de que el motor sufra una avería por sobreesfuerzo se duplica.
  * **Deriva Térmica:** Si el motor entra en estado degradado, la temperatura comenzará a subir irremediablemente (+0.4 a +1.5 grados por ciclo) hasta que los técnicos 
  lo reparen. 

3. Zona de Cajas (Sensor de CO2)
Simula el flujo de personas y la calidad del aire:
  * **Aglomeraciones (`queue_active`):** El nivel de CO2 fluctúa de forma natural, pero hay un 4% de probabilidad de que se forme una cola en las cajas. Cuando esto 
  ocurre, los niveles de CO2 suben drásticamente (hasta un límite de 600 de deriva) simulando la concentración de personas.
  * **Ventilación (`clearing_queue`):** Eventualmente (5% de probabilidad), la cola se disipa. Esto activa un estado de ventilación donde los niveles de CO2 caen 
  rápidamente hasta volver al valor base del local (450 ppm).

4. Frutería (Sensor de Etileno)
Simula la maduración climatérica de las frutas expuestas:
  * **Acumulación de Gas:** El etileno aumenta constantemente (+0.04 a +0.08 por ciclo) de forma gradual simulando la maduración de la fruta.
  * **Intervención Humana (`clearing`):** Si la concentración media local supera los 0.5 ppm, el gas empieza a ser crítico. En ese momento, existe un 30% de probabilidad 
  de que un trabajador del supermercado retire la fruta pasada o ventile la zona, haciendo que los niveles de etileno bajen progresivamente hasta normalizarse a cero.


# COMANDOS PARA EJECUTAR EL SISTEMA:

**Arrancar el sistema completo:**

  docker compose up --build
  *(Nota: Se puede añadir -d al final si se prefiere ejecutar en segundo plano para no bloquear la terminal).*

**Ver los logs en tiempo real (si se arrancó con -d):**
    
  docker compose logs -f ingestion/api/simulators/influxdb/mosquitto (elegir una/varias de estas opciones)

**Apagar el sistema conservando el historial de datos:**

  docker compose down

**Apagar el sistema y BORRAR el historial:**

  docker compose down -v
  *(Advertencia: Al añadir la bandera -v, se destruyen los volúmenes persistentes de InfluxDB y Mosquitto. Ideal para probar el sistema desde cero).*

# ACCESOS A LOS SERVICIOS:

Una vez que el sistema esté arrancado con Docker (docker compose up), puedes acceder a las distintas interfaces y herramientas desde tu navegador a través de los siguientes enlaces:

* INTERFAZ DE USUARIO Y API
  **Dashboard del Supermercado (Control Central):**
      * URL: http://localhost:5000
      * Uso: Interfaz web para consultar el historial (REST) y recibir alertas en tiempo real (WebSockets).
    
  **Documentación Interactiva de la API (Swagger UI):**
      * URL: http://localhost:5000/docs
      * Seguridad: Para probar los endpoints, pulsa en "Authorize" e introduce la clave: mi-clave-secreta-2026.

* Infraestructura y Datos
  **Panel de Grafana (Visualización Avanzada):**
      * **URL:** http://localhost:3000
      * **Usuario:** `admin`
      * **Contraseña:** `admin` 
      * **Uso:** Creación de dashboards personalizados conectados a InfluxDB.
  **Panel de InfluxDB (Base de Datos TSDB):**
      * URL: http://localhost:8086
      * Usuario: admin
      * Contraseña: pic2026pass
      * Token: mi-token-secreto

  **Broker MQTT (Mosquitto):**
      * Host: localhost
      * Puerto TCP: 1883 (Para clientes como MQTT Explorer o sensores físicos)
      * Puerto WebSockets: 9001 (Usado internamente por el Dashboard web)

# PASOS PARA CONECTAR INFLUX A GRAFANA E IMPORTAR EL DASHBOARD:


1. Entrar en Grafana desde el navegador: http://localhost:3000. (El usuario y contraseña por defecto la primera vez es admin / admin).

2. En el menú lateral izquierdo, ir a Connections > Data Sources.

3. Hacer clic en el botón azul Add data source.

4. Buscar y seleccionar InfluxDB.

5. En el campo desplegable llamado Query Language, seleccionar Flux. (Este paso es vital, si lo dejan en InfluxQL no funcionará el código de las consultas).

6. En el bloque de HTTP URL, escribir exactamente esto: http://influxdb:8086.

7. Desactivar el interruptor de Basic Auth si está encendido.

8. Bajar hasta el final de la página a la sección InfluxDB Details y rellenar estos tres campos exactos:

9. Organization: esei

10. Token: supermercado-token-2026

11. Default Bucket: iot_data

12. Hacer clic en el botón Save & Test.

13. Volver al menú de Grafana, darle a dashboards -> new -> import.

14. Importar el json de la carpeta api "GRAFANA DASHBOARD SUPERMERCADO-1775404370236.json"

15. Para los 4 gráficos, es necesario darle a los 3 puntitos darle a editar y luego volver, para que se actualicen correctamente.

## DISEÑO DE LA ARQUITECTURA MQTT (Componente C2)

Para este proyecto, hemos diseñado una jerarquía de tópicos estructurada y justificada de la siguiente manera:

* **Estructura base:** `supermarket/{zona}/{device_id}/{tipo_mensaje}`
* **Ejemplos:**
  * `supermarket/carniceria/temp-fridge-01/telemetry` (Datos individuales del sensor)
  * `supermarket/alerts/temp-fridge-01` (Alertas generadas por la ingesta)
  * `supermarket/status/simulador` (Estado global del sistema de simulación)
  * `supermarket/comandos/simulador` (Recepción de órdenes centralizadas)

**JUSTIFICACIÓN DEL DISEÑO**
1. Escalabilidad por Zonas: Al incluir la {zona} (carnicería, cajas, frutería) al principio de la jerarquía, permitimos que un 
suscriptor pueda escuchar únicamente lo que ocurre en una sección específica usando el comodín supermarket/carniceria/#, reduciendo 
el tráfico innecesario en el cliente.

2. Segregación de Flujos: Separamos la telemetry de las alerts. Esto permite que el Dashboard de tiempo real sea eficiente, 
ya que puede estar suscrito solo al tópico de alertas (supermarket/alerts/+) para reaccionar inmediatamente a emergencias sin 
tener que procesar todos los mensajes de telemetría de todos los sensores.

3. Facilidad de Filtrado: La estructura permite usar niveles de abstracción claros. El servicio de ingesta utiliza 
supermarket/+/+/telemetry para capturar todos los datos de sensores de forma global, independientemente de la zona o el ID, 
facilitando la expansión del supermercado con nuevos dispositivos sin cambiar una sola línea de código en el backend.

4. Control Individualizado: Al finalizar el tópico con /commands, garantizamos que cada dispositivo tenga su propio buzón de entrada 
privado, evitando que una orden de "cambiar intervalo" enviada a la carnicería afecte por error a los sensores de la zona de cajas.

## PIPELINE DE INGESTA Y ALMACENAMIENTO (Componente C3)

Nuestro servicio de ingesta (`ingestion_service.py`) implementa un procesamiento de flujo de datos en tiempo real (*streaming*) basado en capas:

1. Procesamiento en Tránsito (Streaming)
  * **Validación y Filtrado (Capa 1):** El sistema descarta JSON malformados o con campos ausentes. Además, aplica un filtro inteligente que ignora 
  las lecturas de error (`-999.0`) reportadas durante fallos de hardware, garantizando la integridad matemática de las métricas.
  * **Ventana Deslizante Dinámica (Capa 2):** Implementamos un algoritmo basado en colas de memoria (`deque`) que procesa los datos en tiempo real 
  considerando la marca temporal (timestamp) estricta. Cada dispositivo tiene una ventana personalizada (ej. 30s para temperatura, 60s para gases) 
  sobre la cual calcula su Media Móvil.
  * **Detección de Eventos (Capa 3):** Si la Media Móvil supera el umbral crítico definido en el `DEVICE_CONFIG` (ej. >7.0°C en carnicería o >800ppm
  de CO2), el sistema emite instantáneamente un aviso al tópico MQTT `supermarket/alerts/{device_id}`.

2. Almacenamiento y Persistencia
  * **Base de Datos TSDB (Capa 4):** Seleccionamos **InfluxDB**. Guardamos los datos estructurados en "tags" (device_id, type) para indexación rápida, 
  y "fields" (value, humidity).
  * **Políticas de Retención Automática ("Zero-Touch"):** A diferencia de configuraciones manuales, delegamos la retención de datos en la orquestación 
  de la infraestructura. El archivo `compose.yaml` inyecta la regla `DOCKER_INFLUXDB_INIT_RETENTION=30d`, garantizando que la base de datos se autopurgue 
  pasados 30 días, evitando que el disco se llene sin requerir intervención humana.

# BONUS B1: Thing Description (WoT)

**¿Qué es un Thing Description (TD)?**
Es un documento estandarizado en formato JSON-LD, promovido por el estándar Web of Things (WoT) del W3C. Actúa como el pasaporte digital de un dispositivo 
IoT, describiendo de forma estructurada sus capacidades, metadatos, y las interfaces de red disponibles.

**¿Por qué es útil para la interoperabilidad?**
En un entorno real, un supermercado podría tener cámaras frigoríficas de múltiples fabricantes, cada una con su propio formato de datos y protocolos. El TD 
soluciona esta fragmentación al ofrecer una capa de descripción uniforme. Permite que cualquier aplicación de terceros o agente externo entienda automáticamente 
qué datos ofrece el dispositivo y cómo conectarse a él, eliminando la necesidad de leer el código fuente o depender de integraciones manuales ad-hoc.

**Uso en nuestro Supermercado Inteligente:**
Hemos generado el TD para nuestro sensor temp-fridge-01 (Cámara de la Carnicería). Siguiendo las recomendaciones de diseño WoT, el documento expone dos propiedades 
físicas directas del dispositivo: la temperature y la humidity, ambas accesibles suscribiéndose a su tópico de telemetría MQTT. Además, hemos definido una acción 
(setInterval) que indica cómo un sistema externo puede publicar en el tópico de comandos del sensor para modificar su frecuencia de medición en vivo. Así, cualquier 
auditor sabría exactamente qué información ofrece nuestro hardware y cómo interactuar con él de forma estandarizada.

# BONUS B2: Análisis de Consumo de Hardware

| Dispositivo                      | Chip ref.         | Consumo activo | Consumo sleep |Duty cycle| Frec.envío| Autonomía est.|
| :---                             | :---              | :---           | :---          | :---     | :---      | :---          |
| **Cámara Carnicería** (Temp/Hum) | ESP32 + DHT22     | 160 mA         | 10 µA         | ~0.1%    | 1 msg/30s | **~520 días** |
| **Zona Cajas** (CO2)             | ESP32 + MH-Z19B   | 220 mA         | 10 µA         | ~5.0%    | 1 msg/10s | **~75 días**  |
| **Frutería** (Gas Etileno)       | ESP32 + ZE03-C2H4 | 165 mA         | 10 µA         | ~1.0%    | 1 msg/60s | **~240 días** |

**Justificación de los cálculos y decisiones de diseño:**
Para esta estimación teórica hemos tomado como referencia el uso de microcontroladores ESP32 alimentados por una batería LiPo estándar de 3.7V y 2000mAh.

* El **sensor de la cámara frigorífica** pasa el 99.9% del tiempo en modo *deep sleep* para ahorrar energía, despertando únicamente unos milisegundos para leer y enviar 
por MQTT. Esto le otorga una vida útil excelente de más de un año y medio.
* El **sensor de Etileno de la frutería** utiliza un módulo electroquímico (ZE03) de bajo consumo, pero requiere estar activo un poco más de tiempo para que el gas 
estabilice la lectura. Aun así, midiendo cada minuto, la batería durará unos 8 meses, lo cual es aceptable para ciclos de mantenimiento.
* El **sensor de calidad del aire (CO2)** en las cajas utiliza un sensor óptico NDIR (MH-Z19B) que requiere "calentar" una pequeña lámpara infrarroja, siendo muy exigente 
energéticamente. Para detectar aglomeraciones rápidas envía datos cada 10s, lo que eleva su *duty cycle* al 5% y hunde su autonomía a unos dos meses. En un despliegue real 
en el supermercado, **nuestra decisión técnica sería conectar este dispositivo directamente a la red eléctrica del techo** para evitar cambiar la batería constantemente.

*(Nota sobre la simulación: Para la demostración técnica de la práctica y para poder validar las ventanas deslizantes (C3) rápidamente, los simuladores en Python están configurados para enviar datos cada 5-10 segundos. Sin embargo, este análisis B2 refleja los intervalos reales que programaríamos en el firmware físico para maximizar la eficiencia energética).*

## BONUS B3: Ejecución con Docker

1. Para levantar todo el sistema:
   ```bash
   docker compose up --build

2. Puertos Expuestos
| Puerto   | Servicio               | Uso                                                              |
| :---     | :---                   | :---                                                             |
| **1883** | Mosquitto (MQTT)       | Conexión de sensores para envío de telemetría y comandos         |
| **9001** | Mosquitto (WebSockets) | Conexión directa del Dashboard para recibir datos en tiempo real |
| **8086** | InfluxDB               | Base de datos (TSDB) y acceso a su panel de control nativo       |
| **5000** | API REST / Dashboard   | Acceso a la interfaz gráfica web y a los endpoints de consulta   |
| **3000** | Grafana                | Acceso al panel avanzado de visualización de métricas            |

3. Variables de Entorno (Configuración del sistema)
El archivo `compose.yaml` inyecta automáticamente las siguientes variables de entorno para conectar los contenedores entre sí usando resolución de nombres de Docker, sin necesidad de IPs fijas:

| Variable        | Servicio(s)               | Descripción                                                             |
| :---            | :---                      | :---                                                                    |
| `MQTT_BROKER`   | `simulators`, `ingestion` | Apunta al hostname del contenedor Mosquitto (`mosquitto`).              |
| `INFLUX_URL`    | `ingestion`, `api`        | URL interna de la base de datos (`http://influxdb:8086`).               |
| `INFLUX_TOKEN`  | `ingestion`, `api`        | Token de seguridad para escribir/leer en InfluxDB (`mi-token-secreto`). |
| `INFLUX_ORG`    | `ingestion`, `api`        | Organización de la base de datos (`esei`).                              |
| `INFLUX_BUCKET` | `ingestion`, `api`        | Nombre del bucket donde se guarda la telemetría (`iot_data`).           |

*(Nota: Además, el servicio de InfluxDB utiliza sus variables nativas `DOCKER_INFLUXDB_INIT_*` en el compose para auto-configurar el usuario admin, la contraseña y el bucket en su primer arranque, garantizando un despliegue total sin intervención manual).*

## Consideraciones de Seguridad y Trabajo Futuro

Para facilitar el despliegue local y la evaluación ágil de esta práctica, el broker MQTT (Mosquitto) está configurado temporalmente con `allow_anonymous true`. 

Sin embargo, somos plenamente conscientes de que en un entorno de producción real, esto representaría una vulnerabilidad crítica (permitiendo inyección de comandos no autorizados o denegación de servicio). El siguiente paso lógico para llevar este sistema a producción sería:
1. Desactivar el acceso anónimo en `mosquitto.conf`.
2. Implementar listas de control de acceso (ACLs) y un archivo de contraseñas (`mosquitto_passwd`).
3. Actualizar los clientes (Simuladores, Ingesta y Dashboard) para inyectar credenciales mediante variables de entorno seguras (`client.username_pw_set()`).
4. Habilitar TLS (MQTTS en el puerto 8883) para encriptar la telemetría y evitar ataques de *Man-in-the-Middle*.