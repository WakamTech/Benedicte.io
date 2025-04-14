# company/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse # Import reverse
from .models import CompanyProfile # Import CompanyProfile model
from .forms import (
    CompanyProfileForm,
    FinancialDataFormSet,
    ChargeFormSet,
    ProductServiceFormSet
)

# Helper function to get or create company profile for the user
def get_or_create_company_profile(user):
    profile, created = CompanyProfile.objects.get_or_create(user=user)
    return profile

@login_required
def company_profile_step(request):
    profile = get_or_create_company_profile(request.user)
    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            # Redirect to the next step (financials)
            return redirect('company_financials_step')
    else:
        form = CompanyProfileForm(instance=profile)

    context = {'form': form, 'step_title': "Étape 1/5 : Informations sur l'entreprise", 'next_step_url': reverse('company_financials_step')}
    return render(request, 'company/onboarding_step.html', context)

@login_required
def company_financials_step(request):
    profile = get_or_create_company_profile(request.user)
    if request.method == 'POST':
        formset = FinancialDataFormSet(request.POST, instance=profile)
        if formset.is_valid():
            formset.save()
            # Redirect to the next step (charges)
            return redirect('company_charges_step')
    else:
        formset = FinancialDataFormSet(instance=profile)

    context = {'formset': formset, 'step_title': "Étape 2/5 : Données Financières (CA Annuel)",'prev_step_url': reverse('company_profile_step'), 'next_step_url': reverse('company_charges_step')}
    return render(request, 'company/onboarding_formset_step.html', context)

@login_required
def company_charges_step(request):
    profile = get_or_create_company_profile(request.user)
    if request.method == 'POST':
        formset = ChargeFormSet(request.POST, instance=profile)
        if formset.is_valid():
            formset.save()
            # Redirect to the next step (products/services)
            return redirect('company_products_step')
    else:
        formset = ChargeFormSet(instance=profile)

    context = {'formset': formset, 'step_title': "Étape 3/5 : Charges Fixes et Variables",'prev_step_url': reverse('company_financials_step'), 'next_step_url': reverse('company_products_step')}
    return render(request, 'company/onboarding_formset_step.html', context)

@login_required
def company_products_step(request):
    profile = get_or_create_company_profile(request.user)
    if request.method == 'POST':
        formset = ProductServiceFormSet(request.POST, instance=profile)
        if formset.is_valid():
            formset.save()
            # Redirect to the next step (Scenario Request - Phase 3)
            # We don't have this URL yet, let's redirect home for now
            # Replace 'home' with the actual next step URL later
            return redirect(reverse('request_scenario')) # Needs Phase 3 URL 'request_scenario'
    else:
        formset = ProductServiceFormSet(instance=profile)

    context = {'formset': formset, 'step_title': "Étape 4/5 : Produits / Services Principaux", 'prev_step_url': reverse('company_charges_step'), 'next_step_url': reverse('request_scenario')}
    return render(request, 'company/onboarding_formset_step.html', context)