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