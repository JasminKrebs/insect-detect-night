import board
import neopixel
import time

# Set up NeoPixel ring
LED_COUNT = 24         # Number of LEDs on your ring
PIN = board.D18        # GPIO18 (pin 12 on Pi)
BRIGHTNESS = 0.5       # Optional: range from 0.0 to 1.0

# Initialize the NeoPixel object
pixels = neopixel.NeoPixel(PIN, LED_COUNT, brightness=BRIGHTNESS, auto_write=False)

# Turn all LEDs white
pixels.fill((255, 255, 255))  # RGB for white
pixels.show()

# Wait for 2 seconds
time.sleep(2)

# Turn all LEDs off
pixels.fill((0, 0, 0))
pixels.show()
