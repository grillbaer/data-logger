# Data Logger
Measure, display and log temperatures with Raspberry PI.

This is a simply hobby project for logging temperatures in my heating system. Feel free to adjust and use it in your own projects.

## Functions



## Hardware

- Raspberry PI 3
- Official Raspberry PI 7" Touch Display, 800x480 (expensive, but well supported in Raspbian, multi-touch)
- DS 18B20 temperature sensors (1-Wire bus allows many sensors at the same GPIO port, well supported in Raspbian)
- TSIC 306 temperature sensors (high accurracy, expensive, but already installed from a previous project)
- Official Raspberry power supply 5.1V/2.5A with additional 330uF capacitor for stabilization (Raspi is quite picky here...)
- Heat sink on Raspberry CPU (... to avoid the random crashes that may occur otherwise)

## Software

- OS Raspbian
- Language: Python 3.6 (I begin to really like Python, however, the code is still at Python beginner's level)
- UI toolkit: Kivy (nice and simple UIs with multi-touch support, some quirks)
- Charts: Kivy Garden Graphs (fast drawing)
- GPIO access: PIGPIO (IO with precise timing)
