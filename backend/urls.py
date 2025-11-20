"""
URL Configuration for AI Study Tutor Django backend
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls, name='admin'),
    
    # Authentication endpoints
    path('api/register', views.register_user, name='register'),
    path('api/login', views.login_user, name='login'),
    path('api/logout', views.logout_user, name='logout'),
    path('api/user', views.get_user_info, name='user_info'),
    
    # API endpoints (require authentication)
    path('api/send-message', views.send_message, name='send_message'),
    path('api/generate-tts', views.generate_tts, name='generate_tts'),
    path('api/upload-file', views.upload_file, name='upload_file'),
    path('api/history', views.get_session_history, name='get_history'),
    path('api/sessions', views.list_sessions, name='list_sessions'),
    path('api/new-session', views.create_new_session, name='new_session'),
    path('api/delete-session', views.delete_session_view, name='delete_session'),
    path('api/reset-history', views.reset_history, name='reset_history'),
    path('api/reset-index', views.reset_index, name='reset_index'),
    path('api/transcribe', views.transcribe, name='transcribe'),
    
    # Public endpoints
    path('api/healthz', views.healthz, name='healthz'),
    
    # Frontend
    path('', views.root_redirect, name='root'),
    path('login', views.login_page, name='login_page'),
    path('register', views.register_page, name='register_page'),
    path('favicon.ico', views.favicon, name='favicon'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
