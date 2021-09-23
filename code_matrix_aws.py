import time
import json
import board
import microcontroller
import busio
from digitalio import DigitalInOut
import displayio
import framebufferio
import rgbmatrix
import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_minimqtt.adafruit_minimqtt as MQTT
#from adafruit_io.adafruit_io import IO_MQTT
from adafruit_aws_iot import MQTT_CLIENT

from secrets import secrets

# Get device certificate
try:
    with open("aws/aws_cert_matrix.pem.crt", "rb") as f:
        DEVICE_CERT = f.read()
except ImportError:
    print("Certificate (aws_cert_matrix.pem.crt) not found on CIRCUITPY filesystem.")
    raise

# Get device private key
try:
    with open("aws/private_matrix.pem.key", "rb") as f:
        DEVICE_KEY = f.read()
except ImportError:
    print("Key (private_matrix.pem.key) not found on CIRCUITPY filesystem.")
    raise

# Matrix Display
WIDTH = 64
HEIGHT = 32
BLACK = 0x000000
WHITE = 0x505050
WHITE_DIM = 0x1a1a1a
RED = 0xFF0000
RED_DIM = 0x100000
GREEN_DIM = 0x001010
BLUE_DIM = 0x000010

shadow_topic = "$aws/things/{}/shadow".format(secrets["client_id_matrix"])

deco_font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")

print("ONAIR display with MatrixPortal")

displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64, bit_depth=4,
    rgb_pins=[
        board.MTX_R1,
        board.MTX_G1,
        board.MTX_B1,
        board.MTX_R2,
        board.MTX_G2,
        board.MTX_B2
    ],
    addr_pins=[
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE
)
display = framebufferio.FramebufferDisplay(matrix)

splash = displayio.Group(max_size=10)

group_on = displayio.Group()
splash.append(group_on)
group_on.hidden = True
group_off = displayio.Group()
splash.append(group_off)

