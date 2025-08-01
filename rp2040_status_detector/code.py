import board
import digitalio
import time
import os
import wifi
import socketpool
import ipaddress
import ssl
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_requests

# ----------------- USER CONFIG ------------------
PIR_PIN = board.GP27   
OCCU_PIN = board.GP14
MAGNET_PIN = board.GP26      
DOOR_PIN = board.GP15   
USE_MQTT = True

OCCU_STATE_TOPIC = "foxyhamster/feeds/pir"   
DOOR_STATE_TOPIC = "foxyhamster/feeds/door"

TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"
JSON_QUOTES_URL = "https://www.adafruit.com/api/quotes.php"
# -----------------------------------------------

pir = digitalio.DigitalInOut(PIR_PIN)
pir.direction = digitalio.Direction.INPUT

door_sensor = digitalio.DigitalInOut(MAGNET_PIN)
door_sensor.direction = digitalio.Direction.INPUT
door_sensor.pull = digitalio.Pull.UP  # Most door sensors are "normally closed" to GND


led1 = digitalio.DigitalInOut(OCCU_PIN)
led1.direction = digitalio.Direction.OUTPUT

led2 = digitalio.DigitalInOut(DOOR_PIN)
led2.direction = digitalio.Direction.OUTPUT

# ---- Wi-Fi & MQTT Setup ----
print("Connecting to Wi-Fi...")
print("MAC address:", [hex(b) for b in wifi.radio.mac_address])
wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
print("Connected! IP:", wifi.radio.ipv4_address)

ping_ip = ipaddress.IPv4Address("8.8.8.8")
ping = wifi.radio.ping(ip=ping_ip)

# retry once if timed out
if ping is None:
    ping = wifi.radio.ping(ip=ping_ip)

if ping is None:
    print("Couldn't ping 'google.com' successfully")
else:
    # convert s to ms
    print(f"Pinging 'google.com' took: {ping * 1000} ms")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

print(f"Fetching text from {TEXT_URL}")
response = requests.get(TEXT_URL)
print("-" * 40)
print(response.text)
print("-" * 40)

print(f"Fetching json from {JSON_QUOTES_URL}")
response = requests.get(JSON_QUOTES_URL)
print("-" * 40)
print(response.json())
print("-" * 40)


pool = socketpool.SocketPool(wifi.radio)
mqtt_client = MQTT.MQTT(
    broker=os.getenv("MQTT_BROKER"),
    port=int(os.getenv("MQTT_PORT")),
    username=os.getenv("MQTT_USERNAME"),
    password=os.getenv("MQTT_PASSWORD"),
    socket_pool=pool,
)
mqtt_client.connect()

last_pir = None
last_door = None

#main

while True:
    if pir.value:
        led1.value = True     # Turn LED ON
        if last_pir != True:
            print("Motion detected!")
            mqtt_client.publish(OCCU_STATE_TOPIC, "yes")
        last_pir = True
    else:
        led1.value = False    # Turn LED OFF
        if last_pir != False:
            print("No motion.")
            mqtt_client.publish(OCCU_STATE_TOPIC, "no")
        last_pir = False

    if door_sensor.value:
        led2.value = True   # Door is open → LED ON
        if last_door != True:
            print("Door is OPEN.")
            mqtt_client.publish(DOOR_STATE_TOPIC, "OPEN")
        last_door = True
    else:
        led2.value = False  # Door is closed → LED OFF
        if last_door != False:
            print("Door is CLOSED.")
            mqtt_client.publish(DOOR_STATE_TOPIC, "CLOSED")
        last_door = False

    mqtt_client.loop()
    time.sleep(5)
    print("running")  # Added print statement to indicate the loop is running