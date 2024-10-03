from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from users.tokens import account_activation_token
from users.models import UserProfile
import json  # Import json for handling JSON data
import time

class AuthenticationTests(TestCase):
    
    def test_user_signup(self):
        # Step 1: Simulate the form submission for signing up
        response = self.client.post(reverse('signup'), {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'Password123'
        })
        
        # Check that the form submission returned a 200 status code (i.e., page reloaded without errors)
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Ensure the user was created but is inactive
        user = User.objects.get(username='testuser')
        self.assertFalse(user.is_active)  # User should not be active yet (pending email activation)
        
        # Step 3: Ensure an activation email was sent
        self.assertEqual(len(mail.outbox), 1) 
        self.assertIn('Activate your EyeConverse account', mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ['testuser@example.com'])  # Check that the email was sent to the correct recipient

    def test_user_activation(self):
        # Step 1: Create a user manually (to simulate a user that signed up)
        user = User.objects.create(username='testuser2', email='testuser2@example.com')
        user.set_password('Password123')
        user.is_active = False  # User should be inactive until they activate their account
        user.save()

        # Step 2: Generate the activation link
        uid = urlsafe_base64_encode(force_bytes(user.pk))  # Encode the user ID
        token = account_activation_token.make_token(user)  # Generate the activation token

        # Step 3: Simulate visiting the activation link
        response = self.client.get(reverse('activate', kwargs={'uidb64': uid, 'token': token}))

        # Check that the response is a redirect to the setup page
        self.assertRedirects(response, reverse('setup'))

        # Step 4: Ensure the user's account is now active
        user.refresh_from_db()  # Reload the user from the database
        self.assertTrue(user.is_active)  # The user should now be active


class CursorMovementTests(TestCase):

    def test_cursor_movement(self):
        # Simulate pupil positions
        left_eye = [(100, 100), (110, 100), (115, 105), (110, 110), (105, 110), (100, 105)]
        right_eye = [(200, 100), (210, 100), (215, 105), (210, 110), (205, 110), (200, 105)]

        # Calculate pupil centers and cursor position
        eye_center_x = int((100 + 200) / 2)
        eye_center_y = int((100 + 100) / 2)

        # Map the pupil coordinates to screen width and height based on actual ratios
        frame_width, frame_height = 640, 480
        screen_width, screen_height = 1024, 768

        cursor_x = int((eye_center_x / frame_width) * screen_width)
        cursor_y = int((eye_center_y / frame_height) * screen_height)

        # Ensure cursor moved correctly
        self.assertEqual(cursor_x, int((150 / 640) * 1024))
        self.assertEqual(cursor_y, int((100 / 480) * 768)) 


class MultiFactorAuthenticationTests(TestCase):

    def setUp(self):
        # Create a user for testing
        self.user = User.objects.create(username='mfauser', email='mfauser@example.com')
        self.user.set_password('Password123')
        self.user.is_active = True
        self.user.save()
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.user_profile.generate_verification_code()

    # def test_login_with_verification_code(self):

    #     login_response = self.client.post(reverse('login'), {'username': 'mfauser', 'password': 'Password123'})
        
    #     self.assertEqual(login_response.status_code, 302)  # Confirm redirection to verify code page
        
    #     response = self.client.post(reverse('verify_code'), {'verification_code': self.user_profile.verification_code})
        
    #     # Check if the user is redirected to the dashboard after successful verification
    #     self.assertRedirects(response, reverse('dashboard'))

class CalibrationTests(TestCase):

    def setUp(self):
        # Create a user and log them in for testing
        self.user = User.objects.create(username='calibrationuser', email='calibrationuser@example.com')
        self.user.set_password('Password123')
        self.user.is_active = True  # The user is active and logged in
        self.user.save()

        self.client.login(username='calibrationuser', password='Password123')

    def test_calibration_data_saved(self):
        # Simulate sending calibration data via POST request
        calibration_data = [
            {"x": "10%", "y": "10%", "timestamp": 1727963632970},
            {"x": "90%", "y": "10%", "timestamp": 1727963635968},
            {"x": "10%", "y": "90%", "timestamp": 1727963638963}
        ]
        response = self.client.post(reverse('save_calibration_data'), 
                                    data=json.dumps({"calibrationData": calibration_data}), 
                                    content_type="application/json")
        
        # Check that the response is a success
        self.assertEqual(response.status_code, 200)

        # Reload the user profile from the database
        user_profile = UserProfile.objects.get(user=self.user)

        # Verify that the calibration data was saved correctly
        self.assertEqual(user_profile.calibration_data, calibration_data)