rect_on = Rect(0, 0, WIDTH, 2*HEIGHT//3, fill=RED_DIM, outline=WHITE)
group_on.append(rect_on)

label_onair = Label(deco_font, text="ON AIR", color=WHITE)
label_onair.scale=1
label_onair.anchor_point = (0.5, 0.5)
label_onair.anchored_position = (WIDTH//2, HEIGHT//4+2)
group_on.append(label_onair)

rect_off = Rect(0, 0, WIDTH, 2*HEIGHT//3, fill=BLACK)
group_off.append(rect_off)

label_off = Label(deco_font, text="GOOD", color=GREEN_DIM)
label_off.scale=1
label_off.anchor_point = (0.5, 0.5)
label_off.anchored_position = (WIDTH//2, HEIGHT//4+2)
group_off.append(label_off)

label_time = Label(terminalio.FONT, text="13:30", color=WHITE_DIM)
label_time.anchor_point = (0.5, 0.5)
label_time.anchored_position = (WIDTH//2, 3*(HEIGHT//4)+1)
splash.append(label_time)
label_time.text = ""

rect_status = Rect(63,31,1,1,fill=RED_DIM)
splash.append(rect_status)

def turn_on():
    group_on.hidden = False
    group_off.hidden = True
    label_time.text = "13:30"

def turn_off():
    group_on.hidden = True
    group_off.hidden = False
    label_time.text = ""

display.show(splash)

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.2
)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Set AWS Device Certificate
esp.set_certificate(DEVICE_CERT)

# Set AWS RSA Private Key
esp.set_private_key(DEVICE_KEY)

def connected(client, userdata, flags, rc):
    # Connected function will be called when the client is connected to Adafruit IO.
    print('Connected to AWS IoT!')
    print('Flags: {0}\nRC: {1}'.format(flags, rc))
    rect_status.fill = BLUE_DIM

    print("Subscribing to matrix shadow update delta...")
    #aws_iot.shadow_subscribe()
    aws_iot.subscribe(shadow_topic + "/update/delta")

    print("Subscribing to matrix shadow get...")
    #aws_iot.shadow_get_subscribe()  
    aws_iot.subscribe(shadow_topic + "/get/accepted")

    print("Publish matrix shadow get")
    #aws_iot.shadow_get()
    aws_iot.publish(shadow_topic + "/get", "{}")

def subscribed(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))
    rect_status.fill = WHITE_DIM

def unsubscribed(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a topic.
    print('Unsubscribed from {0} with PID {1}'.format(topic, pid))

def disconnected(client, userdata, rc):
    # Disconnected function will be called when the client disconnects.
    print('Disconnected from AWS IoT!')
    rect_status.fill = GREEN_DIM

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
        {"state":{
            "desired":{"onair":"ON","text":"."},
            "reported":{"onair":"OFF","text":"."},
            "delta":{"onair":"ON"}},
            "metadata":{"desired":{"onair":{"timestamp":1629007360},"text":{"timestamp":1629007360}},"reported":{"onair":{"timestamp":1629004179},"text":{"timestamp":1629004179}}},"version":25,"timestamp":1629007611}        
        """
        payload=json.loads(msg)
        print("get accepted state desired is ")
        print(payload["state"]["desired"])
        handle_delta(payload["state"]["desired"])
    elif topic == shadow_topic + "/update/delta":
        """
        Message from $aws/things/on_air_sign_matrix/shadow/update/delta: 
        {"version":11,
            "timestamp":1628996348,
            "state":{
                "temp":"-1",
                "moisture":"93.4033",
                "onair":"ON",
                "text":"."},
            "metadata":{"temp":{"timestamp":1628948687},"moisture":{"timestamp":1628948687},"onair":{"timestamp":1628996348},"text":{"timestamp":1628996348}}}
        """
        payload=json.loads(msg)
        print("update delta state is")
        print(payload["state"])
        handle_delta(payload["state"])

def update_onair(message):
    if message == "ON":
        group_on.hidden = False
        group_off.hidden = True
    elif message == "OFF":
        group_on.hidden = True
        group_off.hidden = False
        #label_time.text = ""
    else:
        print("Unexpected message on LED feed.")

def update_text(message):
    if message == ".":
        label_time.text = ""
    else:
        label_time.text = message

def handle_delta(delta):
    print("handle_delta")
    print(delta)
    reported = {}
    delta_onair = delta.get("onair")
    if delta_onair:
        update_onair(delta_onair)
        reported["onair"] = delta_onair
    delta_text = delta.get("text")
    if delta_text:
        update_text(delta_text)
        reported["text"] = delta_text
    if reported:
        payload = {"state": {"reported":reported}}
        print("publish to /update: ")
        print(payload)
        aws_iot.publish(shadow_topic + "/update", json.dumps(payload))

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")
rect_status.fill = GREEN_DIM

# Initialize MQTT interface with the esp interface
MQTT.set_socket(socket, esp)
client =  MQTT.MQTT(
    broker = secrets['broker'],
    client_id = secrets['client_id_matrix'])

aws_iot = MQTT_CLIENT(client)
aws_iot.on_connect = connected
aws_iot.on_disconnect = disconnected
aws_iot.on_subscribe = subscribed
aws_iot.on_unsubscribe = unsubscribed
aws_iot.on_publish = published
aws_iot.on_message = message


#io.add_feed_callback(FEED_ONAIR, on_matrix_onair)
#io.add_feed_callback(FEED_TEXT, on_matrix_text)

print('Attempting to connect to %s'%client.broker)
aws_iot.connect()
# Subscribe to all messages on the led feed
#aws_iot.subscribe(FEED_ONAIR)
#aws_iot.subscribe(FEED_TEXT)

while True:
    try:
        #aws_iot.loop()
        aws_iot.client.loop(0.1)
    except (ValueError, RuntimeError, MQTT.MMQTTException, AttributeError) as e:
        print("Failed to get data, retrying\n", e)
        try:
            print("wifi.reset")
            wifi.reset()
            print("wifi.connect")
            wifi.connect()
            print("aws_iot.reconnect()")
            aws_iot.reconnect()
            """
            Still network error... keep trying.
            ESP32 not responding
            Failed to get data, retrying
            MiniMQTT is not connected.
            wifi.reset
            wifi.connect
            aws_iot.reconnect()
            Still network error... keep trying.
            ESP32 not responding
            Failed to get data, retrying
            MiniMQTT is not connected.
            wifi.reset
            wifi.connect
            aws_iot.reconnect()
            Still network error... keep trying.
            ESP32 not responding
            Failed to get data, retrying
            MiniMQTT is not connected.
            wifi.reset
            wifi.connect
            aws_iot.reconnect()
            """
        except Exception as e:
            print("Still network error... Going to reset.")
            print(e)
            microcontroller.reset() 
        continue

