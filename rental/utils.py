"""Tiện ích liên kết VietQR và gửi email xác nhận đơn đặt xe."""
import logging
from urllib.parse import quote_plus

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from email.utils import make_msgid

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# URLs VietQR TPBank (Ngân hàng: TPBank - STK: 00003771572 - Chủ TK: NGO DINH BAO KHANH)
# ---------------------------------------------------------------------------

VETQR_BASE = 'https://img.vietqr.io/image/TPB-00003771572-compact2.png'
VETQR_ACCOUNT_NAME = 'NGO%20DINH%20BAO%20KHANH'

# Mã thành đại điểm mặc định khi gửi email
def build_vietqr_url(amount=None, note=None):
    """
    Sinh đường link ảnh VietQR TPBank.
    
    Args:
        amount: Số tiền (số nguyên, VD: 60000) hoặc None nếu chỉ hiển thị thông tin
        note: Nội dung chuyển khoản (mã đơn)
    Returns:
        str: URL ảnh VietQR có thể dùng trực tiếp trong <img src="...">
    """
    params = []
    if amount:
        params.append(f'amount={int(amount)}')
    if note:
        params.append(f'addInfo={quote_plus(note)}')
    params.append(f'accountName={VETQR_ACCOUNT_NAME}')
    
    if params:
        return f'{VETQR_BASE}?{"&".join(params)}'
    return f'{VETQR_BASE}?accountName={VETQR_ACCOUNT_NAME}'


def get_bank_info_display():
    """Chuỗi thông tin ngân hàng hiển thị rõ ràng."""
    return f"Ngân hàng: {settings.BOOKXE_BANK_NAME} - STK: {settings.BOOKXE_BANK_ACCOUNT} - Chủ TK: {settings.BOOKXE_BANK_HOLDER}"


def build_qr_payload(order):
    """
    Nội dung được mã hoá trong mã QR thanh toán / nhận xe.
    Dùng cho QR trên web/App nếu cần (VN-QR format).
    """
    return (
        f'BOOKXE|ORDER:{order.order_code}'
        f'|SHOP:{order.shop.shop_name}'
        f'|AMOUNT:{int(order.deposit_paid_amount)} VND'
        f'|BANK:{settings.BOOKXE_BANK_NAME}'
        f'|ACC:{settings.BOOKXE_BANK_ACCOUNT}'
        f'|HOLDER:{settings.BOOKXE_BANK_HOLDER}'
        f'|NOTE:Don thue xe - {order.order_code}'
    )


def generate_booking_qr(order):
    """
    Trả về đường link ảnh VietQR TPBank cho đơn đặt cọc.
    
    - Ảnh được tải từ VietQR khi trình duyệt hiển thị (không cần lưu vào MEDIA_ROOT)
    - VN-QR format nếu cần quét QR theo chuẩn VN
    
    Returns:
        str: URL ảnh VietQR (luôn hợp lệ, trả về URL rỗng nếu không có)
    """
    return build_vietqr_url(
        amount=int(order.deposit_paid_amount),
        note=order.order_code,
    )


def send_order_confirmation_email(order, user):
    """
    Gửi HTML email kèm mã QR về cho khách hàng.
    Trả về True/False.
    
    Dùng VietQR URL trực tiếp trong email (nhúng ảnh từ img.vietqr.io).
    """
    subject = f'[{order.order_code}] Xác nhận đặt cọc xe tại BookXe'
    vietqr_url = build_vietqr_url(
        amount=int(order.deposit_paid_amount),
        note=order.order_code,
    )
    context = {
        'order': order,
        'user': user,
        'vietqr_url': vietqr_url,
        'bank_name': settings.BOOKXE_BANK_NAME,
        'bank_account': settings.BOOKXE_BANK_ACCOUNT,
        'bank_holder': settings.BOOKXE_BANK_HOLDER,
        'bank_info_display': get_bank_info_display(),
    }

    text_body = (
        f'Xin chào {user.get_full_name() or user.username},\n\n'
        f'BookXe đã nhận yêu cầu đặt cọc xe của bạn. Mã đơn: {order.order_code}.\n'
        f'Tổng tiền thuê: {int(order.total_rental_amount):,} VND. '
        f'Tiền đặt cọc: {int(order.deposit_paid_amount):,} VND.\n'
        f'Cửa hàng: {order.shop.shop_name}.\n'
        f'Địa chỉ nhận xe: {order.pickup_address}.\n'
        f'SĐT liên hệ: {order.receiver_phone}.\n\n'
        f'Vui lòng xuất trình mã QR đính kèm khi nhận xe.\n\n'
        f'Thông tin chuyển khoản: {get_bank_info_display()}\n\n'
        f'Cảm ơn bạn đã dùng BookXe!'
    )
    html_body = render_to_string('emails/order_confirmation.html', context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach_alternative(html_body, 'text/html')

    try:
        email.send(fail_silently=False)
        return True
    except Exception:
        logger.exception('Gửi email xác nhận đơn %s thất bại', order.order_code)
        return False
