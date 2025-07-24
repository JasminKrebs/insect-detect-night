import socket
import struct
import os
from rpi_ws281x import PixelStrip, Color
import time

# LED strip configuration
LED_COUNT = 12
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_INVERT = False
LED_CHANNEL = 0

# Global LED strip object
led = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_CHANNEL)
led.begin()

def set_led_on(brightness):
    """Turn LEDs on (brightness is controlled in webapp.py)."""
    led.setBrightness(int(brightness))
    for i in range(led.numPixels()):
        led.setPixelColor(i, Color(255, 255, 255))
    led.show()

def set_led_off():
    """Turn all LEDs off."""
    for i in range(led.numPixels()):
        led.setPixelColor(i, Color(0, 0, 0))
    led.show()

def set_led_detect(target_brightness, fade_time=1.0):
    """Gradually turn LEDs on to target brightness, hold for 2s, then turn off."""
    steps = 20
    delay = fade_time / steps
    for step in range(1, steps + 1):
        brightness = int(target_brightness * step / steps)
        led.setBrightness(brightness)
        for i in range(led.numPixels()):
            led.setPixelColor(i, Color(255, 255, 255))
        led.show()
        time.sleep(delay)
    time.sleep(2)  # Keep LEDs on at full brightness
    for i in range(led.numPixels()):
        led.setPixelColor(i, Color(0, 0, 0))
    led.show()

def set_led_burst(target_brightness, hold_time=5, fade_time=1.0):
    """Fade in LEDs to target brightness, hold for hold_time seconds, then turn off."""
    steps = 20
    delay = fade_time / steps
    for step in range(1, steps + 1):
        brightness = int(target_brightness * step / steps)
        led.setBrightness(brightness)
        for i in range(led.numPixels()):
            led.setPixelColor(i, Color(255, 255, 255))
        led.show()
        time.sleep(delay)
    time.sleep(hold_time)
    for i in range(led.numPixels()):
        led.setPixelColor(i, Color(0, 0, 0))
    led.show()

# UNIX socket path
SOCKET_PATH = "/tmp/led.sock"

# Remove old socket if exists
if os.path.exists(SOCKET_PATH):
    os.remove(SOCKET_PATH)

sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
sock.bind(SOCKET_PATH)
os.chmod(SOCKET_PATH, 0o666)

print("LED server started, waiting for commands...")

while True:
    data, _ = sock.recvfrom(1024)
    try:
        cmd, value = data.decode().split(":")
        value = int(value)
        if cmd == "on":
            set_led_on(value)
        elif cmd == "off":
            set_led_off()
        elif cmd == "detect":
            set_led_detect(value)
        elif cmd == "burst":
            set_led_burst(value)
    except Exception as e:
        print("Invalid command:", data, e)