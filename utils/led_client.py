import socket

SOCKET_PATH = "/tmp/led.sock"

def led_send_command(cmd, value=0):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.sendto(f"{cmd}:{value}".encode(), SOCKET_PATH)
        sock.close()
    except Exception as e:
        print("LED socket error:", e)

def set_led_on(brightness):
    led_send_command("on", brightness)

def set_led_off():
    led_send_command("off", 0)

def set_led_detect(brightness):
    led_send_command("detect", brightness)