import bluetooth
import cv2
import numpy as np
import json
import threading
import tkinter as tk

# Variables to hold the command state
current_command = ""
current_speed = 30  # Default speed

def connect_to_server():
    server_address = "D8:3A:DD:78:0F:5C"  # Replace with your Raspberry Pi's Bluetooth address
    port = 1  # RFCOMM port
    socket_ = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    socket_.connect((server_address, port))
    return socket_

def receive_video_feed(socket_):
    while True:
        try:
            # Receive the frame size
            size_data = socket_.recv(4)
            if not size_data:
                print("No data received, closing the connection.")
                break

            # Read the frame size
            frame_size = int.from_bytes(size_data, 'big')

            # Receive the frame data
            frame_data = b""
            while len(frame_data) < frame_size:
                frame_data += socket_.recv(frame_size - len(frame_data))

            # Decode the frame
            np_arr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            # Display the frame
            cv2.imshow('Camera Feed', frame)

            # After the frame, receive the car stats JSON size
            stats_size_data = socket_.recv(4)
            if not stats_size_data:
                print("No stats data received, closing connection.")
                break

            # Read the stats size
            stats_size = int.from_bytes(stats_size_data, 'big')

            # Receive the car stats data
            stats_data = b""
            while len(stats_data) < stats_size:
                stats_data += socket_.recv(stats_size - len(stats_data))

            # Decode and print car stats
            car_stats = json.loads(stats_data.decode('utf-8'))
            print("Car Stats:", car_stats)

            # Handle keypress events
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        except Exception as e:
            print("Error receiving video feed:", e)
            break



def send_command(socket_):
    global current_command
    try:
        # Send the current command
        if current_command:
            socket_.send(current_command.encode('utf-8'))
    except Exception as e:
        print(f"Error sending command: {e}")

class CarControlApp:
    def __init__(self, socket_):
        self.socket_ = socket_
        self.root = tk.Tk()
        self.root.title("Car Control")

        # Create buttons for controls
        self.up_button = tk.Button(self.root, text="Move Forward", command=self.move_forward)
        self.up_button.pack(pady=5)

        self.down_button = tk.Button(self.root, text="Move Backward", command=self.move_backwards)
        self.down_button.pack(pady=5)

        self.left_button = tk.Button(self.root, text="Move Left", command=self.move_left)
        self.left_button.pack(pady=5)

        self.right_button = tk.Button(self.root, text="Move Right", command=self.move_right)
        self.right_button.pack(pady=5)

        # Create speed control slider
        self.speed_scale = tk.Scale(self.root, from_=10, to=60, orient=tk.HORIZONTAL, label="Speed", command=self.update_speed)
        self.speed_scale.set(current_speed)  # Set the default speed
        self.speed_scale.pack(pady=10)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_speed(self, value):
        global current_speed
        current_speed = int(value)  # Update the speed based on the slider

    def move_forward(self):
        global current_command
        current_command = f"move_forward({current_speed})"
        send_command(self.socket_)

    def move_backwards(self):
        global current_command
        current_command = f"move_backwards({current_speed})"
        send_command(self.socket_)

    def move_left(self):
        global current_command
        current_command = f"move_left({current_speed})"
        send_command(self.socket_)

    def move_right(self):
        global current_command
        current_command = f"move_right({current_speed})"
        send_command(self.socket_)

    def on_close(self):
        self.socket_.close()  # Close the socket connection
        cv2.destroyAllWindows()  # Close all OpenCV windows
        self.root.quit()

    def run(self):
        self.root.mainloop()

def main():
    # Create the app first
    app = CarControlApp(None)  # Temporarily pass None

    # Connect to server
    socket_ = connect_to_server()
    app.socket_ = socket_  # Assign socket to the app

    # Start the video feed in a separate thread
    video_thread = threading.Thread(target=receive_video_feed, args=(socket_,))
    video_thread.start()

    # Run the Tkinter app
    app.run()

    # Ensure that the video thread is joined before exiting
    video_thread.join()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

