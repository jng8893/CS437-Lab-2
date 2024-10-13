import sys
import threading
import time
import socket
import numpy as np
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QLabel, QSlider, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from windows_socket import send_supported_func, rx_retvals, start_client, exit_event

class BluetoothControlWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()
        self.start_bluetooth_thread()

    def initUI(self):
        self.setWindowTitle('PiCar-X Bluetooth Controller')

        # Create layout
        layout = QVBoxLayout()

        # Video feed QLabel
        self.video_label = QLabel(self)
        layout.addWidget(self.video_label)

        # Forward, Backward, Stop buttons
        self.forward_btn = QPushButton('Forward', self)
        self.forward_btn.clicked.connect(self.forward)
        layout.addWidget(self.forward_btn)

        self.backward_btn = QPushButton('Backward', self)
        self.backward_btn.clicked.connect(self.backward)
        layout.addWidget(self.backward_btn)

        self.stop_btn = QPushButton('Stop', self)
        self.stop_btn.clicked.connect(self.stop)
        layout.addWidget(self.stop_btn)

        # Sliders for pan and tilt angles
        self.pan_label = QLabel('Camera Pan Angle: 0°', self)
        layout.addWidget(self.pan_label)
        self.pan_slider = QSlider(Qt.Horizontal)
        self.pan_slider.setMinimum(-90)
        self.pan_slider.setMaximum(90)
        self.pan_slider.valueChanged.connect(self.update_pan_angle)
        layout.addWidget(self.pan_slider)

        self.tilt_label = QLabel('Camera Tilt Angle: 0°', self)
        layout.addWidget(self.tilt_label)
        self.tilt_slider = QSlider(Qt.Horizontal)
        self.tilt_slider.setMinimum(-90)
        self.tilt_slider.setMaximum(90)
        self.tilt_slider.valueChanged.connect(self.update_tilt_angle)
        layout.addWidget(self.tilt_slider)

        # Status labels for battery voltage, ultrasonic distance, and cliff status
        self.battery_label = QLabel('Battery Voltage: N/A', self)
        layout.addWidget(self.battery_label)

        self.ultrasonic_label = QLabel('Ultrasonic Distance: N/A', self)
        layout.addWidget(self.ultrasonic_label)

        self.cliff_label = QLabel('Cliff Status: N/A', self)
        layout.addWidget(self.cliff_label)

        # Button to get battery voltage
        self.get_battery_btn = QPushButton('Get Battery Voltage', self)
        self.get_battery_btn.clicked.connect(self.get_battery_voltage)
        layout.addWidget(self.get_battery_btn)

        # Button to get ultrasonic distance
        self.get_ultrasonic_btn = QPushButton('Get Ultrasonic Distance', self)
        self.get_ultrasonic_btn.clicked.connect(self.get_ultrasonic_distance)
        layout.addWidget(self.get_ultrasonic_btn)

        # Button to get cliff status
        self.get_cliff_btn = QPushButton('Get Cliff Status', self)
        self.get_cliff_btn.clicked.connect(self.get_cliff_status)
        layout.addWidget(self.get_cliff_btn)

        # Set up window
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.setGeometry(100, 100, 400, 600)

    # Command functions for controlling PiCar-X
    def forward(self):
        send_supported_func('forward', 50)
        print("Moving forward")

    def backward(self):
        send_supported_func('backward', 50)
        print("Moving backward")

    def stop(self):
        send_supported_func('stop')
        print("Stopping")

    # Camera pan and tilt controls
    def update_pan_angle(self):
        angle = self.pan_slider.value()
        send_supported_func('set_camera_pan_angle', angle)
        self.pan_label.setText(f'Camera Pan Angle: {angle}°')
        print(f"Set pan angle to {angle}")

    def update_tilt_angle(self):
        angle = self.tilt_slider.value()
        send_supported_func('set_camera_tilt_angle', angle)
        self.tilt_label.setText(f'Camera Tilt Angle: {angle}°')
        print(f"Set tilt angle to {angle}")

    # Status functions for getting sensor data
    def get_battery_voltage(self):
        send_supported_func('get_battery_voltage')
        time.sleep(2)  # Simulating a delay to receive the data
        self.battery_label.setText(f"Battery Voltage: {rx_retvals['battery_voltage']}")
        print(f"Battery Voltage: {rx_retvals['battery_voltage']}")

    def get_ultrasonic_distance(self):
        send_supported_func('get_ultrasonic_distance')
        time.sleep(2)
        self.ultrasonic_label.setText(f"Ultrasonic Distance: {rx_retvals['ultrasonic_distance']}")
        print(f"Ultrasonic Distance: {rx_retvals['ultrasonic_distance']}")

    def get_cliff_status(self):
        send_supported_func('get_cliff_status')
        time.sleep(2)
        self.cliff_label.setText(f"Cliff Status: {rx_retvals['cliff_status']}")
        print(f"Cliff Status: {rx_retvals['cliff_status']}")

    # Video feed handling
    def update_video_feed(self, frame_data):
        # Convert the byte data to an image
        np_arr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Update QLabel with the new frame
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))

    def receive_video_feed(self, client_socket):
        while True:
            try:
                # Receive the frame size
                frame_size = int.from_bytes(client_socket.recv(4), 'big')
                # Receive the actual frame data
                frame_data = b""
                while len(frame_data) < frame_size:
                    packet = client_socket.recv(frame_size - len(frame_data))
                    if not packet:
                        return  # Connection closed
                    frame_data += packet

                # Update video feed with the received frame
                self.update_video_feed(frame_data)

            except Exception as e:
                print(f"Error receiving video feed: {e}")
                break

    def start_bluetooth_thread(self):
        # Connect to the Bluetooth server and start receiving video
        server_addr = 'D8:3A:DD:E9:35:3E'
        server_port = 1
        client_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        client_socket.connect((server_addr, server_port))  # Make sure these match your PiCar-X setup
        self.video_thread = threading.Thread(target=self.receive_video_feed, args=(client_socket,))
        self.video_thread.start()

    def closeEvent(self, event):
        exit_event.set()
        self.video_thread.join()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = BluetoothControlWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
