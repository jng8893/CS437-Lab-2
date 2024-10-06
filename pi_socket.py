import socket
import threading
from collections import deque
import signal
import time
from picarx import Picarx

server_addr = 'D8:3A:DD:E9:35:3E'
server_port = 1

buf_size = 1024

client_sock = None
server_sock = None
sock = None

exit_event = threading.Event()

tx_message_deque = deque([])
rx_message_deque = deque([])
output = ""

dq_lock = threading.Lock()
output_lock = threading.Lock()

# Instantiate Picar-X
picar = Picarx()

def get_cliff_status(*args) -> bool:
    """
    Returns cliff detection status. True for cliff detected, False otherwise.

    Returns:
        bool: Cliff detection status.
    """
    return picar.get_cliff_status(picar.get_grayscale_data())

def get_ultrasonic_distance(*args) -> float:
    """
    Returns distance detected from ultrasonic sensor.

    Returns:
        float: Distance detected, in centimeters.
    """
    return picar.get_distance()

def call_supported_func(func_name, *args):
    supported_funcs = {
        "get_cliff_status": get_cliff_status,
        "get_ultrasonic_distance": get_ultrasonic_distance,
    }

    func = supported_funcs.get(func_name, None)
    if func is None:
        print(f"Received unsupported function call: {func_name}({args})")
        return None

    return f"{func_name} {func(*args)}"

def handler(signum, frame):
    exit_event.set()

signal.signal(signal.SIGINT, handler)

def start_client():
    global server_addr
    global server_port
    global server_sock
    global sock
    global exit_event
    global tx_message_deque
    global output
    global dq_lock
    global output_lock

    server_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    server_sock.bind((server_addr, server_port))
    server_sock.listen(1)
    server_sock.settimeout(10)
    sock, address = server_sock.accept()

    print(f"Connected to client at {address}")

    server_sock.settimeout(None)
    sock.setblocking(0)

    # Server loop
    while not exit_event.is_set():

        # Receive message from the client
        if output_lock.acquire(blocking=False):
            data = ""
            try:
                data = sock.recv(1024).decode('utf-8')

            # If no data received, continue to status reporting
            except socket.error:
                pass

            except Exception as e:
                exit_event.set()
                continue

            # Add received messages to corresponding deque
            output += data
            output_split = output.split("\r\n")

            # Only add messages to the deque if the termination sequence was received
            if len(output_split) > 1:
                rx_message_deque.extend(output_split[:len(output_split) - 1])

            # Update received output to any remaining message fragment
            # Will be an empty string if there is no remaining message fragment
            output = output_split[-1]
            output_lock.release()

        # Parse function and args to call from message
        if len(rx_message_deque) > 0:
            rx_message_parts = rx_message_deque.popleft().split(" ")
            func_name = rx_message_parts.pop(0)

            # Call function with args
            ret_val = call_supported_func(func_name, *rx_message_parts)

            # TODO: Send back results of called function
            print(ret_val)
            # tx_message_deque.append(ret_val)

        # Send each message in the deque
        if dq_lock.acquire(blocking=False):
            if(len(tx_message_deque) > 0):
                # Attempt sending the current message
                try:
                    bytes_sent = sock.send(bytes(tx_message_deque[0], 'utf-8'))

                # Close server when exception is raised
                except Exception:
                    exit_event.set()
                    continue

                # If the socket did not send the entire message, set the current message to the remaining bytes
                if bytes_sent < len(tx_message_deque[0]):
                    print(tx_message_deque, tx_message_deque[0][bytes_sent:])
                    tx_message_deque[0] = tx_message_deque[0][bytes_sent:]
                else:
                    tx_message_deque.popleft()
            dq_lock.release()

    # Cleanup
    server_sock.close()
    sock.close()
    print("Client thread closed")


if __name__ == "__main__":
    cth = threading.Thread(target=start_client)
    cth.start()

    while not exit_event.is_set():
        time.sleep(1.5)


    print("Disconnected.")

    print("All done.")