# content/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('faq/', views.faq_view, name='faq'),
    # Ajoutez ici les URLs pour Contact, CGV, Politique...
]