def reference():
    pass
    # Raspberry Pi Pico RP2040
    #dir(board)
    #['__class__', 'A0', 'A1', 'A2', 'A3', 'GP0', 'GP1', 'GP10', 'GP11', 'GP12', 'GP13',
    #'GP14', 'GP15', 'GP16', 'GP17', 'GP18', 'GP19', 'GP2', 'GP20', 'GP21', 'GP22', 'GP23',
    #'GP24', 'GP25', 'GP26', 'GP26_A0', 'GP27', 'GP27_A1', 'GP28', 'GP28_A2', 'GP3', 'GP4',
    #'GP5', 'GP6', 'GP7', 'GP8', 'GP9', 'LED', 'SMPS_MODE', 'VBUS_SENSE', 'VOLTAGE_MONITOR']

    # ON_AIR_controller v1.0
    # GP12: red button
    # GP13: white button
    # GP17: Rotary Encoder A
    # GP16: Rotary Encoder B
    # GP15: Rotary Encoder LED Red
    # GP14: Rotary Encoder LED Green
    # GP18: Rotary Encoder LED Blue
    # GP19: Rotary Encoder Switch
    # GP2: AirLift SCK
    # GP3: AIrLift MOSI
    # GP4: AirLift MISO
    # GP5: AirLift CS
    # GP6: AirLift BUSY
    # GP7: AirLift !RST
    # GP8: neopixel
    # GP10: SDA
    # GP11: SCL
    # I2C SSD1306 OLED 128x64 display address 0x3c

    #>>> help("modules")
    #__main__          board             microcontroller   storage
    #_bleio            builtins          micropython       struct
    #_eve              busio             msgpack           supervisor
    #_pixelbuf         collections       neopixel_write    sys
    #adafruit_bus_device                 countio           os                terminalio
    #analogio          digitalio         pulseio           time
    #array             displayio         pwmio             touchio
    #audiobusio        errno             random            ulab
    #audiocore         fontio            re                usb_hid
    #audiomp3          framebufferio     rgbmatrix         usb_midi
    #audiopwmio        gamepad           rotaryio          vectorio
    #binascii          gc                rp2pio            watchdog
    #bitbangio         io                rtc
    #bitmaptools       json              sdcardio
    #bitops            math              sharpdisplay
    #Plus any modules on the filesystem

import time
import json
import board
import rtc
import digitalio
from digitalio import DigitalInOut
from adafruit_debouncer import Debouncer
import rotaryio
import busio
from adafruit_datetime import datetime, timedelta
import displayio
import adafruit_displayio_ssd1306
import terminalio
from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.line import Line
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
#import adafruit_requests as requests
import adafruit_minimqtt.adafruit_minimqtt as MQTT
#from adafruit_io.adafruit_io import IO_MQTT
from adafruit_aws_iot import MQTT_CLIENT

from secrets import secrets

# Get device certificate
try:
    with open("aws/aws_cert_controller.pem.crt", "rb") as f:
        DEVICE_CERT = f.read()
except ImportError:
    print("Certificate (aws_cert_controller.pem.crt) not found on CIRCUITPY filesystem.")
    raise

# Get device private key
try:
    with open("aws/private_controller.pem.key", "rb") as f:
        DEVICE_KEY = f.read()
except ImportError:
    print("Key (private_controller.pem.key) not found on CIRCUITPY filesystem.")
    raise

# OLED Display
WIDTH = 128
HEIGHT = 64
BORDER = 5
BLACK = 0x000000
WHITE = 0xFFFFFF

shadow_topic = "$aws/things/{}/shadow".format(secrets["client_id_matrix"])
tz_offset=9 * 60 * 60 # Time zone offset from UTC in seconds

print("ONAIR display controller")

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Rotary Encoder
encoder = rotaryio.IncrementalEncoder(board.GP16, board.GP17)
led_red = digitalio.DigitalInOut(board.GP15)
led_red.direction = digitalio.Direction.OUTPUT
led_red.value = True # OFF
led_green = digitalio.DigitalInOut(board.GP14)
led_green.direction = digitalio.Direction.OUTPUT
led_green.value = True # OFF
led_blue = digitalio.DigitalInOut(board.GP18)
led_blue.direction = digitalio.Direction.OUTPUT
led_blue.value = True # OFF
btnRotaryPin = digitalio.DigitalInOut(board.GP19)
btnRotaryPin.direction = digitalio.Direction.INPUT
btnRotaryPin.pull = digitalio.Pull.UP
#btnRotary = Debouncer(btnRotaryPin, interval=0.1)
btnRotary = Debouncer(btnRotaryPin)

