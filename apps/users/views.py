from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from common.http import _get_client_ip
from integrations.turnstile import verify_turnstile


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