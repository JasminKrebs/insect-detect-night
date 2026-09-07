"""Helpers for reading ambient light information from a TSL2591 sensor."""

import logging
import threading

try:
    import board
    import adafruit_tsl2591

    TSL2591_AVAILABLE = True
except ImportError:
    TSL2591_AVAILABLE = False

logger = logging.getLogger(__name__)

def init_light_sensor():
    """Initialize the TSL2591 light sensor if the hardware stack is available."""
    if not TSL2591_AVAILABLE:
        logger.warning("TSL2591 library not available, light sensor disabled")
        return None

    try:
        i2c = board.I2C()
        sensor = adafruit_tsl2591.TSL2591(i2c)
        sensor.gain = adafruit_tsl2591.GAIN_LOW
        sensor.integration_time = adafruit_tsl2591.INTEGRATIONTIME_100MS

        _ = sensor.lux

        logger.info("TSL2591 light sensor initialized successfully")
        return sensor
    except Exception as e:
        logger.warning(f"Failed to initialize TSL2591 light sensor: {e}")
        return None

def create_get_light_data(sensor):
    """Create a thread-safe getter for the current light sensor readings."""
    light_lock = threading.Lock()

    def get_light_data():
        """Return lux / infrared / visible values as a dictionary."""
        if sensor is None:
            return None

        with light_lock:
            try:
                full_spectrum = getattr(sensor, "full_spectrum", None)
                infrared = getattr(sensor, "infrared", None)
                lux = float(sensor.lux)
                if full_spectrum is None or infrared is None:
                    visible = None
                else:
                    visible = max(0.0, float(full_spectrum) - float(infrared))

                return {
                    "lux": round(lux, 2),
                    "infrared": float(infrared) if infrared is not None else 0.0,
                    "visible": round(visible, 2) if visible is not None else 0.0,
                }
            except RuntimeError:
                return None
            except Exception as e:
                logger.warning(f"Error reading light sensor: {e}")
                return None

    return get_light_data
