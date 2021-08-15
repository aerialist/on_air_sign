import time
import board
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
from adafruit_io.adafruit_io import IO_MQTT

from secrets import secrets

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

FEED_ONAIR = "matrix-onair"
FEED_TEXT = "matrix-text"

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

def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    print("Connected to Adafruit IO! ")
    rect_status.fill = BLUE_DIM

def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))
    rect_status.fill = WHITE_DIM

def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")
    rect_status.fill = GREEN_DIM

def on_matrix_onair(client, topic, message):
    # Method called whenever user/feeds/led has a new value
    print("New message on topic {0}: {1} ".format(topic, message))
    if message == "ON":
        group_on.hidden = False
        group_off.hidden = True
    elif message == "OFF":
        group_on.hidden = True
        group_off.hidden = False
        #label_time.text = ""
    else:
        print("Unexpected message on LED feed.")

def on_matrix_text(client, topic, message):
    # Method called whenever user/feeds/led has a new value
    print("New message on topic {0}: {1} ".format(topic, message))
    if message == ".":
        label_time.text = ""
    else:
        label_time.text = message

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")
rect_status.fill = GREEN_DIM

# Initialize MQTT interface with the esp interface
MQTT.set_socket(socket, esp)
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_password"],
)

io = IO_MQTT(mqtt_client)
io.on_connect = connected
io.on_disconnect = disconnected
io.on_subscribe = subscribe

io.add_feed_callback(FEED_ONAIR, on_matrix_onair)
io.add_feed_callback(FEED_TEXT, on_matrix_text)
print("Connecting to Adafruit IO...")
io.connect()
# Subscribe to all messages on the led feed
io.subscribe(FEED_ONAIR)
io.subscribe(FEED_TEXT)

while True:
    try:
        io.loop()
    except (ValueError, RuntimeError, MQTT.MMQTTException) as e:
        print("Failed to get data, retrying\n", e)
        try:
            wifi.reset()
            wifi.connect()
            io.reconnect()
            #Failed to get data, retrying
            # ESP32 timed out on SPI select
            #Traceback (most recent call last):
            #  File "code.py", line 190, in <module>
            #  File "code.py", line 189, in <module>
            #  File "adafruit_io/adafruit_io.py", line 101, in reconnect
            #  File "adafruit_io/adafruit_io.py", line 101, in reconnect
            #AdafruitIO_MQTTError: MQTT Error: Unable to reconnect to Adafruit IO.
        except Exception as e:
            print("Still network error... keep trying.")
            print(e)
        continue

