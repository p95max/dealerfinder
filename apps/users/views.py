from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from utils.http import _get_client_ip
from integrations.turnstile import verify_turnstile
from apps.users.middleware import reset_quota_if_new_day

def login_gate_view(request):
    """Show login gate page and verify Turnstile before Google OAuth."""
    if request.user.is_authenticated:
        return redirect("dealers:home")

    if request.method == "POST":
        token = request.POST.get("cf-turnstile-response", "")
        ip = _get_client_ip(request)

        if not verify_turnstile(token, ip):
            messages.warning(request, "Please complete the security check.")
            return render(request, "account/login.html", status=400)

        request.session["turnstile_login_ok"] = True
        return redirect("google_login")

    return render(request, "account/login.html")

@login_required
def profile_view(request):
    return render(request, "users/profile.html")


@login_required
def accept_terms_view(request):
    if request.user.terms_accepted:
        return redirect("/")

    error = None
    if request.method == "POST":
        if request.POST.get("terms"):
            request.user.terms_accepted = True
            request.user.save(update_fields=["terms_accepted"])
            return redirect("/")
        else:
            error = "You must accept the terms to continue."

    return render(request, "users/accept_terms.html", {"error": error})

@require_POST
def anon_accept_terms_view(request):
    request.session["anon_terms"] = True
    return JsonResponse({"ok": True})


def pricing_view(request):
    return render(request, "users/pricing.html", {
        "anon_limit": settings.ANON_DAILY_LIMIT,
        "free_limit": settings.FREE_DAILY_LIMIT,
        "premium_limit": settings.PREMIUM_DAILY_LIMIT,
    })


@login_required
def delete_account_view(request):
    if request.method != "POST":
        return redirect("dealers:home")

    token = request.POST.get("cf-turnstile-response", "")
    ip = _get_client_ip(request)
    if not verify_turnstile(token, ip):
        messages.warning(request, "Please complete the security check.")
        return redirect("users:profile")

    user = request.user
    logout(request)
    user.delete()
    messages.success(request, "Your account has been deleted.")
    return redirect("dealers:home")


@login_required
def quota_status(request):
    user = request.user
    reset_quota_if_new_day(user)
    user.refresh_from_db(fields=["used_today", "daily_quota"])
    return JsonResponse({"used": user.used_today, "limit": user.daily_quota})