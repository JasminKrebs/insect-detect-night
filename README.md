# Insect Detect Night - DIY camera trap for automated nocturnal insect monitoring

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://choosealicense.com/licenses/gpl-3.0/)

This project is based on [Insect Detect](https://github.com/maxsitt/insect-detect). Here, Insect Detect was adapted to enable the passive monitoring of nocturnal pollinators. The most important implemented adaptations include a night-vision camera with
integrated infrared (IR) illumination to allow reliable detection under low-light conditions, an LED ring to provide illumination for high-resolution color images of detected insects and a light sensor to measure ambient light levels.

This repository contains Python scripts for the **Insect Detect Night** DIY camera trap for automated insect monitoring.

The camera trap system is composed of low-cost off-the-shelf hardware components
([Raspberry Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/),
[Luxonis OAK-D Pro](https://docs.luxonis.com/hardware/products/OAK-D%20Pro),
[Witty Pi 4 L3V7](https://www.uugear.com/product/witty-pi-4-l3v7/),
[WS2812 RGB Ring](https://shop.watterott.com/WS2812-RGB-Ring-12-weiss),
[Lichtsensor, TSL2591](https://www.reichelt.de/de/de/shop/produkt/entwicklerboards_-_lichtsensor_tsl2591-316547)), combined with open source software.

<img src="https://raw.githubusercontent.com/JasminKrebs/insect-detect-night/main/docs/images/cam_trap_setup.jpg" width="400">

---

## Processing pipeline

All configuration parameters can be customized in the web app or by directly modifying the
[`config_mono.yaml`](https://github.com/JasminKrebs/insect-detect-night/tree/main/configs/config_mono.yaml)
file. 

Processing pipeline for the
[`yolo_tracker_save_hqsync.py`](https://github.com/JasminKrebs/insect-detect-night/blob/main/yolo_tracker_save_hqsync.py)
script that can be used for automated insect monitoring:


<img src="https://raw.githubusercontent.com/JasminKrebs/insect-detect-night/main/docs/images/pipeline.png" width="800">

---

## License

This repository is licensed under the terms of the GNU General Public License v3.0
([GNU GPLv3](https://choosealicense.com/licenses/gpl-3.0/)).
