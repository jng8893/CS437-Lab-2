import bluetooth
import cv2
import json
from picamera2 import Picamera2
from picarx import Picarx
from robot_hat import utils
from time import sleep, time
import threading

# Initialize Picarx
px = Picarx()

# Define car stats
car_stats = {
    "MOVING": "stopped",
    "SPEED": 0,
    "TURNING": "no",
    "DISTANCE": 0,
    "BATTERY": 0
}
car_stats_lock = threading.Lock()
last_command_time = time()  # Track the time of the last car command

# Initialize Picamera2
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration(main={"size": (420, 340), "format": "RGB888"})
picam2.configure(camera_config)
picam2.start()

def update_battery_and_distance():
    distance = round(px.ultrasonic.read(), 2)
    battery_level = (utils.get_battery_voltage() / 8.4) * 100
    with car_stats_lock:
        car_stats["DISTANCE"] = distance
        car_stats["BATTERY"] = battery_level

def start_bluetooth_server():
    server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    port = bluetooth.PORT_ANY
    server_socket.bind(("", port))
    server_socket.listen(1)
    print("Waiting for Bluetooth connection...")
    client_socket, client_info = server_socket.accept()
    print("Accepted connection from", client_info)
    return client_socket

def handle_video_feed(client_socket):
    while True:
        try:
            # Capture frame from Picamera2
            frame = picam2.capture_array()

            # Update battery and distance
            update_battery_and_distance()

            # Lock to read car stats safely
            with car_stats_lock:
                # Define positions for each stat
                moving_text = f"Moving: {car_stats['MOVING']}"
                speed_text = f"Speed: {car_stats['SPEED']}"
                turning_text = f"Turning: {car_stats['TURNING']}"
                distance_text = f"Distance: {car_stats['DISTANCE']} cm"
                battery_text = f"Battery: {car_stats['BATTERY']:.1f} %"

            # Draw each text on the frame at different positions
            cv2.putText(frame, moving_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)   # Moving
            cv2.putText(frame, speed_text, (210, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)    # Speed
            cv2.putText(frame, turning_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)   # Turning
            cv2.putText(frame, distance_text, (210, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)  # Distance
            cv2.putText(frame, battery_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)   # Battery

            # Encode the frame as JPEG with reduced quality (to optimize for Bluetooth)
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            frame_data = buffer.tobytes()

            # Send the frame size followed by the frame data
            client_socket.sendall(len(frame_data).to_bytes(4, 'big'))  # Send frame size first
            client_socket.sendall(frame_data)  # Then send frame data

            # Send the car stats as JSON separately
            with car_stats_lock:
                car_stats_json = json.dumps(car_stats).encode('utf-8')  # Encode JSON stats
            client_socket.sendall(len(car_stats_json).to_bytes(4, 'big'))  # Send JSON size first
            client_socket.sendall(car_stats_json)  # Then send JSON data

        except Exception as e:
            print(f"Error receiving video feed: {e}")
            break

        # Sleep to control frame rate (lower rate for Bluetooth bandwidth)
        sleep(0.2)

def move_car(command):
    global last_command_time
    with car_stats_lock:
        if command.startswith("move_forward"):
            speed = int(command.split("(")[1].strip(')'))
            car_stats["MOVING"] = "forward"
            car_stats["SPEED"] = speed
            car_stats["TURNING"] = "no"
            last_command_time = time()  # Update last command time
            px.forward(speed)
            sleep(0.5)
            px.stop()
        elif command.startswith("move_left"):
            speed = int(command.split("(")[1].strip(')'))
            car_stats["MOVING"] = "left"
            car_stats["SPEED"] = speed
            car_stats["TURNING"] = "yes"
            last_command_time = time()
            for angle in range(0, -31, -1):
                px.set_dir_servo_angle(angle)
                sleep(0.05)
            px.forward(speed)
            sleep(0.5)
            px.stop()
            for angle in range(-30, 1):
                px.set_dir_servo_angle(angle)
                sleep(0.05)
        elif command.startswith("move_right"):
            speed = int(command.split("(")[1].strip(')'))
            car_stats["MOVING"] = "right"
            car_stats["SPEED"] = speed
            car_stats["TURNING"] = "yes"
            last_command_time = time()
            for angle in range(0, 31):
                px.set_dir_servo_angle(angle)
                sleep(0.05)
            px.forward(speed)
            sleep(0.5)
            px.stop()
            for angle in range(30, -1, -1):
                px.set_dir_servo_angle(angle)
                sleep(0.05)
        elif command.startswith("move_backwards"):
            speed = int(command.split("(")[1].strip(')'))
            car_stats["MOVING"] = "backward"
            car_stats["SPEED"] = speed
            car_stats["TURNING"] = "no"
            last_command_time = time()
            px.backward(speed)
            sleep(0.5)
            px.stop()

def reset_stats_after_idle():
    """Reset car stats if the car has been idle"""
    global last_command_time
    while True:
        current_time = time()
        if current_time - last_command_time > 5:  # 5 seconds idle threshold
            with car_stats_lock:
                car_stats["MOVING"] = "stopped"
                car_stats["SPEED"] = 0
                car_stats["TURNING"] = "no"
        sleep(1)  # Check every second

# Main function
def main():
    client_socket = start_bluetooth_server()

    # Start the video feed in a separate thread
    video_thread = threading.Thread(target=handle_video_feed, args=(client_socket,))
    video_thread.start()

    # Start a thread to reset stats after 2 seconds of inactivity
    idle_reset_thread = threading.Thread(target=reset_stats_after_idle)
    idle_reset_thread.daemon = True  # Ensure this thread stops when the main program ends
    idle_reset_thread.start()

    try:
        while True:
            # Receive command from client
            command = client_socket.recv(1024).decode('utf-8')
            if command:
                move_car(command)
    except Exception as e:
        print("Error:", e)
    finally:
        client_socket.close()
        picam2.close()

if __name__ == "__main__":
    main()

