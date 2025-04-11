# analysis/urls.py
from django.urls import path
from . import views
from .views import display_dashboard # Ajoutez display_dashboard
from .views import download_report_view

urlpatterns = [
    path('request/scenario/', views.request_scenario_view, name='request_scenario'),
    path('request/confirmation/<int:request_id>/', views.request_confirmation_view, name='request_confirmation'),
    path('dashboard/<int:request_id>/', views.display_dashboard, name='dashboard'),
    path('download/report/<int:request_id>/<str:format>/', views.download_report_view, name='download_report'),
    # Optional processing page URL:
    # path('request/processing/<int:request_id>/', views.processing_view, name='processing'),
    # Dashboard URL will be added later:
    # path('dashboard/<int:request_id>/', views.display_dashboard, name='dashboard'),
]