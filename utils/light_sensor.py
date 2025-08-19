import threading
import time
import logging

try:
    import board
    import adafruit_tsl2591
    TSL2591_AVAILABLE = True
except ImportError:
    TSL2591_AVAILABLE = False

logger = logging.getLogger(__name__)


def init_light_sensor():
    """Initialize TSL2591 light sensor.
    
    Returns:
        sensor object or None if initialization fails
    """
    if not TSL2591_AVAILABLE:
        logger.warning("TSL2591 library not available, light sensor disabled")
        return None
    
    try:
        i2c = board.I2C()
        sensor = adafruit_tsl2591.TSL2591(i2c)
        
        # Configure sensor settings
        sensor.gain = adafruit_tsl2591.GAIN_LOW
        sensor.integration_time = adafruit_tsl2591.INTEGRATIONTIME_100MS
        
        # Test reading to ensure sensor is working
        _ = sensor.lux
        
        logger.info("TSL2591 light sensor initialized successfully")
        return sensor
        
    except Exception as e:
        logger.warning(f"Failed to initialize TSL2591 light sensor: {e}")
        return None


def get_light_reading(sensor):
    """Get current light sensor readings.
    
    Args:
        sensor: TSL2591 sensor object
        
    Returns:
        dict with light measurements or None if reading fails
    """
    if sensor is None:
        return None
        
    try:
        return {
            "lux": round(sensor.lux, 2) if sensor.lux is not None else 0.0,
            "infrared": sensor.infrared,
            "visible": sensor.visible,
            "full_spectrum": sensor.full_spectrum
        }
    except Exception as e:
        logger.warning(f"Failed to read light sensor: {e}")
        return None


def create_get_light_data(sensor):
    """Create a thread-safe function to get light sensor data.
    
    Args:
        sensor: TSL2591 sensor object
        
    Returns:
        Function that returns current light data
    """
    light_lock = threading.Lock()
    
    def get_light_data():
        """Get current light sensor data in a thread-safe manner."""
        with light_lock:
            try:
                if sensor is None:
                    return {
                        "lux": "NA",
                        "infrared": "NA", 
                        "visible": "NA",
                        "full_spectrum": "NA"
                    }
                
                data = get_light_reading(sensor)
                if data is None:
                    return {
                        "lux": "NA",
                        "infrared": "NA",
                        "visible": "NA", 
                        "full_spectrum": "NA"
                    }
                return data
                
            except Exception as e:
                logger.warning(f"Error getting light data: {e}")
                return {
                    "lux": "NA",
                    "infrared": "NA",
                    "visible": "NA",
                    "full_spectrum": "NA"
                }
    
    return get_light_data
