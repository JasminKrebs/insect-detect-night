"""Helpers for reading ambient light information from a TSL2591 sensor."""

import logging
import threading
import time

try:
    import board
    import adafruit_tsl2591

    TSL2591_AVAILABLE = True
except ImportError:
    TSL2591_AVAILABLE = False

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 1.0

_sensor = None
_pollers: dict[int, "_LightPoller"] = {}
_lock = threading.Lock()


def init_light_sensor():
    """Initialize the TSL2591 light sensor if the hardware stack is available.

    The sensor is only initialized once per process, later calls return the same instance
    (e.g. after a camera restart in the web app).
    """
    global _sensor
    if not TSL2591_AVAILABLE:
        logger.warning("TSL2591 library not available, light sensor disabled")
        return None

    with _lock:
        if _sensor is not None:
            return _sensor

        try:
            i2c = board.I2C()
            sensor = adafruit_tsl2591.TSL2591(i2c)
            sensor.gain = adafruit_tsl2591.GAIN_LOW
            sensor.integration_time = adafruit_tsl2591.INTEGRATIONTIME_100MS

            _ = sensor.lux

            logger.info("TSL2591 light sensor initialized successfully")
            _sensor = sensor
            return sensor
        except Exception as e:
            logger.warning(f"Failed to initialize TSL2591 light sensor: {e}")
            return None


class _LightPoller:
    """Read the light sensor in a background thread and cache the latest values.

    Each sensor read blocks for the integration time (~100 ms per value), so reading it directly
    in the web app's event loop or in the recording loop would stall them.
    """

    def __init__(self, sensor) -> None:
        self._sensor = sensor
        self._latest_lock = threading.Lock()
        self._latest: dict[str, float] | None = self._read()
        threading.Thread(target=self._run, name="LightSensorPoller", daemon=True).start()

    def _read(self) -> dict[str, float] | None:
        try:
            full_spectrum = getattr(self._sensor, "full_spectrum", None)
            infrared = getattr(self._sensor, "infrared", None)
            lux = float(self._sensor.lux)
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

    def _run(self) -> None:
        while True:
            time.sleep(POLL_INTERVAL_S)
            data = self._read()
            if data is not None:
                with self._latest_lock:
                    self._latest = data

    def latest(self) -> dict[str, float] | None:
        """Return the most recent lux / infrared / visible values (None if not read yet)."""
        with self._latest_lock:
            return dict(self._latest) if self._latest is not None else None


def create_get_light_data(sensor):
    """Create a non-blocking getter for the latest light sensor readings."""
    if sensor is None:
        return lambda: None

    with _lock:
        poller = _pollers.get(id(sensor))
        if poller is None:
            poller = _LightPoller(sensor)
            _pollers[id(sensor)] = poller

    return poller.latest
