const video = document.getElementById('video');
const startDetectionButton = document.getElementById('start-detection');
const errorMessage = document.getElementById('error-message');
const canvas = document.createElement('canvas');

// Access the webcam
navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        video.srcObject = stream;
        video.play();
    })
    .catch(err => {
        errorMessage.style.display = "block";
    });

startDetectionButton.addEventListener('click', () => {
    // Capture a single frame from the video feed
    const width = video.videoWidth;
    const height = video.videoHeight;
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, width, height);

    // Convert the frame to base64
    const frameData = canvas.toDataURL('image/jpeg');

    // Send the frame to the backend for processing
    fetch('{% url "process_frame" %}', {
        method: 'POST',
        body: JSON.stringify({ image: frameData }),
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.face && data.eyes.length > 0) {
            // Face and eyes detected, redirect to the dashboard
            alert('Face and eyes detected successfully. Redirecting to dashboard...');
            window.location.href = '{% url "dashboard" %}';
        } else {
            // No face or eyes detected, show an alert
            alert('Face or eyes not detected. Please try again.');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        alert('An error occurred during detection. Please try again.');
    });
});
