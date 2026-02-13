# lala/urls.py
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tracking.urls')),  # Include the URLs from the tracking app
      # Add a URL pattern for the root (home) page
]
