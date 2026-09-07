"""Client helpers for sending LED commands to the LED control service."""

import socket

SOCKET_PATH = "/tmp/led.sock"

def led_send_command(cmd, value=0):
    """Send a command to the LED control socket."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.sendto(f"{cmd}:{value}".encode(), SOCKET_PATH)
        sock.close()
    except Exception as e:
        print("LED socket error:", e)

def set_led_on(brightness):
    """Turn the LED strip on at the given brightness."""
    led_send_command("on", brightness)

def set_led_off():
    """Turn the LED strip off."""
    led_send_command("off", 0)

def set_led_detect(brightness):
    """Trigger the short detection LED pulse."""
    led_send_command("detect", brightness)

def set_led_burst(brightness):
    """Trigger the longer burst LED pulse."""
    led_send_command("burst", brightness)
