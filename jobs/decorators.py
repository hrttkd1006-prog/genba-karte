from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def hospital_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account_login')
        if not request.user.is_hospital_admin:
            messages.error(request, 'このページは病院・施設の管理者専用です。')
            return redirect('top')
        return view_func(request, *args, **kwargs)
    return wrapper
