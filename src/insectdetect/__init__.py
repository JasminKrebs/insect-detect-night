"""Software package for automated insect monitoring with the Insect Detect camera trap.

Source:   https://github.com/maxsitt/insect-detect
License:  GNU GPLv3 (https://choosealicense.com/licenses/gpl-3.0/)
Author:   Maximilian Sittinger (https://github.com/maxsitt)
Docs:     https://maxsitt.github.io/insect-detect-docs/

Entry Points (via pyproject.toml scripts):
    startup: uv run startup
    capture_day:   uv run capture_day
    capture_night: uv run capture_night
    webapp:        uv run webapp

Modules:
    startup:     Run configured startup sequence at boot (requires enabled systemd service).
    capture_day:   Capture detection-triggered images with the RGB camera (daytime).
    capture_night: Capture detection-triggered images with mono camera, IR floodlight and LED (night).
    webapp:      Stream OAK camera live feed and configure settings via browser-based web app.
    config:      Classes and functions for configuration file management.
    data:        Utility functions for data management.
    metrics:     Utility functions for system metrics and information logging.
    network:     Utility functions for network management via NetworkManager.
    oak:         Utility functions for OAK camera pipeline creation and metadata conversion.
    postprocess: Utility functions for post-processing of captured images.
    power:       Utility functions for power management initialization and state handling.
    wittypi:     Utility class for reading status information from Witty Pi 4 L3V7.
"""
