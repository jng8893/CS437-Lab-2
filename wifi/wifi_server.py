import socket
import json
import picar_4wd as fc
from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import threading
import time
# from image_recognition import get_latest_frame, get_latest_detection

HOST = "10.0.0.22" # IP address of your Raspberry PI
PORT = 65432          # Port to listen on (non-privileged ports are > 1023)

# Flask app
app = Flask(__name__)


latest_frame = None
frame_lock = threading.Lock()
speed = 25 # Initial speed of the car


"""
    Handles incoming commands from the client and controls the car accordingly.

    Args:
        command (str): The command received from the client.

    Returns:
        str: A JSON-formatted string containing the status and car data.
"""
def handle_command(command):
    global speed
    print(f"Received command: {command}")
    if command == 'forward':
        fc.forward(speed)
        return json.dumps({"status": "Moving forward", **get_car_data()})
    elif command == 'backward':
        fc.backward(speed)
        return json.dumps({"status": "Moving backward", **get_car_data()})
    elif command == 'left':
        fc.turn_left(speed)
        return json.dumps({"status": "Turning left", **get_car_data()})
    elif command == 'right':
        fc.turn_right(speed)
        return json.dumps({"status": "Turning right", **get_car_data()})
    elif command == 'stop':
        fc.stop()
        return json.dumps({"status": "Stopped", **get_car_data()})
    elif command == 'getData':
        return json.dumps(get_car_data())
    elif command == 'speedUp':
        speed = min(speed + 5, 100)
        return json.dumps({"status": "Speed increased", "speed": speed})
    elif command == 'speedDown':
        speed = max(speed - 5, 0)
        return json.dumps({"status": "Speed decreased", "speed": speed})
    else:
        return json.dumps({"greeting": f"Hello {command} from the server!"})

"""
    Retrieves the current data from the car's sensors.

    Returns:
        dict: A dictionary containing distance, grayscale sensor values, and speed.
"""
def get_car_data():
    return {
        # "speed": fc.speed_val(),
        "distance": fc.us.get_distance(),
        "grayscale": fc.get_grayscale_list(),
        "speed": speed
    }

# Initializes the PiCamera2 for capturing video frames
def initialize_camera():
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()
    return picam2

# Continuously captures frames from the camera and updates the latest_frame variable.
def capture_frames(picam2):
    global latest_frame
    while True:
        frame = picam2.capture_array()
        with frame_lock: # Acquire the lock before updating latest_frame
            latest_frame = frame
        time.sleep(0.03)  # 30 FPS

# Generates encoded JPEG frames for the video feed.
def generate_frames():
    while True:
        with frame_lock: # Acquire the lock before updating latest_frame
            if latest_frame is not None:
                _, buffer = cv2.imencode('.jpg', latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.03)  # 30 FPS

# def generate_frames():
#     while True:
#         frame = get_latest_frame()
#         if frame is not None:
#             detection = get_latest_detection()
#             if detection['detected']:
#                 label = f"{detection['class_name']}: {detection['class_score']:.2f}"
#                 cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
#             _, buffer = cv2.imencode('.jpg', frame)
#             frame = buffer.tobytes()
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
#         else:
#             time.sleep(0.1)


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    
# For object recognition
# @app.route('/detection_result')
# def detection_result():
#     return jsonify(get_latest_detection())

# Runs the TCP server that listens for incoming connections and handles commands.
def run_server():
    host = "10.0.0.22"
    port = 65432

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port)) # Bind the socket to the address and port
        s.listen() # Start listening for incoming connections
        print(f"Server listening on {host}:{port}")

        while True:
            client, clientInfo = s.accept()
            print("Server received connection from:", clientInfo)
            data = client.recv(1024).decode().strip()
            print(f"Received data: {data}")

            if data:
                response = handle_command(data)
                print(f"Sending response: {response}")
                client.sendall(response.encode())
            
            client.close()



# The use of separate threads for capturing frames and running the Flask server allows the server to handle multiple tasks concurrently without blocking.
if __name__ == '__main__':
    picam2 = initialize_camera()


    # Start a separate thread to capture frames continuously
    frame_thread = threading.Thread(target=capture_frames, args=(picam2,))
    frame_thread.daemon = True
    frame_thread.start()

    # Start the Flask server in a separate thread
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=9000, threaded=True))
    flask_thread.daemon = True
    flask_thread.start()

    run_server()