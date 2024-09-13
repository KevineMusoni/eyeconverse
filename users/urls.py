from django.urls import path, include
from .views import signup_view, login_view, logout_view, activate, dashboard_view, verify_code, setup_view, get_cursor_position, eye_tracking_setup, get_highlighted_key, confirm_eye_tracking, profile_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('activate/<uidb64>/<token>/', activate, name='activate'),  # Activation link
    path('dashboard/', dashboard_view, name='dashboard'),
    path('verify_code/', verify_code, name='verify_code'), 
    path('setup/', setup_view, name='setup'),
    path('eye_tracking_setup/', eye_tracking_setup, name='eye_tracking_setup'),
    path('confirm_eye_tracking/', confirm_eye_tracking, name='confirm_eye_tracking'),
    path('eye_tracking_feed/', eye_tracking_setup, name='eye_tracking_feed'),
    path('get_cursor_position/', get_cursor_position, name='get_cursor_position'),
    path('get_highlighted_key/', get_highlighted_key, name='get_highlighted_key'),
     path('profile/', profile_view, name='profile'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)