import time
import os
import board
import digitalio
import wifi
import socketpool
import busio
import adafruit_ahtx0
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# ----------------- USER CONFIG ------------------
PIR_PIN = board.IO1      
RELAY_PIN = board.IO2  
SCL_PIN = board.IO9        
SDA_PIN = board.IO8    
MOTION_TIMEOUT = 3        # Seconds, how long to keep the relay on after motion
USE_MQTT = True

OUTLET_STATE_TOPIC = "foxyhamster/feeds/outlet-state"   
OUTLET_COMMAND_TOPIC = "foxyhamster/feeds/outlet-set"
# -----------------------------------------------

# ---- Hardware setup ----
i2c = busio.I2C(scl=SCL_PIN, sda=SDA_PIN)
sensor = adafruit_ahtx0.AHTx0(i2c)

pir = digitalio.DigitalInOut(PIR_PIN)
pir.direction = digitalio.Direction.INPUT

relay = digitalio.DigitalInOut(RELAY_PIN)
relay.direction = digitalio.Direction.OUTPUT
relay.value = False

last_motion_time = None

# ---- MQTT Setup ----
def connect(client, userdata, flags, rc):
    print("Connected to MQTT broker!")
    client.subscribe(OUTLET_COMMAND_TOPIC)

def message(client, topic, msg):
    print(f"Received on {topic}: {msg}")
    if topic == OUTLET_COMMAND_TOPIC:
        set_relay(msg == "ON")

def set_relay(state):
    global last_motion_time
    relay.value = state
    if state:
        last_motion_time = time.monotonic()
    else:
        last_motion_time = time.monotonic() - MOTION_TIMEOUT
    if USE_MQTT:
        mqtt_client.publish(OUTLET_STATE_TOPIC, "on" if state else "off")
        print("Published:", "on" if state else "off")

# ---- Wi-Fi & MQTT Connect ----
print("Connecting to Wi-Fi...")
print("WIFI_SSID:", os.getenv("WIFI_SSID"))
wifi.radio.connect(os.getenv("WIFI_SSID"))
#wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
print("Connected! IP:", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
mqtt_client = MQTT.MQTT(
    broker=os.getenv("MQTT_BROKER"),
    port=int(os.getenv("MQTT_PORT")),
    username=os.getenv("MQTT_USERNAME"),
    password=os.getenv("MQTT_PASSWORD"),
    socket_pool=pool,
    ssl_context=None,   # Adafruit IO is non-SSL by default
)
mqtt_client.on_connect = connect
mqtt_client.on_message = message
mqtt_client.connect()

set_relay(False)

# ---- Main loop ----
while True:
    temperature = sensor.temperature
    humidity = sensor.relative_humidity
    print(f"Temperature: {temperature:.1f} C, Humidity: {humidity:.1f}%")

    if temperature > 28 and humidity > 80:
        if not relay.value:
            print("Auto: turning ON relay (temp/humidity high)")
            set_relay(True)
    else:
        if relay.value:
            print("Auto: turning OFF relay (below threshold)")
            set_relay(False)

    # # Motion detected
    # if pir.value:
    #     last_motion_time = time.monotonic()
    #     if not relay.value:
    #         set_relay(True)

    # # Timeout logic
    # if relay.value and last_motion_time is not None:
    #     if time.monotonic() > last_motion_time + MOTION_TIMEOUT:
    #         print("Motion timeout, turning off relay.")
    #         set_relay(False)

    # Check for MQTT messages
    mqtt_client.loop()
    time.sleep(2)
