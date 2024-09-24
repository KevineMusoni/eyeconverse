
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from .models import UserProfile
from .tokens import account_activation_token
import random
import cv2
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render
import dlib
import os
from django.conf import settings
import numpy as np

# Load Dlib's pre-trained facial landmark detector
detector = dlib.get_frontal_face_detector()
predictor_path = os.path.join(settings.BASE_DIR, 'users', 'shape_predictor_68_face_landmarks.dat')
predictor = dlib.shape_predictor(predictor_path)

# User Registration View
def signup_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        # Validation checks for username and email (omitted here for brevity)

        # Create inactive user
        user = User.objects.create(username=username, email=email, password=make_password(password))
        user.is_active = False
        user.save()

        # Send activation email
        current_site = get_current_site(request)
        mail_subject = 'Activate your EyeConverse account.'
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
        activation_link = reverse('activate', kwargs={'uidb64': uid, 'token': token})
        activation_url = f'http://{current_site.domain}{activation_link}'

        # Render the message
        message = render_to_string('activation_email.txt', {
            'user': user,
            'activation_url': activation_url,
        })

        # **Send the email here**
        send_mail(
            mail_subject, 
            message, 
            'noreply@eyeconverse.com',  # Sender email
            [email],  # Recipient email
            fail_silently=False
        )

        # Notify user and stay on the signup page
        messages.success(request, 'Account created! Please check your email to activate your account.')
        return render(request, 'signup.html')

    return render(request, 'signup.html')


# Email Activation View
def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been activated successfully!')

        # Redirect to setup page
        return redirect('setup')
    else:
        messages.error(request, 'Activation link is invalid!')
        return redirect('signup')


# Login View with Verification Code
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            # User successfully authenticated, now proceed with login
            login(request, user)

            # Generate verification code for 2FA
            user_profile = UserProfile.objects.get(user=user)
            user_profile.generate_verification_code()

            # Send verification code via email
            send_mail(
                'Your Verification Code',
                f'Your code is {user_profile.verification_code}',
                'noreply@eyeconverse.com',
                [user.email],
                fail_silently=False,
            )

            # Redirect to the verification page
            return redirect('verify_code')
        else:
            # Wrong username or password, redirect back to login page
            messages.error(request, 'Invalid username or password.')
            return redirect('login')  # Ensure this redirects to the login page

    return render(request, 'login.html')



# Verification Code View
def verify_code(request):
    if request.method == 'POST':
        code = request.POST.get('verification_code')
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.verification_code == code:
            messages.success(request, 'Verification successful!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid verification code.')
            return redirect('verify_code')
    else:
        return render(request, 'verify_code.html') 


# Logout View
def logout_view(request):
    logout(request)
    return redirect('index')


# Dashboard View
def dashboard_view(request):
    return render(request, 'dashboard.html')


# Setup Page View (for when the user activates their account)
def setup_view(request):
    return render(request, 'setup.html')


# Function to calculate the Eye Aspect Ratio (EAR)
def eye_aspect_ratio(eye):
    # Compute the Euclidean distances between the two sets of vertical eye landmarks (x, y)-coordinates
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])

    # Compute the Euclidean distance between the horizontal eye landmark (x, y)-coordinates
    C = np.linalg.norm(eye[0] - eye[3])

    # Compute the eye aspect ratio
    ear = (A + B) / (2.0 * C)
    return ear

# Constants for blink detection
EYE_AR_THRESH = 0.2  # Threshold for considering a blink
EYE_AR_CONSEC_FRAMES = 2  # Number of consecutive frames where the eye ratio is below threshold

