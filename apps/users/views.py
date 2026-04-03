from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from utils.http import _get_client_ip
from integrations.turnstile import verify_turnstile
from apps.users.services.quota_service import reset_quota_if_new_day
from .models import Favorite
from django.urls import reverse

def login_gate_view(request):
    """Render custom login page."""
    if request.user.is_authenticated:
        return redirect("home")

    return render(request, "account/login.html")



@require_POST
def google_oauth_start_view(request):
    token = request.POST.get("cf-turnstile-response", "")
    ip = _get_client_ip(request)

    if not verify_turnstile(token, ip):
        messages.warning(request, "Please complete the security check.")
        return redirect("account_login")

    request.session["google_oauth_verified"] = True
    return redirect(reverse("google_login"))


@login_required
def profile_view(request):
    return render(request, "users/profile.html")


@login_required
def delete_account_view(request):
    if request.method != "POST":
        return redirect("home")

    token = request.POST.get("cf-turnstile-response", "")
    ip = _get_client_ip(request)
    if not verify_turnstile(token, ip):
        messages.warning(request, "Please complete the security check.")
        return redirect("users:profile")

    user = request.user
    logout(request)
    user.delete()
    messages.success(request, "Your account has been deleted.")
    return redirect("home")


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


@require_POST
def cookie_consent_view(request):
    choice = request.POST.get("choice")

    if choice not in {"accepted", "rejected"}:
        return JsonResponse({"ok": False, "error": "Invalid choice"}, status=400)

    request.session["cookie_consent"] = choice
    return JsonResponse({"ok": True, "choice": choice})


def pricing_view(request):
    return render(request, "users/pricing.html", {
        "anon_limit": settings.ANON_DAILY_LIMIT,
        "free_limit": settings.FREE_DAILY_LIMIT,
        "premium_limit": settings.PREMIUM_DAILY_LIMIT,
    })


@login_required
def quota_status(request):
    user = request.user
    reset_quota_if_new_day(user)
    user.refresh_from_db(fields=["used_today", "daily_quota"])
    return JsonResponse({"used": user.used_today, "limit": user.daily_quota})


@login_required
def favorites_view(request):
    favorites = request.user.favorites.all()
    return render(request, "users/favorites.html", {"favorites": favorites})


@login_required
@require_POST
def favorite_add_view(request):
    data = {
        "place_id": request.POST.get("place_id", ""),
        "name": request.POST.get("name", ""),
        "address": request.POST.get("address", ""),
        "city": request.POST.get("city", ""),
        "rating": request.POST.get("rating") or None,
        "phone": request.POST.get("phone", ""),
        "website": request.POST.get("website", ""),
        "lat": request.POST.get("lat") or None,
        "lng": request.POST.get("lng") or None,
    }
    if not data["place_id"]:
        return JsonResponse({"ok": False}, status=400)

    Favorite.objects.get_or_create(user=request.user, place_id=data["place_id"], defaults=data)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def favorite_remove_view(request, place_id):
    Favorite.objects.filter(user=request.user, place_id=place_id).delete()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def favorites_clear_view(request):
    request.user.favorites.all().delete()
    return JsonResponse({"ok": True})