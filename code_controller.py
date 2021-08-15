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

import board
import time
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
from adafruit_io.adafruit_io import IO_MQTT

from secrets import secrets

# OLED Display
WIDTH = 128
HEIGHT = 64
BORDER = 5
BLACK = 0x000000
WHITE = 0xFFFFFF

FEED_ONAIR = "matrix-onair"
FEED_TEXT = "matrix-text"
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

def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    print("Connected to Adafruit IO! ")
    group_status.y -= 1

def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")

def on_matrix_onair(client, topic, message):
    # Method called whenever user/feeds/led has a new value
    print("New message on topic {0}: {1} ".format(topic, message))
    if message == "ON":
        led.value = True
        group_on.hidden = False
        group_off.hidden = True
    elif message == "OFF":
        led.value = False
        group_on.hidden = True
        group_off.hidden = False
    else:
        print("Unexpected message on LED feed.")

def on_matrix_text(client, topic, message):
    print("New message on topic {0}: {1} ".format(topic, message))
    if message == ".":
        label_time_feed.text = ""
    else:
        label_time_feed.text = message

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
            io.publish(FEED_ONAIR, "ON")
            print("Published!")
            io.publish(FEED_TEXT, ".")
            print("Published!")
        if btnWhite.rose == True:
            print("btnWhite is pressed")
            led_blue.value = True
            led_green.value = True
            io.publish(FEED_ONAIR, "OFF")
            print("Published!")
            io.publish(FEED_TEXT, ".")
            print("Published!")
        if btnRotary.rose == True:
            print("btnRotary is pressed")
            #if group_on.hidden == False:
            led_green.value = False
            io.publish(FEED_TEXT, "~"+label_time.text)
            print("Published!")
        # Poll for incoming messages
        try:
            io.loop(0.1)
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

loop()

