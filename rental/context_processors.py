"""Context processors dùng chung cho toàn bộ template."""
from django.conf import settings

from .models import ContactSupport


def site_settings(request):
    """Cấu hình thanh toán + số yêu cầu hỗ trợ chưa đọc trên Navbar."""
    unread = 0
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        is_admin = user.is_superuser or getattr(user, 'role', '') == 'admin'
        is_staff = getattr(user, 'role', '') == 'staff' and not user.is_superuser
        if is_admin or is_staff:
            qs = ContactSupport.objects.filter(is_read_by_staff=False)
            if is_staff:
                qs = qs.filter(shop__owner=user)
            unread = qs.count()

    return {
        'bank_name': settings.BOOKXE_BANK_NAME,
        'bank_account': settings.BOOKXE_BANK_ACCOUNT,
        'bank_holder': settings.BOOKXE_BANK_HOLDER,
        'deposit_rate': settings.BOOKXE_DEPOSIT_RATE,
        'support_unread_count': unread,
    }
