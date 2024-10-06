import socket
import threading
from collections import deque
import signal
import time
from picarx import Picarx
from robot_hat import utils

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

tx_lock = threading.Lock()
rx_lock = threading.Lock()

# Instantiate Picar-X
picar = Picarx()

def get_battery_voltage(*args) -> float:
    """
    Returns battery voltage of the Picar.

    Returns:
        float: Battery voltage.
    """
    return utils.get_battery_voltage()

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

def set_camera_pan_angle(angle) -> int:
    """
    Sets camera pan angle.

    Args:
        angle (int): Camera pan angle, in degrees.

    Returns:
        int: New servo angle, in degrees.
    """
    picar.set_cam_pan_angle(int(angle))
    return int(angle)

def set_camera_tilt_angle(angle) -> int:
    """
    Sets camera tilt angle.

    Args:
        angle (int): Camera tilt angle, in degrees.

    Returns:
        int: New servo angle, in degrees.
    """
    picar.set_cam_tilt_angle(int(angle))
    return int(angle)

def set_direction_servo_angle(angle) -> int:
    """
    Sets direction servo angle.

    Args:
        angle (int): Direction servo angle, in degrees.

    Returns:
        int: New servo angle, in degrees.
    """
    picar.set_dir_servo_angle(int(angle))
    return int(angle)

def forward(speed):
    """
    Moves Picar-X forwards at the specified speed.

    Args:
        speed (int): Forwards speed, as duty cycle percentage.

    Returns:
        int: New motor speed, as duty cycle percentage.
    """
    picar.forward(int(speed))
    return int(speed)

def backward(speed):
    """
    Moves Picar-X backwards at the specified speed.

    Args:
        speed (int): Backwards speed, as duty cycle percentage.

    Returns:
        int: New motor speed, as duty cycle percentage.
    """
    picar.backward(int(speed))
    return int(speed)

def stop(*args):
    """
    _summary_

    Returns:
        int: New motor speed as duty cycle percentage, always 0.
    """
    picar.stop()
    return 0

def call_supported_func(func_name, *args):
    supported_funcs = {
        "get_battery_voltage": get_battery_voltage,
        "get_cliff_status": get_cliff_status,
        "get_ultrasonic_distance": get_ultrasonic_distance,
        "set_camera_pan_angle": set_camera_pan_angle,
        "set_camera_tilt_angle": set_camera_tilt_angle,
        "set_direction_servo_angle": set_direction_servo_angle,
        "forward": forward,
        "backward": backward,
        "stop": stop,
    }

    func = supported_funcs.get(func_name, None)
    if func is None:
        print(f"Received unsupported function call: {func_name}({args})")
        return None

    return f"{func_name} {func(*args)}\r\n"

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
    global tx_lock
    global rx_lock

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
        if rx_lock.acquire(blocking=False):
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
            rx_lock.release()

        # Parse function and args to call from message
        if len(rx_message_deque) > 0:
            rx_message_parts = rx_message_deque.popleft().split(" ")
            func_name = rx_message_parts.pop(0)

            # Call function with args
            ret_val = call_supported_func(func_name, *rx_message_parts)

            # Queue results of called function for transmission
            if tx_lock.acquire(blocking=False):
                tx_message_deque.append(ret_val)
                tx_lock.release()

        # Send each message in the deque
        if tx_lock.acquire(blocking=False):
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
            tx_lock.release()

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