# content/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('faq/', views.faq_view, name='faq'),
    path('contact/', views.contact_view, name='contact'),
    path('politique-confidentialite/', views.privacy_policy_view, name='privacy_policy'),
    path('cgv/', views.terms_conditions_view, name='terms_conditions'),
    path('tarifs/', views.pricing_view, name='pricing'),
    path('mentions-legales/', views.legal_notice_view, name='legal_notice'),
]