"""Template (HTML) views for the BookXe storefront & dashboards."""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    BookingOrder, ContactSupport, Country, RentalShop, ReviewComment,
    ShopBlog, User, Vehicle,
)


def get_city_choices():
    """Danh sách thành phố duy nhất, ưu tiên bảng Country do Admin xếp thứ tự."""
    cities = list(
        Country.objects.filter(is_active=True)
        .order_by('display_order', 'name')
        .values_list('name', flat=True)
    )
    if not cities:
        cities = list(
            RentalShop.objects.order_by()
            .exclude(city_district='')
            .values_list('city_district', flat=True)
            .distinct()
        )
    # Khử trùng lặp nhưng vẫn giữ nguyên thứ tự.
    seen = set()
    result = []
    for city in cities:
        if city and city not in seen:
            seen.add(city)
            result.append(city)
    return result


def home_view(request):
    shops = RentalShop.objects.select_related('owner').all()[:12]
    featured_vehicles = Vehicle.objects.filter(
        availability_status=Vehicle.Availability.AVAILABLE
    ).select_related('shop').prefetch_related('images')[:8]
    latest_blogs = ShopBlog.objects.select_related('shop').all()[:3]
    cities = get_city_choices()
    return render(request, 'rental/home.html', {
        'shops': shops,
        'featured_vehicles': featured_vehicles,
        'latest_blogs': latest_blogs,
        'cities': cities,
    })


def product_list_view(request):
    """Trang PRODUCT: toàn bộ xe cho thuê kèm bộ lọc (lọc qua /api/products/)."""
    cities = get_city_choices()
    return render(request, 'rental/products.html', {'cities': cities})


def shop_detail_view(request, slug):
    shop = get_object_or_404(
        RentalShop.objects.select_related('owner'), slug=slug,
    )
    blogs = shop.blogs.select_related('featured_vehicle').all()[:6]
    return render(request, 'rental/shop_detail.html', {
        'shop': shop,
        'blogs': blogs,
    })


def vehicle_detail_view(request, pk):
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('shop', 'shop__owner').prefetch_related('images'),
        pk=pk,
    )
    user_has_rated = False
    if request.user.is_authenticated:
        user_has_rated = ReviewComment.objects.filter(
            user=request.user, vehicle=vehicle, rating__isnull=False,
        ).exists()
    return render(request, 'rental/vehicle_detail.html', {
        'vehicle': vehicle,
        'shop': vehicle.shop,
        'user_has_rated': user_has_rated,
    })


def blog_list_view(request):
    return render(request, 'rental/blog_list.html', {})


def blog_detail_view(request, slug):
    blog = get_object_or_404(
        ShopBlog.objects.select_related('shop', 'author', 'featured_vehicle'), slug=slug,
    )
    user_has_rated = False
    if request.user.is_authenticated:
        user_has_rated = ReviewComment.objects.filter(
            user=request.user, blog=blog, rating__isnull=False,
        ).exists()
    return render(request, 'rental/blog_detail.html', {
        'blog': blog,
        'shop': blog.shop,
        'user_has_rated': user_has_rated,
    })


@login_required
def cart_view(request):
    return render(request, 'rental/cart.html', {})


@login_required
def checkout_view(request):
    cart = getattr(request.user, 'cart', None)
    if not cart or not cart.cart_items.exists():
        messages.warning(request, 'Giỏ đặt cọc của bạn đang trống. Hãy thêm xe trước khi thanh toán.')
        return redirect('cart')
    # Đơn được tạo tại CheckoutAPIView: QR/email được bọc try...except riêng,
    # nên lỗi SMTP hay QR chậm vẫn trả về order_code để sang trang xác nhận.
    # receiver_name do khách tự nhập trên form checkout.
    receiver_name = (
        request.POST.get('receiver_name', '').strip()
        or request.GET.get('receiver_name', '').strip()
        or request.user.get_full_name()
    )
    return render(request, 'rental/checkout.html', {
        'cart': cart,
        'receiver_name': receiver_name,
    })


@login_required
def order_confirmation_view(request, order_code):
    order = get_object_or_404(
        BookingOrder.objects.select_related('shop').prefetch_related('items'),
        order_code=order_code,
    )
    if order.user_id != request.user.id and request.user.role != 'admin':
        messages.error(request, 'Bạn không có quyền xem đơn hàng này.')
        return redirect('home')
    return render(request, 'rental/order_confirmation.html', {'order': order})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Chào mừng trở lại, {user.get_full_name() or user.username}!')
            next_url = request.POST.get('next') or request.GET.get('next') or 'home'
            return redirect(next_url)
        messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng.')
    return render(request, 'rental/login.html', {'next': request.GET.get('next', '')})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        phone = request.POST.get('phone', '').strip()
        is_student = request.POST.get('is_student') == 'on'

        if password != confirm:
            messages.error(request, 'Mật khẩu xác nhận không khớp.')
        elif not username or not email or not password:
            messages.error(request, 'Vui lòng điền đầy đủ thông tin bắt buộc.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập đã tồn tại.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email đã được sử dụng.')
        else:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role=User.Role.USER,
                    phone=phone,
                    is_student=is_student,
                    first_name=request.POST.get('first_name', '').strip(),
                    last_name=request.POST.get('last_name', '').strip(),
                )
            login(request, user)
            messages.success(request, 'Đăng ký tài khoản thành công. Chúc bạn tìm được xe ưng ý!')
            return redirect('home')
    return render(request, 'rental/register.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Bạn đã đăng xuất.')
    return redirect('home')