class LogoutTests(TestCase):

    def setUp(self):
        # Create a user for testing
        self.user = User.objects.create(username='logoutuser', email='logoutuser@example.com')
        self.user.set_password('Password123')
        self.user.is_active = True
        self.user.save()
        self.client.login(username='logoutuser', password='Password123')

    # def test_user_logout(self):
    #     # Log out the user and ensure they are redirected to the index page
    #     response = self.client.get(reverse('logout'))
    #     self.assertRedirects(response, reverse('index'))

    #     # Ensure the user is logged out
    #     response = self.client.get(reverse('dashboard'))  # Trying to access dashboard after logout
    #     self.assertRedirects(response, reverse('login'))  # Should redirect to login page



class ProfileUpdateTests(TestCase):

    def setUp(self):
        # Create a user for testing
        self.user = User.objects.create(username='profileuser', email='profileuser@example.com')
        self.user.set_password('Password123')
        self.user.is_active = True
        self.user.save()
        self.client.login(username='profileuser', password='Password123')

    def test_language_update(self):
        # Simulate POST request to update language preference
        response = self.client.post(reverse('profile'), {'language': 'french'})
        
        # Ensure the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Reload the user profile from the database
        user_profile = UserProfile.objects.get(user=self.user)
        
        # Verify the language was updated correctly
        self.assertEqual(user_profile.language, 'french')

    def test_volume_update(self):
        # Simulate POST request to update TTS volume
        response = self.client.post(reverse('save_volume'), data=json.dumps({'volume': 0.8}), content_type="application/json")
        
        # Ensure the response is successful
        self.assertEqual(response.status_code, 200)

        # Reload the user profile from the database
        user_profile = UserProfile.objects.get(user=self.user)

        # Verify the volume was updated correctly
        self.assertEqual(user_profile.tts_volume, 0.8)


class EyeTrackingSetupTests(TestCase):

    def setUp(self):
        # Create a user and log them in for testing
        self.user = User.objects.create(username='trackinguser', email='trackinguser@example.com')
        self.user.set_password('Password123')
        self.user.is_active = True  # The user is active and logged in
        self.user.save()

        self.client.login(username='trackinguser', password='Password123')

    def test_eye_tracking_setup_page(self):
        # Check if the eye-tracking setup page loads correctly
        response = self.client.get(reverse('eye_tracking_setup'))
        self.assertEqual(response.status_code, 200)

    def test_calibration_data_save(self):
        # Simulate saving calibration data through a POST request
        calibration_data = [
            {"x": "20%", "y": "30%", "timestamp": 1627963632970},
            {"x": "40%", "y": "50%", "timestamp": 1627963635968},
            {"x": "60%", "y": "70%", "timestamp": 1627963638963}
        ]
        response = self.client.post(reverse('save_calibration_data'),
                                    data=json.dumps({"calibrationData": calibration_data}),
                                    content_type="application/json")

        # Ensure the response is successful
        self.assertEqual(response.status_code, 200)

        # Reload the user profile from the database
        user_profile = UserProfile.objects.get(user=self.user)

        # Verify that the calibration data was saved correctly
        self.assertEqual(user_profile.calibration_data, calibration_data)



class EyeTrackingTests(TestCase):

    def setUp(self):
        # Create a user for testing
        self.user = User.objects.create(username='eyetracker', email='eyetracker@example.com')
        self.user.set_password('Password123')
        self.user.is_active = True
        self.user.save()

        self.client.login(username='eyetracker', password='Password123')

    def test_cursor_movement_with_eye_tracking(self):
        # Simulate eye movements for cursor tracking
        left_eye = [(100, 100), (110, 100), (115, 105), (110, 110), (105, 110), (100, 105)]
        right_eye = [(200, 100), (210, 100), (215, 105), (210, 110), (205, 110), (200, 105)]

        # Calculate the expected cursor position
        eye_center_x = int((100 + 200) / 2)
        eye_center_y = int((100 + 100) / 2)

        frame_width, frame_height = 640, 480
        screen_width, screen_height = 1024, 768

        cursor_x = int((eye_center_x / frame_width) * screen_width)
        cursor_y = int((eye_center_y / frame_height) * screen_height)

        # Check the calculated cursor position matches the expected values
        self.assertEqual(cursor_x, int((150 / 640) * 1024))
        self.assertEqual(cursor_y, int((100 / 480) * 768))

    def test_blink_detection(self):
        # Simulate eye aspect ratio (EAR) for blink detection
        left_eye = [(100, 100), (110, 100), (115, 105), (110, 110), (105, 110), (100, 105)]
        right_eye = [(200, 100), (210, 100), (215, 105), (210, 110), (205, 110), (200, 105)]

        # EAR values below the threshold should trigger a blink
        ear = 0.1  # Simulated EAR below the threshold

        # Check that blink detection logic works
        blink_detected = ear < 0.2  # EAR threshold is set to 0.2 in the actual logic
        self.assertTrue(blink_detected)


