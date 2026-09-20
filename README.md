# Simple Raspberry Pi Color + B&W Camera

A deliberately minimal digital camera for a Raspberry Pi Zero, Pi Camera Module
v1.3, Waveshare-style 0.96-inch IPS display, and UPS-Lite. The screen is only a
viewfinder. There is no touchscreen handling, menu, overlay, focus peaking,
digital zoom, filter, or adjustable camera setting.

Pressing the single physical shutter button captures one full-resolution frame
and saves two JPEGs made from that same exposure:

```text
20260920_142530_123456_color.jpg
20260920_142530_123456_bw.jpg
```

The color file is saved first. The B&W file is a neutral grayscale conversion
of the exact same captured pixels; it is not a second exposure.

## Hardware target

- Raspberry Pi Zero W or Zero 2 W
- Raspberry Pi Camera Module v1.3 (OV5647, fixed focus, 2592x1944 stills)
- 0.96-inch 160x80 IPS SPI LCD using the ST7735S controller
- UPS-Lite for Raspberry Pi Zero
- Normally-open momentary shutter switch

UPS-Lite supplies power only and needs no integration in the app. Shut Raspberry
Pi OS down cleanly over SSH before switching off the UPS-Lite; the shutter has
no secondary or long-press action.

## Wiring

The display pinout follows the Waveshare 0.96-inch LCD module. GPIO numbers are
BCM numbers.

| Part | Signal | Raspberry Pi |
|---|---|---|
| LCD | VCC | 3.3 V (physical pin 1) |
| LCD | GND | GND (physical pin 6) |
| LCD | DIN/MOSI | GPIO10 (physical pin 19) |
| LCD | CLK/SCLK | GPIO11 (physical pin 23) |
| LCD | CS | GPIO8/CE0 (physical pin 24) |
| LCD | DC | GPIO25 (physical pin 22) |
| LCD | RST | GPIO27 (physical pin 13) |
| LCD | BL | GPIO18 (physical pin 12) |
| Shutter | one terminal | GPIO26 (physical pin 37) |
| Shutter | other terminal | GND (physical pin 39) |

The shutter uses the Pi's internal pull-up, matching the GPIO26 implementation
in `rpi-film-simulation-camera`. Do not add a connection to 3.3 V.

## Raspberry Pi OS setup

Use current Raspberry Pi OS Lite. Enable the camera and SPI interface:

```bash
sudo raspi-config
```

Under **Interface Options**, enable SPI. Current Raspberry Pi OS camera support
uses libcamera/Picamera2 and normally needs no legacy-camera setting. Reboot,
then install the platform packages:

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv python3-numpy \
  python3-gpiozero python3-spidev
```

Copy this directory to `/home/pi/rpi-simple-camera`, then verify the app before
installing the service:

```bash
cd /home/pi/rpi-simple-camera
python3 camera.py
```

Pictures are written to `/home/pi/Pictures`, which is created automatically.
Stop the manual run with `Ctrl+C`.

## Start automatically at boot

```bash
sudo cp systemd/rpi-simple-camera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-simple-camera.service
```

This is a console service and does not need X11, Wayland, a desktop session, or
a framebuffer mirror. The app sends the 160x80 preview directly over SPI.

Useful diagnostics:

```bash
sudo systemctl status rpi-simple-camera.service
sudo journalctl -u rpi-simple-camera.service -f
rpicam-hello --list-cameras
ls -l /dev/spidev0.0
```

Run the small image-helper test suite on the Pi with:

```bash
python3 -m unittest discover -s tests
```

## Fixed behavior

- Live, center-cropped 2:1 color preview on the LCD
- Automatic exposure and white balance
- One GPIO26 press captures one native-resolution frame
- JPEG quality 95
- Matching color and grayscale files from one exposure
- No controls, touch input, UI, indicators, filters, or focus processing

The hardware constants are collected at the top of `camera.py` and `st7735s.py`
if a physically different ST7735S board uses another pinout or orientation.
