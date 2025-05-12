import time
from rpi_ws281x import PixelStrip, Color

# LED strip configuration:
LED_COUNT = 16       # Number of LED pixels.
LED_PIN = 18         # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ = 800000 # LED signal frequency in hertz (usually 800kHz).
LED_DMA = 10         # DMA channel to use for generating signal (try 10).
LED_BRIGHTNESS = 255 # Set to 0 for darkest and 255 for brightest.
LED_INVERT = False   # True to invert the signal (when using NPN transistor level shift).
LED_CHANNEL = 0      # Set to 1 for GPIOs 13, 19, 41, 45 or 53.

# Create PixelStrip object.
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# Function to turn on all LEDs with a specific color.
def turn_on_leds(strip, color, duration):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()
    time.sleep(duration)
    strip.clear()  # Turn off LEDs after the duration.
    strip.show()

# Main program.
if __name__ == "__main__":
    try:
        # Turn on LEDs with white color for 2 seconds.
        turn_on_leds(strip, Color(255, 255, 255), 2)
    except KeyboardInterrupt:
        # Gracefully handle exit.
        strip.clear()
        strip.show()