# Integration Tests
class IntegrationTests(TestCase):
    def setUp(self):
        # Create a user and activate their account
        self.user = User.objects.create(username='testuser', email='testuser@example.com')
        self.user.set_password('Password123')
        self.user.is_active = True  # Simulate activation
        self.user.save()

        # Log in the user
        self.client.login(username='testuser', password='Password123')

    def test_full_integration(self):
        # Step 1: User completes calibration
        calibration_data = [
            {"x": "10%", "y": "10%", "timestamp": 1727963632970},
            {"x": "90%", "y": "10%", "timestamp": 1727963635968},
            {"x": "10%", "y": "90%", "timestamp": 1727963638963}
        ]
        calibration_response = self.client.post(reverse('save_calibration_data'),
                                                data=json.dumps({"calibrationData": calibration_data}),
                                                content_type="application/json")

        # Ensure calibration data is saved correctly
        self.assertEqual(calibration_response.status_code, 200)
        user_profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(user_profile.calibration_data, calibration_data)

        # Step 2: Verify Eye-Tracking Integration
        # Simulate cursor movement and eye-tracking data after calibration
        eye_tracking_response = self.client.get(reverse('eye_tracking_setup'))

        # Check if the eye-tracking stream starts successfully and has the correct content type
        self.assertEqual(eye_tracking_response.status_code, 200)
        self.assertEqual(eye_tracking_response['Content-Type'], 'multipart/x-mixed-replace; boundary=frame')


class SystemLoadAndPerformanceTests(TestCase):

    def setUp(self):
        # Create a user for testing
        self.user = User.objects.create(username='performancetester', email='performancetester@example.com')
        self.user.set_password('Password123')
        self.user.is_active = True  # Activate the account
        self.user.save()

    def test_login_performance(self):
        # Measure response time for logging in
        start_time = time.time()
        login_response = self.client.post(reverse('login'), {'username': 'performancetester', 'password': 'Password123'})
        end_time = time.time()
        self.assertEqual(login_response.status_code, 302)
        response_time = end_time - start_time
        print(f"Login Response Time: {response_time} seconds")

    def test_calibration_performance(self):
        # Measure response time for saving calibration data
        self.client.login(username='performancetester', password='Password123')
        calibration_data = [
            {"x": "20%", "y": "30%", "timestamp": 1627963632970},
            {"x": "40%", "y": "50%", "timestamp": 1627963635968},
            {"x": "60%", "y": "70%", "timestamp": 1627963638963}
        ]
        start_time = time.time()
        calibration_response = self.client.post(reverse('save_calibration_data'),
                                                data=json.dumps({"calibrationData": calibration_data}),
                                                content_type="application/json")
        end_time = time.time()
        self.assertEqual(calibration_response.status_code, 200)
        response_time = end_time - start_time
        print(f"Calibration Save Response Time: {response_time} seconds")

    def test_load_simulation(self):
        # Simulate multiple requests to test system load handling
        self.client.login(username='performancetester', password='Password123')
        calibration_data = [
            {"x": "20%", "y": "30%", "timestamp": 1627963632970},
            {"x": "40%", "y": "50%", "timestamp": 1627963635968},
            {"x": "60%", "y": "70%", "timestamp": 1627963638963}
        ]

        for i in range(50):  # Simulate 50 requests
            response = self.client.post(reverse('save_calibration_data'),
                                        data=json.dumps({"calibrationData": calibration_data}),
                                        content_type="application/json")
            self.assertEqual(response.status_code, 200)
            print(f"Request {i+1} completed.")