btnRedPin = digitalio.DigitalInOut(board.GP12)
btnRedPin.direction = digitalio.Direction.INPUT
btnRedPin.pull = digitalio.Pull.UP
btnRed = Debouncer(btnRedPin)

btnWhitePin = digitalio.DigitalInOut(board.GP13)
btnWhitePin.direction = digitalio.Direction.INPUT
btnWhitePin.pull = digitalio.Pull.UP
btnWhite = Debouncer(btnWhitePin)

displayio.release_displays()
i2c = busio.I2C(board.GP11, board.GP10)
display_bus = displayio.I2CDisplay(i2c, device_address=0x3c)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

splash = displayio.Group(max_size=10)

group_on = displayio.Group()
splash.append(group_on)
group_on.hidden = True
group_off = displayio.Group()
splash.append(group_off)
group_status = displayio.Group()
group_status.x = WIDTH-6
group_status.y = HEIGHT-2
splash.append(group_status)

rect_on = Rect(0, 0, WIDTH, HEIGHT//2, fill=WHITE)
group_on.append(rect_on)

label_onair = Label(terminalio.FONT, text="ON AIR", color=BLACK)
label_onair.scale=2
label_onair.anchor_point = (0.5, 0.5)
label_onair.anchored_position = (WIDTH//2, HEIGHT//4)
group_on.append(label_onair)

rect_off = Rect(0, 0, WIDTH, HEIGHT//2, fill=BLACK)
group_off.append(rect_off)

label_off = Label(terminalio.FONT, text="GOOD", color=WHITE)
label_off.scale=2
label_off.anchor_point = (0.5, 0.5)
label_off.anchored_position = (WIDTH//2, HEIGHT//4)
group_off.append(label_off)

label_time = Label(terminalio.FONT, text="13:30", color=WHITE)
label_time.scale=2
label_time.anchor_point = (0.5, 0.5)
label_time.anchored_position = (WIDTH//4, 3*(HEIGHT//4))
splash.append(label_time)
label_time.text = ""

line_time = Line(2,HEIGHT-2, WIDTH//2-2, HEIGHT-2, color=WHITE)
splash.append(line_time)

label_time_feed = Label(terminalio.FONT, text="13:30", color=WHITE)
label_time_feed.scale=2
label_time_feed.anchor_point = (0.5, 0.5)
label_time_feed.anchored_position = (3*WIDTH//4, 3*(HEIGHT//4))
splash.append(label_time_feed)
label_time_feed.text = ""

rect_status = Rect(0,0,5,5,fill=WHITE)
group_status.append(rect_status)

def turn_on():
    group_on.hidden = False
    group_off.hidden = True
    label_time.text = "13:30"

def turn_off():
    group_on.hidden = True
    group_off.hidden = False
    label_time.text = ""

display.show(splash)

esp32_cs = DigitalInOut(board.GP5)
esp32_ready = DigitalInOut(board.GP6)
esp32_reset = DigitalInOut(board.GP7)
spi = busio.SPI(board.GP2, board.GP3, board.GP4)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
# esp._debug = True
status_light = neopixel.NeoPixel(board.GP8, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)
#requests.set_socket(socket, esp)

# Set AWS Device Certificate
esp.set_certificate(DEVICE_CERT)

# Set AWS RSA Private Key
esp.set_private_key(DEVICE_KEY)

def connected(client, userdata, flags, rc):
    # Connected function will be called when the client is connected to Adafruit IO.
    print('Connected to AWS IoT!')
    print('Flags: {0}\nRC: {1}'.format(flags, rc))
    group_status.y -= 1

    print("Subscribing to matrix shadow update accepted...")
    #aws_iot.shadow_subscribe()
    aws_iot.subscribe(shadow_topic + "/update/accepted")

    print("Subscribing to matrix shadow get...")
    #aws_iot.shadow_get_subscribe()  
    aws_iot.subscribe(shadow_topic + "/get/accepted")

    print("Publish matrix shadow get")
    #aws_iot.shadow_get()
    aws_iot.publish(shadow_topic + "/get", "{}")

def disconnected(client, userdata, rc):
    # This method is called when the client disconnects
    # from the broker.
    print('Disconnected from AWS IoT!')

def subscribed(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new topic.
    print('Subscribed to {0} with QOS level {1}'.format(topic, granted_qos))

def unsubscribed(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a topic.
    print('Unsubscribed from {0} with PID {1}'.format(topic, pid))

def published(client, userdata, topic, pid):
    # This method is called when the client publishes data to a topic.
    print('Published to {0} with PID {1}'.format(topic, pid))

def message(client, topic, msg):
    # This method is called when the client receives data from a topic.
    print("Message from {}: {}".format(topic, msg))
    """
    Message from $aws/things/on_air_sign_matrix/shadow/update/documents: {"previous":{"state":{"desired":{"welcome":"aws-iot","temp":"-1","moisture":"93.4033","onair":"ON","text":"."},"reported":{"welcome":"aws-iot"}},"metadata":{"desired":{"welcome":{"timestamp":1628934959},"temp":{"timestamp":1628948687},"moisture":{"timestamp":1628948687},"onair":{"timestamp":1628995475},"text":{"timestamp":1628995475}},"reported":{"welcome":{"timestamp":1628934959}}},"version":10},"current":{"state":{"desired":{"welcome":"aws-iot","temp":"-1","moisture":"93.4033","onair":"ON","text":"."},"reported":{"welcome":"aws-iot"}},"metadata":{"desired":{"welcome":{"timestamp":1628934959},"temp":{"timestamp":1628948687},"moisture":{"timestamp":1628948687},"onair":{"timestamp":1628996348},"text":{"timestamp":1628996348}},"reported":{"welcome":{"timestamp":1628934959}}},"version":11},"timestamp":1628996348}
    Message from $aws/things/on_air_sign_matrix/shadow/update/delta: {"version":11,"timestamp":1628996348,"state":{"temp":"-1","moisture":"93.4033","onair":"ON","text":"."},"metadata":{"temp":{"timestamp":1628948687},"moisture":{"timestamp":1628948687},"onair":{"timestamp":1628996348},"text":{"timestamp":1628996348}}}
    Message from $aws/things/on_air_sign_matrix/shadow/update/accepted: {"state":{"desired":{"onair":"ON","text":"."}},"metadata":{"desired":{"onair":{"timestamp":1628996348},"text":{"timestamp":1628996348}}},"version":11,"timestamp":1628996348}
    """
    if topic == shadow_topic + "/get/accepted":
        """
        Message from $aws/things/on_air_sign_matrix/shadow/get/accepted: 
        {"state":{"desired":{"welcome":"aws-iot",
                            "temp":"-1",
                            "moisture":"93.4033",
                            "onair":"ON","text":"."},
                        "reported":{"welcome":"aws-iot"},
                        "delta":{"temp":"-1","moisture":"93.4033","onair":"ON","text":"."}},
                        "metadata":{"desired":{"welcome":{"timestamp":1628934959},"temp":{"timestamp":1628948687},"moisture":{"timestamp":1628948687},"onair":{"timestamp":1628996348},"text":{"timestamp":1628996348}},"reported":{"welcome":{"timestamp":1628934959}}},"version":11,"timestamp":1629001301}
        """
        payload=json.loads(msg)
        print("get accepted state reported is ")
        print(payload["state"]["reported"])
        handle_reported(payload["state"]["reported"])
    elif topic == shadow_topic + "/update/accepted":
        """
        Message from $aws/things/on_air_sign_matrix/shadow/update/accepted: {"state":{"desired":{"onair":"ON","text":"."}},"metadata":{"desired":{"onair":{"timestamp":1628996348},"text":{"timestamp":1628996348}}},"version":11,"timestamp":1628996348}        
        """
        payload=json.loads(msg)
        print("update accepted state desired is")
        print(payload["state"].get("desired"))
        print("update accepted state reported is")
        print(payload["state"].get("reported"))
        if payload["state"].get("reported"):
            handle_reported(payload["state"]["reported"])

def update_onair(message):
    if message == "ON":
        led.value = True
        group_on.hidden = False
        group_off.hidden = True
    elif message == "OFF":
        led.value = False
        group_on.hidden = True
        group_off.hidden = False
    else:
        print("Unexpected message on onair.")

def update_text(message):
    if message == ".":
        label_time_feed.text = ""
    else:
        label_time_feed.text = message

def handle_reported(reported):
    reported_onair = reported.get("onair")
    if reported_onair:
        update_onair(reported_onair)
    reported_text = reported.get("text")
    if reported_text:
        update_text(reported_text)

def update_time_area_text(position):
    dt = datetime.now() + timedelta(minutes=10*position) + timedelta(hours=1)
    pp = "{:02d}:{:02d}".format(dt.hour, dt.minute//10*10)
    #print(pp)
    label_time.text = pp

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")
group_status.y -= 1

# Get time from NTP server and set system time
while True:
    # esp get_time fails in first few attemps
    try:
        now = esp.get_time()
    except ValueError as e:
        print(e)
        time.sleep(1)
    else:
        break
print(now)
now = time.localtime(now[0] + tz_offset)
print(now)
rtc.RTC().datetime = now
group_status.y -= 1

# Initialize MQTT interface with the esp interface
MQTT.set_socket(socket, esp)
client =  MQTT.MQTT(
    broker = secrets['broker'],
    client_id = secrets['client_id_controller'])

aws_iot = MQTT_CLIENT(client)
aws_iot.on_connect = connected
aws_iot.on_disconnect = disconnected
aws_iot.on_subscribe = subscribed
aws_iot.on_unsubscribe = unsubscribed
aws_iot.on_publish = published
aws_iot.on_message = message

#aws_iot.add_feed_callback(FEED_ONAIR, on_matrix_onair)
#aws_iot.add_feed_callback(FEED_TEXT, on_matrix_text)

print('Attempting to connect to %s'%client.broker)
aws_iot.connect()

# Subscribe to all messages on the led feed
#aws_iot.subscribe(FEED_ONAIR)
#aws_iot.subscribe(FEED_TEXT)

def loop():
    last_position = None
    while True:
        #print(time.monotonic())
        btnRotary.update()
        btnRed.update()
        btnWhite.update()
        position = encoder.position
        if last_position is None or position != last_position:
            update_time_area_text(position)
        last_position = position
        if btnRed.rose == True:
            print("btnRed is pressed")
            led_blue.value = False
            led_green.value = True
            encoder.position = 0
            position = 0
            last_position = 0
            update_time_area_text(position)
            payload = {"state":{"desired":{
                                    "onair":"ON",
                                    "text": "."}}}
            aws_iot.publish(secrets["matrix_update_topic"], json.dumps(payload))
            print("Published!")
        if btnWhite.rose == True:
            print("btnWhite is pressed")
            led_blue.value = True
            led_green.value = True
            payload = {"state":{"desired":{
                                    "onair":"OFF",
                                    "text": "."}}}
            aws_iot.publish(secrets["matrix_update_topic"], json.dumps(payload))
            print("Published!")
        if btnRotary.rose == True:
            print("btnRotary is pressed")
            #if group_on.hidden == False:
            led_green.value = False
            payload = {"state":{"desired":{
                                    "text": "~"+label_time.text}}}
            aws_iot.publish(secrets["matrix_update_topic"], json.dumps(payload))
            print("Published!")
        # Poll for incoming messages
        try:
            aws_iot.client.loop(0.1)
        except (ValueError, RuntimeError, MQTT.MMQTTException) as e:
            print("Failed to get data, retrying\n", e)
            try:
                print("wifi.reset")
                wifi.reset()
                print("wifi.connect")
                wifi.connect()
                print("aws_iot.recoonect")
                aws_iot.reconnect()
            except Exception as e:
                print("Still network error... keep trying.")
                print(e)
            continue

loop()
