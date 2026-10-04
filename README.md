# Simple Raspberry Pi Film Camera

A compact digital camera for a Raspberry Pi Zero, Raspberry Pi Camera Module,
1.14-inch IPS display, and UPS-Lite. The display provides a live viewfinder,
while a single physical button selects a film style or captures a full-resolution
JPEG.

Tap GPIO26 to cycle through the ten styles. The selected style appears briefly
on the screen. Hold GPIO26 for more than one second, then release it to capture
one image in that style. Standard is selected at startup. Ilford B&W produces
the black-and-white image; captures no longer create a color/B&W pair.

## Sample capture

| Standard color | Ilford B&W |
|---|---|
| <img src="docs/sample-capture.jpg" alt="Full-resolution color sample captured by the Raspberry Pi camera" width="360"> | <img src="docs/sample-capture-bw.jpg" alt="Black-and-white sample captured by the Raspberry Pi camera" width="360"> |

## Features

- Live 240x135 color viewfinder with a center-cropped 16:9 preview
- Quick shutter-frame and flash animation when a capture starts
- Full-resolution capture using the connected camera sensor's native resolution
- Ten live film styles: Standard, Classic Chrome, Kodak Portra, Fuji Velvia,
  Fuji Astia, Ilford B&W, Kodak Gold, Warm Natural, Golden Daylight, and Soft Nostalgia
- A short press cycles styles; a press over one second captures one styled JPEG
- The style name appears on the viewfinder for about 1.6 seconds after switching
- Automatic exposure and white balance
- Quality-92 JPEG output with the style name in the filename
- Fresh preview frames and one YUV still buffer to reduce stale frames and
  camera-memory pressure on a Pi Zero
- Direct JPEG saving for Standard; faster planar-YUV styling for the three warm looks
- Simple one-button shutter with no touchscreen or desktop environment required
- Automatic startup through systemd

## Hardware target

- Raspberry Pi Zero W or Zero 2 W
- Raspberry Pi Camera Module v1.3, v2, or another Picamera2-compatible CSI camera
- 1.14-inch 240x135 IPS SPI LCD using the ST7789 controller
- UPS-Lite for Raspberry Pi Zero
- Normally-open momentary shutter switch

UPS-Lite supplies power only and needs no integration in the app. Shut Raspberry
Pi OS down cleanly over SSH before switching off the UPS-Lite.

The included display driver is configured and tested for the 1.14-inch 240x135
ST7789 module. Similar SPI LCDs can also work, but they are not drop-in
replacements. Depending on the panel and controller, adapt `st7789.py` for its
resolution, initialization commands, orientation and color order, display-RAM
offsets, SPI speed, and GPIO mapping. A display using a different controller
will generally need its own driver implementation.

## Wiring

The display is the eight-pin, 1.14-inch 240x135 IPS module with an ST7789
controller and pins labelled `GND VCC SCL SDA RES DC CS BLK`. Despite their
names, `SCL` and `SDA` carry SPI clock and data; do not connect them to the Pi's
I2C pins. GPIO numbers below are BCM numbers.

| Part | Module label | Pi function | Physical pin |
|---|---|---|---:|
| LCD | GND | Ground | 6 |
| LCD | VCC | 3.3 V | 1 |
| LCD | SCL | GPIO11 / SPI0 SCLK | 23 |
| LCD | SDA | GPIO10 / SPI0 MOSI | 19 |
| LCD | RES | GPIO27 | 13 |
| LCD | DC | GPIO25 | 22 |
| LCD | CS | GPIO8 / SPI0 CE0 | 24 |
| LCD | BLK | GPIO18 | 12 |
| Shutter | one terminal | GPIO26 | 37 |
| Shutter | other terminal | Ground | 39 |

Use 3.3 V for the display supply and logic. No MISO wire is required because
the LCD only receives data. The app drives `BLK` high after initialization and
low during shutdown; do not connect `BLK` to both GPIO18 and 3.3 V. Switch off
and disconnect Pi power before changing any wiring.

The shutter uses the Pi's internal pull-up. Do not add a connection to 3.3 V.

Connect the camera module to the Pi Zero's CSI connector with the Pi powered
off. The v1.3 and v2 modules require a Pi Zero 22-pin-to-15-pin camera cable
rather than a standard 15-pin cable. Seat both ends squarely and close both
locking tabs.

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
  python3-gpiozero python3-spidev python3-simplejpeg
```

Copy or clone this repository into the Pi user's home directory, then verify the
app before installing the service:

```bash
cd ~/rpi-simple-camera
python3 camera.py
```

Pictures are written to `~/Pictures`, which is created automatically.
Each shutter hold saves one JPEG named with a timestamp and selected style.
Stop the manual run with `Ctrl+C`.

To copy all captured JPEGs to another computer on the same network, run this on
that computer and replace the destination path as needed:

```bash
scp 'YOUR_USER@raspberrypi.local:~/Pictures/*.jpg' ~/Desktop/
```

## Start automatically at boot

```bash
sudo cp systemd/rpi-simple-camera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-simple-camera.service
```

The bundled service file assumes the Pi username is `pi` and the repository is
at `/home/pi/rpi-simple-camera`. If either differs, update `User`,
`WorkingDirectory`, and `ExecStart` in the service file before installing it.

This is a console service and does not need X11, Wayland, a desktop session, or
a framebuffer mirror. The app sends the 240x135 preview directly to the ST7789
over SPI.

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

Camera controls are in `camera.py`, style recipes are in `film_styles.py`, and
the display driver is in `st7789.py`. Styled captures other than the three warm
looks convert the full-resolution YUV frame to BGR for processing, so they may
take longer on a Pi Zero. High-resolution cameras may need a larger CMA buffer
in `/boot/firmware/config.txt` (for example `dtoverlay=cma,cma-128`); reboot
after changing it. The sample images above show the original color and B&W
output; they are examples of the two looks, not a new paired capture.