# Initialize counters for blinks
blink_counter = 0
blink_detected = False
blink_display_frames = 5  # Show "Blink detected" for 5 frames after a blink is detected
blink_display_counter = 0  # Counts how long to display the "Yes" status
# Initial position of the virtual cursor
cursor_x, cursor_y = 300, 300  # Starting in the middle of the screen
# Function to generate frames from the webcam and sync cursor movement with eye movement
def generate_frames():
    global cursor_x, cursor_y
    cap = cv2.VideoCapture(0)  # Capture from the webcam (0 is the default camera)
    global blink_counter, blink_detected, blink_display_counter

    screen_width = 1024
    screen_height = 768

    # Euclidean distance function
    def euclidean_distance(x1, y1, x2, y2):
        return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # Step 1: Convert the frame to grayscale (better for face detection)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Step 2: Detect faces using Dlib’s face detector
        faces = detector(gray)
        
        for face in faces:
            # Step 3: Get the facial landmarks for each face
            landmarks = predictor(gray, face)

            # Extract the left and right eye coordinates
            left_eye = np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in range(36, 42)])
            right_eye = np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in range(42, 48)])
            
            # Step 4: Extract the left and right eye coordinates from the facial landmarks
            left_eye = np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in range(36, 42)])
            right_eye = np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in range(42, 48)])

            # Step 5: Calculate the center of each pupil using Euclidean distance
            pupil_left_x = np.mean(left_eye[:, 0]).astype(int)
            pupil_left_y = np.mean(left_eye[:, 1]).astype(int)
            pupil_right_x = np.mean(right_eye[:, 0]).astype(int)
            pupil_right_y = np.mean(right_eye[:, 1]).astype(int)

            # Use Euclidean distance to calculate the distance between pupils
            eye_center_x = int((pupil_left_x + pupil_right_x) / 2)
            eye_center_y = int((pupil_left_y + pupil_right_y) / 2)

            # Draw the pupil centers (Green dots)
            cv2.circle(frame, (pupil_left_x, pupil_left_y), 3, (0, 255, 0), -1)  # Left pupil
            cv2.circle(frame, (pupil_right_x, pupil_right_y), 3, (0, 255, 0), -1)  # Right pupil

            # Map eye center coordinates to screen dimensions for cursor movement
            cursor_x = int((eye_center_x / frame.shape[1]) * screen_width)
            cursor_y = int((eye_center_y / frame.shape[0]) * screen_height)

            # Step 6: Blink detection logic based on EAR (Eye Aspect Ratio) threshold
            left_ear = eye_aspect_ratio(left_eye)
            right_ear = eye_aspect_ratio(right_eye)
            ear = (left_ear + right_ear) / 2.0

            if ear < EYE_AR_THRESH:
                blink_counter += 1
            else:
                if blink_counter >= EYE_AR_CONSEC_FRAMES:
                    blink_detected = True
                    blink_counter = 0
                else:
                    blink_counter = 0

            # If blink detected, log a message (replace this with actual action logic later)
            if blink_detected:
                highlighted_key = highlight_key(cursor_x, cursor_y)  # Get highlighted key
                if highlighted_key:
                    print(f"Blink and key detected. Inserting key: {highlighted_key}")
                    perform_click_action(highlighted_key)  # Insert key into textarea
                blink_display_counter = blink_display_frames
                blink_detected = False

            if blink_display_counter > 0:
                blink_display_counter -= 1

            # Highlight the key based on cursor position
            highlighted_key = highlight_key(cursor_x, cursor_y)
            if highlighted_key:
                update_key_style(highlighted_key)

            # Draw eye landmarks and rectangles around detected faces
            for (x, y) in np.concatenate((left_eye, right_eye)):
                cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

            # Display cursor position and blinking status
            cv2.putText(frame, f"Cursor Pos: ({int(cursor_x)}, {int(cursor_y)})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            # Update the blinking status on the frame
            blinking_status = "Yes" if blink_display_counter > 0 else "No"
            cv2.putText(frame, f"Blinking Status: {blinking_status}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # Decrease the display counter, so blinking status resets to "No" after a few frames
            if blink_display_counter > 0:
                blink_display_counter -= 1

        # Encode the frame in JPEG format
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        # Yield the frame for streaming
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
# Highlight the key based on cursor position
def highlight_key(cursor_x, cursor_y):
    # Define key positions and their bounding boxes
    keys = {
        '1': (100, 200, 160, 260),
        '2': (160, 200, 220, 260),
        '3': (220, 200, 280, 260),
        '4': (280, 200, 340, 260),
        '5': (340, 200, 400, 260),
        'q': (100, 260, 160, 320),
        'w': (160, 260, 220, 320),
        'e': (220, 260, 280, 320),
        'r': (280, 260, 340, 320),
        't': (340, 260, 400, 320),
        # Add other keys with their bounding boxes
    }

    # Iterate through the keys and check if the cursor is within the key's bounding box
    for key, (left, top, right, bottom) in keys.items():
        if left <= cursor_x <= right and top <= cursor_y <= bottom:
            return key  # Return the key that the cursor is hovering over
    
    return None  # Return None if no key is being hovered over


# Function to simulate the click action when a blink happens on a highlighted key
def perform_click_action(key):
    print(f"Performing click action on key: {key}")
    return JsonResponse({'clicked_key': key})  # Send the clicked key back to the frontend


# Update the style of the highlighted key
def update_key_style(key):
    return JsonResponse({'highlighted_key': key})
        

# Django view for rendering the webcam feed
def eye_tracking_setup(request):
    return StreamingHttpResponse(generate_frames(), content_type='multipart/x-mixed-replace; boundary=frame')

# Setup Page View (for when the user activates their account)
def setup_view(request):
    return render(request, 'setup.html')

def confirm_eye_tracking(request):
    if request.method == 'POST':
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.setup_confirmed = True
        user_profile.save()

        messages.success(request, 'Eye tracking setup confirmed!')
        return redirect('dashboard')  # Redirect the user to the dashboard after confirmation
    return redirect('setup')

def get_cursor_position(request):
    global cursor_x, cursor_y
    return JsonResponse({'x': cursor_x, 'y': cursor_y})


def get_highlighted_key(request):
    global cursor_x, cursor_y  # Ensure you are using the correct cursor position 
    highlighted_key = highlight_key(cursor_x, cursor_y)
    return JsonResponse({'highlighted_key': highlighted_key})  # Return the dynamically fetched key



# Profile Page View
def profile_view(request):
    user_profile = UserProfile.objects.get(user=request.user)
    context = {
        'user': request.user,
        'user_profile': user_profile,
    }
    return render(request, 'profile.html', context)




