import sys
import threading
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QLabel, QSlider, QWidget
from PyQt5.QtCore import Qt
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
 
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
 
        self.setGeometry(100, 100, 400, 400)
 
    def forward(self):
        send_supported_func('forward', 50)
        print("Moving forward")
 
    def backward(self):
        send_supported_func('backward', 50)
        print("Moving backward")
 
    def stop(self):
        send_supported_func('stop')
        print("Stopping")
 
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
 
    def get_battery_voltage(self):
        send_supported_func('get_battery_voltage')
        time.sleep(2)  
        self.battery_label.setText(f"Battery Voltage: {rx_retvals['get_battery_voltage']}")
        print(f"Battery Voltage: {rx_retvals['get_battery_voltage']}")
 
    def get_ultrasonic_distance(self):
        send_supported_func('get_ultrasonic_distance')
        time.sleep(2)  
        self.ultrasonic_label.setText(f"Ultrasonic Distance: {rx_retvals['get_ultrasonic_distance']}")
        print(f"Ultrasonic Distance: {rx_retvals['get_ultrasonic_distance']}")
 
    def get_cliff_status(self):
        send_supported_func('get_cliff_status')
        time.sleep(2)  
        self.cliff_label.setText(f"Cliff Status: {rx_retvals['get_cliff_status']}")
        print(f"Cliff Status: {rx_retvals['get_cliff_status']}")
 
    def start_bluetooth_thread(self):
        self.bt_thread = threading.Thread(target=start_client)
        self.bt_thread.start()
 
    def closeEvent(self, event):
        exit_event.set()
        self.bt_thread.join()
        event.accept()
 
def main():
    app = QApplication(sys.argv)
    window = BluetoothControlWindow()
    window.show()
    sys.exit(app.exec_())
 
if __name__ == '__main__':
    main()
 