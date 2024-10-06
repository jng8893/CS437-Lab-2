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

dq_lock = threading.Lock()
output_lock = threading.Lock()

rx_retvals = {
    "get_cliff_status": None,
    "get_ultrasonic_distance": None,
}

def send_supported_func(func_name, *args):
    if func_name not in rx_retvals:
        print(f"Cannot send unsupported function: {func_name}")
        return

    if not args:
        message = func_name + "\r\n"
    else:
        message = func_name + " ".join(args) + "\r\n"

    if dq_lock.acquire(blocking=False):
        print(f"Queueing message {message}")
        tx_message_deque.append(message)
        dq_lock.release()


def handler(signum, frame):
    exit_event.set()

signal.signal(signal.SIGINT, handler)

def start_client():
    global sock
    global dq_lock
    global output_lock
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
        if dq_lock.acquire(blocking=False):
            if(len(tx_message_deque) > 0):
                try:
                    sent = sock.send(bytes(tx_message_deque[0], 'utf-8'))
                    print(f"Sent {tx_message_deque[0]}")
                except Exception as e:
                    exit_event.set()
                    continue
                if sent < len(tx_message_deque[0]):
                    tx_message_deque[0] = tx_message_deque[0][sent:]
                else:
                    tx_message_deque.popleft()
            dq_lock.release()

        if output_lock.acquire(blocking=False):
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
            for i in range(len(output_split) - 1):
                print(output_split[i])
            output = output_split[-1]
            output_lock.release()

    sock.close()
    print("client thread end")

if __name__ == "__main__":
    cth = threading.Thread(target=start_client)
    cth.start()

    while not exit_event.is_set():
        # TODO: print retval from Raspberrry Pi
        send_supported_func("get_cliff_status")
        send_supported_func("get_ultrasonic_distance")
        time.sleep(2)

    print("Disconnected.")
    exit_event.set()

    print("All done.")
    exit()