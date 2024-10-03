from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import random

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    setup_confirmed = models.BooleanField(default=False)
    calibration_data = models.JSONField(null=True, blank=True)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    language = models.CharField(max_length=20, default='english')
    tts_volume = models.FloatField(default=1.0)
    
    def generate_verification_code(self):
        """Generate a random 6-digit code."""
        self.verification_code = str(random.randint(100000, 999999))
        self.save()

# Create or update the UserProfile whenever a User is created
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.userprofile.save()
