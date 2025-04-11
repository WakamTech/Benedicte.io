# analysis/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse # Temporary
from .models import ScenarioRequest
from .forms import ScenarioRequestForm
from company.models import CompanyProfile # Need to link the profile

@login_required
def request_scenario_view(request):
    try:
        # Get the company profile associated with the logged-in user
        company_profile = request.user.company_profile
    except CompanyProfile.DoesNotExist:
        # Handle case where profile doesn't exist (shouldn't happen if onboarding is mandatory)
        # Maybe redirect back to the first step of onboarding?
        return redirect('company_profile_step') # Redirect to company profile creation

    if request.method == 'POST':
        form = ScenarioRequestForm(request.POST)
        if form.is_valid():
            # Create the request object but don't save to DB yet
            scenario_request = form.save(commit=False)
            # Assign the user and the company profile
            scenario_request.user = request.user
            scenario_request.company_profile = company_profile
            # Set initial status
            scenario_request.status = 'pending' # Or 'processing' if we simulate immediate start
            scenario_request.save()

            # --- Placeholder for Triggering Analysis ---
            # In Phase 4, we will call backend services here.
            # For now, let's just simulate completion immediately
            # and redirect to a future dashboard URL (or home for now).

            # Simulate processing and completion for testing purposes:
            scenario_request.status = 'completed' # Simulate it finished quickly
            scenario_request.save()

            # Redirect to the dashboard (when it exists)
            # return redirect(reverse('dashboard', args=[scenario_request.id]))
            # For now, redirect to a simple confirmation or home
            return redirect(reverse('request_confirmation', args=[scenario_request.id]))

    else:
        form = ScenarioRequestForm()

    context = {
        'form': form,
        'step_title': "Étape 5: Quel est votre projet ?"
    }
    return render(request, 'analysis/request_scenario.html', context)

@login_required
def request_confirmation_view(request, request_id):
    # Simple confirmation page
    scenario_request = get_object_or_404(ScenarioRequest, id=request_id, user=request.user)
    context = {
        'request_id': scenario_request.id,
        'request_status': scenario_request.get_status_display(),
        'step_title': "Demande d'analyse soumise"
        }
    # In future, this might link to the dashboard:
    # context['dashboard_url'] = reverse('dashboard', args=[scenario_request.id])
    return render(request, 'analysis/request_confirmation.html', context)

# --- Optional: Processing View (if analysis takes time) ---
# @login_required
# def processing_view(request, request_id):
#     scenario_request = get_object_or_404(ScenarioRequest, id=request_id, user=request.user)
#     # You might use AJAX here to check status or just show a waiting message
#     context = {'request_id': scenario_request.id}
#     return render(request, 'analysis/processing.html', context)