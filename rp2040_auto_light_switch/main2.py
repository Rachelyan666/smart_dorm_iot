import time
import os
import board
import digitalio
import pwmio
import wifi
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_motor import servo

# ----------------- USER CONFIG ------------------
LED_PIN = board.LED        # Use the onboard LED, or change to your GPIO (e.g., board.GP15)
SERVO_PIN = board.GP0      # Change if your servo is on another pin

LIGHT_SET_TOPIC = "foxyhamster/feeds/light-set"
LIGHT_STATE_TOPIC = "yourusername/feeds/light-state"
# -----------------------------------------------

# ---- Hardware setup ----
led = digitalio.DigitalInOut(LED_PIN)
led.direction = digitalio.Direction.OUTPUT

pwm = pwmio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
my_servo = servo.Servo(pwm)

# ---- Wi-Fi & MQTT Setup ----
print("Connecting to Wi-Fi...")
wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
print("Connected! IP:", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
mqtt_client = MQTT.MQTT(
    broker=os.getenv("MQTT_BROKER"),
    port=int(os.getenv("MQTT_PORT")),
    username=os.getenv("MQTT_USERNAME"),
    password=os.getenv("MQTT_PASSWORD"),
    socket_pool=pool,
)
state = "OFF"

def on_message(client, topic, msg):
    global state
    print("Received on", topic, ":", msg)
    if topic == LIGHT_SET_TOPIC:
        if msg == "ON":
            led.value = True
            my_servo.angle = 5     # Adjust angle for "ON"
            state = "ON"
            mqtt_client.publish(LIGHT_STATE_TOPIC, "ON")
        elif msg == "OFF":
            led.value = False
            my_servo.angle = 90    # Adjust angle for "OFF"
            state = "OFF"
            mqtt_client.publish(LIGHT_STATE_TOPIC, "OFF")

mqtt_client.on_message = on_message
mqtt_client.connect()
mqtt_client.subscribe(LIGHT_SET_TOPIC)
print("Subscribed to", LIGHT_SET_TOPIC)

# ---- Main Loop ----
mqtt_client.publish(LIGHT_STATE_TOPIC, "OFF")  # Initial state

while True:
    mqtt_client.loop()
    time.sleep(0.1)
