from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import JsonResponse

from common.http import _get_client_ip
from integrations.turnstile import verify_turnstile

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
    return JsonResponse({
        "used": user.used_today,
        "limit": user.daily_quota,
    })