@login_required
def dashboard_view(request):
    user = request.user
    if user.role == 'admin':
        return render(request, 'rental/dashboard_admin.html', {})
    if user.role == 'staff':
        return render(request, 'rental/dashboard_staff.html', {'shop': getattr(user, 'shop', None)})
    # Khách thuê xe -> trang đơn hàng của tôi
    orders = BookingOrder.objects.filter(user=user).select_related('shop').prefetch_related('items')[:20]
    return render(request, 'rental/dashboard_user.html', {'orders': orders})


def _can_write_blog(user):
    return (
        user.is_authenticated
        and (user.is_superuser or getattr(user, 'role', '') in ('admin', 'staff'))
    )


@login_required
def blog_create_view(request):
    """Đăng blog từ web: Admin hoặc Staff đều có quyền (fallback cho form POST)."""
    if not _can_write_blog(request.user):
        messages.error(request, 'Chỉ Admin hoặc Chủ cửa hàng được đăng bài viết.')
        return redirect('blog_list')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if not title or not content:
            messages.error(request, 'Vui lòng nhập tiêu đề và nội dung bài viết.')
            return redirect('blog_list')

        user = request.user
        if user.is_superuser or getattr(user, 'role', '') == 'admin':
            shop = getattr(user, 'shop', None)
            if shop is None:
                shop = RentalShop.objects.order_by('id').first()
            if shop is None:
                shop = RentalShop.objects.create(
                    owner=user,
                    shop_name=f'Cửa hàng của {user.username}',
                    city_district='Đà Nẵng',
                    exact_address='Chưa cập nhật địa chỉ cửa hàng',
                )
        else:
            shop = getattr(user, 'shop', None)
            if shop is None:
                messages.error(request, 'Tài khoản staff chưa có cửa hàng.')
                return redirect('blog_list')

        featured_vehicle_id = request.POST.get('featured_vehicle') or None
        blog = ShopBlog.objects.create(
            shop=shop,
            author=user,
            title=title,
            content=content,
            promo_badge=request.POST.get('promo_badge', '').strip(),
            featured_vehicle_id=featured_vehicle_id,
        )
        if request.FILES.get('thumbnail'):
            blog.thumbnail = request.FILES['thumbnail']
            blog.save(update_fields=['thumbnail'])
        messages.success(request, 'Đăng bài Blog thành công!')
        return redirect('blog_detail', slug=blog.slug)
    return redirect('blog_list')


@login_required
def set_user_role_view(request, pk):
    """Admin đổi role nhanh từ web (fallback cho dashboard_admin.html)."""
    user = request.user
    if not (user.is_superuser or getattr(user, 'role', '') == 'admin'):
        messages.error(request, 'Bạn không có quyền thay đổi phân quyền.')
        return redirect('home')
    if request.method == 'POST':
        target = get_object_or_404(User, pk=pk)
        role = request.POST.get('role', '')
        if role in User.Role.values:
            target.role = role
            target.save()  # User.save() tự đồng bộ is_staff/is_superuser.
            messages.success(request, f'Đã cập nhật quyền của {target.username}.')
        else:
            messages.error(request, 'Quyền không hợp lệ.')
    return redirect('dashboard')


@login_required
def contact_view(request):
    """Trang Liên hệ / Báo sự cố xe hư (có thể nhúng từ shop/đơn thuê)."""
    if request.method == 'POST':
        shop_id = request.POST.get('shop') or request.POST.get('shop_id')
        message = (request.POST.get('message') or '').strip()
        if not shop_id or not message:
            messages.error(request, 'Vui lòng chọn cửa hàng và nhập nội dung cần hỗ trợ.')
        else:
            ContactSupport.objects.create(
                user=request.user,
                shop_id=shop_id,
                vehicle_id=request.POST.get('vehicle') or None,
                order_id=request.POST.get('order') or None,
                issue_type=request.POST.get('issue_type') or ContactSupport.IssueType.OTHER,
                current_location=request.POST.get('current_location', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                message=message,
                image=request.FILES.get('image'),
            )
            messages.success(request, 'Đã gửi yêu cầu hỗ trợ. Cửa hàng sẽ phản hồi ngay!')
            return redirect('contact')
    return render(request, 'rental/contact.html', {
        'shops': RentalShop.objects.order_by('shop_name'),
        'vehicles': Vehicle.objects.select_related('shop'),
        'prefill_shop': request.GET.get('shop', ''),
        'prefill_vehicle': request.GET.get('vehicle', ''),
        'prefill_order': request.GET.get('order', ''),
        'issue_types': ContactSupport.IssueType.choices,
    })


@login_required
def profile_view(request):
    """Xem & sửa toàn bộ thông tin cá nhân + đổi mật khẩu."""
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.phone = request.POST.get('phone', '').strip()
        user.address = request.POST.get('address', '').strip()
        user.is_student = request.POST.get('is_student') == 'on'
        if request.FILES.get('avatar'):
            user.avatar = request.FILES['avatar']
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        if new_password and new_password != confirm_password:
            messages.error(request, 'Mật khẩu xác nhận không khớp.')
            return redirect('profile')
        if new_password:
            user.set_password(new_password)
            update_session_auth_hash(request, user)
        user.save()
        messages.success(request, 'Cập nhật thông tin cá nhân (Update Profile) thành công!')
        return redirect('profile')
    return render(request, 'rental/profile.html', {'profile_user': user})
