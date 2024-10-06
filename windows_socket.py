import socket
import threading
from collections import deque
import signal
import time

server_addr = "D8:3A:DD:E9:35:3E"
server_port = 1

buf_size = 1024

client_sock = None
server_sock = None
sock = None

exit_event = threading.Event()

tx_message_deque = deque([])
output = ""

tx_lock = threading.Lock()
rx_lock = threading.Lock()

rx_retvals = {
    "get_battery_voltage": None,
    "get_cliff_status": None,
    "get_ultrasonic_distance": None,
    "set_camera_pan_angle": None,
    "set_camera_tilt_angle": None,
    "set_direction_servo_angle": None,
    "forward": None,
    "backward": None,
    "stop": None,
}

def send_supported_func(func_name, *args):
    if func_name not in rx_retvals:
        print(f"Cannot send unsupported function: {func_name}")
        return

    if not args:
        message = func_name + "\r\n"
    else:
        message = func_name + ' ' + " ".join([str(arg) for arg in args]) + "\r\n"

    if tx_lock.acquire(blocking=False):
        # print(f"Queueing message {message}")
        tx_message_deque.append(message)
        tx_lock.release()


def handler(signum, frame):
    exit_event.set()

signal.signal(signal.SIGINT, handler)

def start_client():
    global sock
    global tx_lock
    global rx_lock
    global exit_event
    global tx_message_deque
    global output
    global server_addr
    global server_port

    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    sock.settimeout(10)

    sock.connect((server_addr,server_port))
    sock.settimeout(None)
    sock.setblocking(False)

    while not exit_event.is_set():
        if tx_lock.acquire(blocking=False):
            if(len(tx_message_deque) > 0):
                try:
                    sent = sock.send(bytes(tx_message_deque[0], 'utf-8'))
                except Exception as e:
                    exit_event.set()
                    continue
                if sent < len(tx_message_deque[0]):
                    tx_message_deque[0] = tx_message_deque[0][sent:]
                else:
                    tx_message_deque.popleft()
            tx_lock.release()

        if rx_lock.acquire(blocking=False):
            data = ""
            try:
                data = sock.recv(1024).decode("utf-8")
            except socket.error as e:
                pass
                #no data
            except Exception as e:
                exit_event.set()
                continue

            output += data
            output_split = output.split("\r\n")
            for rx_message in output_split[:-1]:
                rx_message_parts = rx_message.split(" ")
                func_name = rx_message_parts.pop(0)
                retval = rx_message_parts.pop(0)
                rx_retvals[func_name] = retval
            output = output_split[-1]
            rx_lock.release()

    sock.close()
    print("client thread end")

if __name__ == "__main__":
    cth = threading.Thread(target=start_client)
    cth.start()
    send_supported_func("set_camera_pan_angle", 30)
    time.sleep(2.0)
    print(rx_retvals)
    send_supported_func("set_camera_pan_angle", -30)
    time.sleep(2.0)
    print(rx_retvals)
    send_supported_func("set_camera_pan_angle", 0)
    time.sleep(2.0)
    print(rx_retvals)

    while not exit_event.is_set():
        # TODO: print retval from Raspberrry Pi
        if len(output) == 0:
            send_supported_func("get_battery_voltage")
            send_supported_func("get_cliff_status")
            send_supported_func("get_ultrasonic_distance")
            print(rx_retvals)
        time.sleep(2)

    print("Disconnected.")
    exit_event.set()

    print("All done.")
    exit()