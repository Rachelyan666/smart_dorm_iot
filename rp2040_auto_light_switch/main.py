import network
import socket
from time import sleep
from picozero import pico_temp_sensor, pico_led
import machine
import rp2
import sys
from servo import Servo

ssid1 = 'RedRover'
ssid2 = 'your-wifi'
password = 'your-pswd'
servo=Servo(pin=0)

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid2, password)
    while wlan.isconnected() == False:
        if rp2.bootsel_button() == 1:
            sys.exit()
        print('Waiting for connection...')
        pico_led.on()
        sleep(0.5)
        pico_led.off()
        sleep(0.5)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    pico_led.on()
    return ip




def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    return connection
    

def webpage(temperature, state):
    #Template HTML
    html = f"""
            <!DOCTYPE html>
            <html>
            <form action="./lighton">
            <input type="submit" value="Light on" />
            </form>
            <form action="./lightoff">
            <input type="submit" value="Light off" />
            </form>
            <form action="./close">
            <input type="submit" value="Stop server" />
            </form>
            <p>LED is {state}</p>
            <p>Temperature is {temperature}</p>
            </body>
            </html>
            """
    return str(html)
    
    
def serve(connection):
    #Start a web server
    state = 'ON'
    pico_led.on()
    temperature = 0
    while True:
        client = connection.accept()[0]
        request = client.recv(1024)
        request = str(request)
        try:
            request = request.split()[1]
        except IndexError:
            servo.stop()
            pass
        if request == '/lighton?':
            pico_led.on()
            servo.move(5)
            state = 'ON'
        elif request =='/lightoff?':
            pico_led.off()
            servo.move(90)
            state = 'OFF'
        elif request == '/close?':
            sys.exit()
        temperature = pico_temp_sensor.temp
        html = webpage(temperature, state)
        client.send(html)
        client.close()

ip = connect()
connection = open_socket(ip)
serve(connection)
