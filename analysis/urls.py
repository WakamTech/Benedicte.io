# analysis/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('request/scenario/', views.request_scenario_view, name='request_scenario'),
    path('request/confirmation/<int:request_id>/', views.request_confirmation_view, name='request_confirmation'),
    # Optional processing page URL:
    # path('request/processing/<int:request_id>/', views.processing_view, name='processing'),
    # Dashboard URL will be added later:
    # path('dashboard/<int:request_id>/', views.display_dashboard, name='dashboard'),
]