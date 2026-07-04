from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login as django_login, logout as django_logout
from django.utils.http import url_has_allowed_host_and_scheme
from services.auth import (
    initiate_google_login,
    handle_oauth_callback,
    extract_identity,
    synchronize_user,
)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")
    return render(request, "accounts/login.html")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")
    return render(request, "accounts/signup.html")


def reset_password_view(request):
    return render(request, "accounts/reserpassword.html")


def google_login_initiate(request):
    """
    Redirects the user to the Supabase Google OAuth login page.
    Stores standard 'next' redirect query parameter in the session.
    """
    try:
        next_url = request.GET.get("next")
        if next_url:
            request.session["next_redirect"] = next_url
            
        callback_url = request.build_absolute_uri(reverse("accounts:google_callback"))
        redirect_url = initiate_google_login(request, callback_url)
        return redirect(redirect_url)
    except Exception as e:
        messages.error(request, f"Failed to initiate Google sign-in: {str(e)}")
        return redirect("accounts:login")


def google_login_callback(request):
    """
    Handles callback redirect from Supabase/Google authentication.
    Performs JWT validation, syncs identity to Django user model, and establishes session.
    """
    error_name = request.GET.get("error")
    error_desc = request.GET.get("error_description")
    if error_name:
        messages.error(request, f"Google authentication failed: {error_desc or error_name}")
        if request.user.is_authenticated:
            return redirect("dashboard:dashboard")
        return redirect("accounts:login")

    code = request.GET.get("code")
    state = request.GET.get("state")
    
    if not code or not state:
        messages.error(request, "Invalid authentication response: missing code or state.")
        if request.user.is_authenticated:
            return redirect("dashboard:dashboard")
        return redirect("accounts:login")
        
    try:
        # 1. Exchange OAuth code for Supabase JWT claims
        claims = handle_oauth_callback(request, code, state)
        
        # 2. Extract normalized identity claims
        identity = extract_identity(claims)
        
        # 3. Synchronize user in Django database
        user = synchronize_user(identity)
        
        # 4. Standard Django session login
        django_login(request, user)
        
        # 5. Cycle key immediately to avoid session fixation vulnerability
        request.session.cycle_key()
        
        # 6. Store lightweight identifier for the login provider
        request.session["oauth_provider"] = identity.get("provider", "google")
        
        # 7. Remove temporary OAuth values
        request.session.pop("supabase_code_verifier", None)
        request.session.pop("supabase_oauth_state", None)
        
        # 8. Retrieve redirect url matching next parameter, default to dashboard
        next_url = request.session.pop("next_redirect", None)
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()
        ):
            redirect_to = next_url
        else:
            redirect_to = reverse("dashboard:dashboard")
            
        messages.success(request, "Successfully authenticated!")
        return redirect(redirect_to)
        
    except ValueError as e:
        messages.error(request, str(e))
        if request.user.is_authenticated:
            return redirect("dashboard:dashboard")
        return redirect("accounts:login")
    except Exception as e:
        messages.error(request, f"Authentication error: {str(e)}")
        if request.user.is_authenticated:
            return redirect("dashboard:dashboard")
        return redirect("accounts:login")


def logout_view(request):
    """
    Clears local Django session and authentication variables.
    """
    django_logout(request)
    messages.success(request, "Successfully logged out.")
    return redirect("accounts:login")
