"""Tiện ích tạo mã QR và gửi email xác nhận đơn đặt coche xe."""
import io
import logging

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from email.mime.image import MIMEImage
from email.utils import make_msgid

logger = logging.getLogger(__name__)


def build_qr_payload(order):
    """Nội dung được mã hoá trong mã QR thanh toán / nhận xe."""
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
    """Sinh ảnh QR cho đơn đặt cọc, lưu vào MEDIA_ROOT/qrcodes và gán vào order."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(build_qr_payload(order))
    qr.make(fit=True)

    image = qr.make_image(fill_color='#0F172A', back_color='#FFFFFF').convert('RGB')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')

    # FileField sẽ tự động thêm upload_to='qrcodes/' -> chỉ truyền tên file.
    filename = f'{order.order_code}.png'
    storage_path = f'qrcodes/{filename}'
    if default_storage.exists(storage_path):
        default_storage.delete(storage_path)

    order.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=False)
    order.save(update_fields=['qr_code_image'])
    return order.qr_code_image.url


def send_order_confirmation_email(order, user):
    """Gửi HTML email kèm mã QR về cho khách hàng. Trả về True/False."""
    subject = f'[{order.order_code}] Xác nhận đặt cọc xe tại BookXe'
    context = {
        'order': order,
        'user': user,
        'bank_name': settings.BOOKXE_BANK_NAME,
        'bank_account': settings.BOOKXE_BANK_ACCOUNT,
        'bank_holder': settings.BOOKXE_BANK_HOLDER,
    }

    text_body = (
        f'Xin chào {user.get_full_name() or user.username},\n\n'
        f'BookXe đã nhận yêu cầu đặt cọc xe của bạn. Mã đơn: {order.order_code}.\n'
        f'Tổng tiền thuê: {int(order.total_rental_amount):,} VND. '
        f'Tiền đặt cọc: {int(order.deposit_paid_amount):,} VND.\n'
        f'Cửa hàng: {order.shop.shop_name}.\n'
        f'Địa chỉ nhận xe: {order.pickup_address}.\n'
        f'SĐT liên hệ: {order.receiver_phone}.\n\n'
        f'Vui lòng xuất trình mã QR đính kèm khi nhận xe. Cảm ơn bạn đã dùng BookXe!'
    )
    html_body = render_to_string('emails/order_confirmation.html', context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach_alternative(html_body, 'text/html')

    if order.qr_code_image and default_storage.exists(order.qr_code_image.name):
        try:
            with default_storage.open(order.qr_code_image.name, 'rb') as fh:
                qr_bytes = fh.read()

            qr_inline = MIMEImage(qr_bytes, _subtype='png')
            cid = make_msgid('bookingqr')[1:-1]
            qr_inline.add_header('Content-ID', f'<{cid}>')
            qr_inline.add_header('Content-Disposition', 'inline', filename='QR_Nhan_Xe.png')
            email.attach(qr_inline)

            # Đính kèm thêm để khách có thể lưu lại / in ra.
            email.attach('QR_Nhan_Xe.png', qr_bytes, 'image/png')

            # Chèn cid thực tế vào HTML (template dùng placeholder {{ qr_cid }}).
            html_body = html_body.replace('cid:booking_qr', f'cid:{cid}')
            email.alternatives = [(html_body, 'text/html')]
        except Exception:
            logger.exception('Không thể đính kèm mã QR vào email đơn %s', order.order_code)

    try:
        email.send(fail_silently=False)
        return True
    except Exception:
        logger.exception('Gửi email xác nhận đơn %s thất bại', order.order_code)
        return False
