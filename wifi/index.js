var server_port = 65432;
var server_addr = "10.0.0.22";   // the IP address of your Raspberry PI

// Function to connect to the server and send a message
function client(message){
    console.log("Client function called with message:", message);
    const net = require('net'); // Require the 'net' module to create a TCP connection
    var input = message || document.getElementById("myName").value; // Get input from the user, or use the provided message parameter

    console.log("Attempting to connect to:", server_addr, "on port:", server_port);

    // Create a TCP connection to the Raspberry Pi server
    const client = net.createConnection({ port: server_port, host: server_addr }, () => {
        console.log('Connected to server!');
        client.write(`${input}\r\n`);
        console.log("Sent message to server:", input);
    });
    
    // Handle data received from the server
    client.on('data', (data) => {
        console.log("Received data from server:", data.toString());

         // parse the data from the server and update the display
        try {
            const parsedData = JSON.parse(data);
            if (parsedData.greeting) {
                document.getElementById("greet_from_server").innerHTML = parsedData.greeting;
            } else if (parsedData.status) {
                document.getElementById("greet_from_server").innerHTML = parsedData.status;
                updateDataDisplay(parsedData);
            } else {
                updateDataDisplay(parsedData);
            }
        // Handle any errors during data parsing
        } catch (error) {
            console.error("Error parsing server response:", error);
            document.getElementById("greet_from_server").innerHTML = "Error processing server response";
        }
        client.end();
    });

    client.on('end', () => {
        console.log('Disconnected from server');
    });

    client.on('error', (err) => {
        console.error('Connection error:', err);
    });
}

function sendCommand(command) {
    console.log("sendCommand called with:", command);
    client(command);
}

// Function to update the displayed data (distance, grayscale, and speed)
function updateDataDisplay(data) {
    console.log("Updating data display with:", data);
    // document.getElementById("speed").textContent = data.speed ? data.speed.toFixed(2) : "N/A";
    document.getElementById("distance").textContent = data.distance ? data.distance.toFixed(2) : "N/A";
    document.getElementById("grayscale").textContent = data.grayscale ? data.grayscale.join(', ') : "N/A";
    if (data.speed !== undefined) {
        document.getElementById("currentSpeed").textContent = `Speed: ${data.speed}`;
    }
}

// Function to toggle the video feed display
function toggleVideo() {
    const videoFeed = document.getElementById("videoFeed");
    const toggleBtn = document.getElementById("toggleVideoBtn");
    if (videoFeed.style.display === "none") {
        videoFeed.style.display = "block";
        toggleBtn.textContent = "Hide Video";
        if (!videoFeed.querySelector('img')) {
            const img = document.createElement('img');
            img.src = `http://${server_addr}:9000/video_feed`;
            img.alt = "Camera Feed";
            videoFeed.appendChild(img);
        }
    } else {
        videoFeed.style.display = "none";
        toggleBtn.textContent = "Show Video";
    }
}

// function getDetectionResult() {
//     fetch(`http://${server_addr}:9000/detection_result`)
//         .then(response => response.json())
//         .then(data => {
//             const detectionResult = document.getElementById('detectionResult');
//             if (data.detected) {
//                 detectionResult.textContent = `Detection: ${data.class_name} (Score: ${data.class_score.toFixed(2)})`;
//             } else {
//                 detectionResult.textContent = 'No object detected';
//             }
//         })
//         .catch(error => console.error('Error fetching detection result:', error));
// }

// setInterval(getDetectionResult, 1000);

// Function to greet the user based on the input name
function greeting(){
    console.log("Greeting function called");
    var name = document.getElementById("myName").value;
    console.log("Input name:", name);
    document.getElementById("greet").innerHTML = "Hello " + name + " !";
    client(name);
}

// Function to set up event listeners for buttons on the page
function setupEventListeners() {
    console.log("Setting up event listeners");
    document.getElementById("greetButton").addEventListener('click', greeting);
    document.getElementById("forward").addEventListener('click', () => sendCommand('forward'));
    document.getElementById("backward").addEventListener('click', () => sendCommand('backward'));
    document.getElementById("left").addEventListener('click', () => sendCommand('left'));
    document.getElementById("right").addEventListener('click', () => sendCommand('right'));
    document.getElementById("stop").addEventListener('click', () => sendCommand('stop'));
    document.getElementById("getData").addEventListener('click', () => sendCommand('getData'));
    document.getElementById("toggleVideoBtn").addEventListener('click', toggleVideo);
    document.getElementById("speedUp").addEventListener('click', () => sendCommand('speedUp'));
    document.getElementById("speedDown").addEventListener('click', () => sendCommand('speedDown'));
}

document.addEventListener('DOMContentLoaded', setupEventListeners);