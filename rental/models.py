"""Database models for the BookXe rental marketplace."""
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator


# ---------------------------------------------------------------------------
# 3.1 Custom User
# ---------------------------------------------------------------------------
class User(AbstractUser):
    """Custom user model extending Django's AbstractUser with RBAC roles."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Quản trị viên'
        STAFF = 'staff', 'Chủ cửa hàng'
        USER = 'user', 'Khách thuê xe'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER, db_index=True)
    phone = models.CharField(max_length=20, blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_student = models.BooleanField(default=False, help_text='Xác thực để hưởng ưu đãi sinh viên')
    address = models.TextField(blank=True, default='')

    # Keep a reverse-friendly related_name while preserving AbstractUser behaviour.
    groups = models.ManyToManyField(
        'auth.Group', related_name='bookxe_user_set', blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission', related_name='bookxe_user_set', blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        verbose_name = 'Người dùng'
        verbose_name_plural = 'Người dùng'

    def save(self, *args, **kwargs):
        """Đồng bộ role <-> is_staff/is_superuser và tự tạo cửa hàng cho staff.

        - superuser hoặc role='admin'  -> role='admin', is_staff=True, is_superuser=True
        - role='staff'                 -> is_staff=True, is_superuser=False, tự tạo RentalShop
        - role='user'                  -> is_staff=False, is_superuser=False
        """
        from django.apps import apps as django_apps

        changed = set()
        if self.is_superuser or self.role == self.Role.ADMIN:
            self.role = self.Role.ADMIN
            self.is_staff = True
            self.is_superuser = True
            changed.update({'role', 'is_staff', 'is_superuser'})
        elif self.role == self.Role.STAFF:
            self.is_staff = True
            self.is_superuser = False
            changed.update({'role', 'is_staff', 'is_superuser'})
        elif self.role == self.Role.USER:
            self.is_staff = False
            self.is_superuser = False
            changed.update({'role', 'is_staff', 'is_superuser'})

        # Giữ update_fields (nếu có) đồng bộ với các field vừa bị ép đổi.
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            kwargs['update_fields'] = set(update_fields) | changed

        super().save(*args, **kwargs)

        # Tự động tạo cửa hàng mặc định cho staff nếu chưa có (chạy sau khi có pk).
        if self.role == self.Role.STAFF:
            try:
                has_shop = hasattr(self, 'shop') and self.shop is not None
            except Exception:
                has_shop = False
            if not has_shop:
                RentalShop = django_apps.get_model('rental', 'RentalShop')
                RentalShop.objects.get_or_create(
                    owner=self,
                    defaults={
                        'shop_name': f'Cửa hàng của {self.username}',
                        'city_district': 'Đà Nẵng',
                        'exact_address': 'Chưa cập nhật địa chỉ cửa hàng',
                        'description': 'Cửa hàng cho thuê xe BookXe - đang cập nhật thông tin.',
                    },
                )

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


# ---------------------------------------------------------------------------
# 3.2 RentalShop
# ---------------------------------------------------------------------------
class RentalShop(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shop')
    shop_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    city_district = models.CharField(max_length=150, help_text='Khu vực / Quận / Thành phố')
    exact_address = models.CharField(max_length=300)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    hotline = models.CharField(max_length=20, blank=True, default='')
    description = models.TextField(blank=True, default='')
    banner_image = models.ImageField(upload_to='shops/banners/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Cửa hàng cho thuê'
        verbose_name_plural = 'Cửa hàng'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.shop_name) or f'shop-{self.owner_id}'
            base = self.slug
            i = 1
            while RentalShop.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{base}-{i}'
                i += 1
        super().save(*args, **kwargs)

    def average_rating(self):
        vals = self.reviews.filter(vehicle__isnull=False, rating__isnull=False).aggregate(avg=models.Avg('rating'))['avg']
        return round(vals, 1) if vals else None

    def __str__(self):
        return self.shop_name


# ---------------------------------------------------------------------------
# 3.2b Danh mục dùng để hiển thị trên /admin/ (Blogs / Brands / Categorys / Countrys)
# ---------------------------------------------------------------------------
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Hãng xe'
        verbose_name_plural = 'Hãng xe'

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Danh mục'
        verbose_name_plural = 'Danh mục'

    def __str__(self):
        return self.name


class Country(models.Model):
    """Thành phố / Khu vực - chỉ Admin được thêm, sửa, sắp xếp."""
    name = models.CharField(max_length=100, unique=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Thành phố / Khu vực'
        verbose_name_plural = 'Countrys'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 3.3 Vehicle
# ---------------------------------------------------------------------------
class Vehicle(models.Model):
    class VehicleType(models.TextChoices):
        MOTORBIKE = 'motorbike', 'Xe máy'
        CAR = 'car', 'Ô tô'

    class Availability(models.TextChoices):
        AVAILABLE = 'available', 'Sẵn sàng cho thuê'
        RENTED = 'rented', 'Đang cho thuê'
        MAINTENANCE = 'maintenance', 'Đang bảo dưỡng'

    shop = models.ForeignKey(RentalShop, on_delete=models.CASCADE, related_name='vehicles')
    vehicle_type = models.CharField(max_length=10, choices=VehicleType.choices, default=VehicleType.MOTORBIKE, db_index=True)
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    license_plate = models.CharField(max_length=20)
    model_year = models.PositiveIntegerField()
    base_price_per_day = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(0)])
    allow_bargain = models.BooleanField(default=True)
    min_bargain_price = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        help_text='Giá sàn thấp nhất shop có thể chấp nhận - Ẩn với khách thuê.',
    )
    condition_status = models.TextField(blank=True, default='')
    availability_status = models.CharField(
        max_length=12, choices=Availability.choices, default=Availability.AVAILABLE, db_index=True,
    )
    specifications = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-id']
        verbose_name = 'Xe cho thuê'
        verbose_name_plural = 'Xe cho thuê'

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first() or self.images.first()
        return img.image if img else None

    def average_rating(self):
        """Chỉ tính trung bình trên các bản ghi CÓ đánh giá sao."""
        vals = self.reviews.filter(rating__isnull=False).aggregate(avg=models.Avg('rating'))['avg']
        return round(vals, 1) if vals else 0.0

    def review_count(self):
        """Số lượt đánh giá sao thực tế (không tính bình luận chữ)."""
        return self.reviews.filter(rating__isnull=False).count()

    def __str__(self):
        return f'{self.brand} {self.name} [{self.license_plate}]'


# ---------------------------------------------------------------------------
# 3.4 VehicleImage
# ---------------------------------------------------------------------------
class VehicleImage(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='vehicles/')
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary', 'id']

    def __str__(self):
        return f'Image for {self.vehicle.name}'


# ---------------------------------------------------------------------------
# 3.5 PriceBargain
# ---------------------------------------------------------------------------
class PriceBargain(models.Model):
    class CustomerType(models.TextChoices):
        STUDENT = 'student', 'Học sinh / Sinh viên'
        LOCAL_TOURIST = 'local_tourist', 'Khách du lịch'
        OFF_SEASON = 'off_season', 'Thuê mùa thấp điểm'
        LONG_TERM = 'long_term', 'Thuê dài ngày'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ duyệt'
        ACCEPTED = 'accepted', 'Shop đã đồng ý'
        COUNTERED = 'countered', 'Shop báo giá lại'
        REJECTED = 'rejected', 'Shop từ chối'

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='bargains')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bargains')
    shop = models.ForeignKey(RentalShop, on_delete=models.CASCADE, related_name='bargains')
    offered_price_per_day = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(0)])
    rental_days = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    customer_type = models.CharField(max_length=20, choices=CustomerType.choices, default=CustomerType.STUDENT)
    note = models.TextField(blank=True, default='')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    counter_price = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Yêu cầu thương lượng giá'
        verbose_name_plural = 'Thương lượng giá'

    @property
    def final_price(self):
        """Giá cuối cùng có hiệu lực nếu shop đồng ý / báo giá lại."""
        if self.status == self.Status.ACCEPTED:
            return self.offered_price_per_day
        if self.status == self.Status.COUNTERED and self.counter_price is not None:
            return self.counter_price
        return None

    def __str__(self):
        return f'{self.user.username} -> {self.vehicle.name}: {self.get_status_display()}'


# ---------------------------------------------------------------------------
# 3.6 DepositCart / DepositCartItem
# ---------------------------------------------------------------------------
class DepositCart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def items(self):
        return self.cart_items.all()

    @property
    def total_days(self):
        return sum(item.total_days for item in self.items.all())

    @property
    def total_rental_amount(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def total_deposit(self):
        return sum(item.deposit_amount for item in self.items.all())

    @property
    def count(self):
        return self.items.count()

    def __str__(self):
        return f'Cart of {self.user.username}'


class DepositCartItem(models.Model):
    cart = models.ForeignKey(DepositCart, on_delete=models.CASCADE, related_name='cart_items')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='cart_items')
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.PositiveIntegerField(default=1)
    applied_price_per_day = models.DecimalField(max_digits=12, decimal_places=0)
    is_bargain_price = models.BooleanField(default=False, help_text='True nếu dùng giá thương lượng đã duyệt')
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['cart', 'vehicle'], name='uniq_cart_vehicle'),
        ]

    @property
    def line_total(self):
        return self.applied_price_per_day * self.total_days

    def __str__(self):
        return f'{self.vehicle.name} x {self.total_days} ngày'


# ---------------------------------------------------------------------------
# 3.7 BookingOrder / BookingOrderItem
# ---------------------------------------------------------------------------
class BookingOrder(models.Model):
    class PaymentMethod(models.TextChoices):
        QR_TRANSFER = 'qr_transfer', 'Chuyển khoản QR'
        CASH_ON_PICKUP = 'cash_on_pickup', 'Thanh toán khi nhận xe'

    class Status(models.TextChoices):
        PENDING_DEPOSIT = 'pending_deposit', 'Chờ đặt cọc'
        CONFIRMED = 'confirmed', 'Đã xác nhận'
        PICKED_UP = 'picked_up', 'Đã nhận xe'
        COMPLETED = 'completed', 'Hoàn tất'
        CANCELLED = 'cancelled', 'Đã hủy'

    order_code = models.CharField(max_length=30, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    shop = models.ForeignKey(RentalShop, on_delete=models.CASCADE, related_name='orders')
    pickup_address = models.TextField()
    receiver_name = models.CharField(max_length=150, blank=True, default='')
    receiver_phone = models.CharField(max_length=20)
    delivery_time_note = models.CharField(
        max_length=255, blank=True, default='Giao xe trong 1 - 2 giờ tới',
    )
    customer_note = models.TextField(blank=True, default='')
    total_rental_amount = models.DecimalField(max_digits=14, decimal_places=0)
    deposit_paid_amount = models.DecimalField(max_digits=14, decimal_places=0)
    payment_method = models.CharField(max_length=16, choices=PaymentMethod.choices, default=PaymentMethod.QR_TRANSFER)
    qr_code_image = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING_DEPOSIT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Đơn đặt xe'
        verbose_name_plural = 'Đơn đặt xe'

    def __str__(self):
        return self.order_code


class BookingOrderItem(models.Model):
    order = models.ForeignKey(BookingOrder, on_delete=models.CASCADE, related_name='items')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, related_name='order_items')
    vehicle_name = models.CharField(max_length=200)
    license_plate = models.CharField(max_length=20, blank=True, default='')
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.PositiveIntegerField(default=1)
    price_per_day = models.DecimalField(max_digits=12, decimal_places=0)
    was_bargain_price = models.BooleanField(default=False)

    @property
    def line_total(self):
        return self.price_per_day * self.total_days

    def __str__(self):
        return f'{self.vehicle_name} in {self.order.order_code}'


# ---------------------------------------------------------------------------
# 3.8 ShopBlog
# ---------------------------------------------------------------------------
class ShopBlog(models.Model):
    shop = models.ForeignKey(RentalShop, on_delete=models.CASCADE, related_name='blogs')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blogs')
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    thumbnail = models.ImageField(upload_to='blogs/', blank=True, null=True)
    content = models.TextField()
    featured_vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='featured_in_blogs')
    promo_badge = models.CharField(max_length=120, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bài viết blog'
        verbose_name_plural = 'Bài viết blog'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title) or f'blog-{self.shop_id}-{self.pk or ""}'
            base = self.slug
            i = 1
            while ShopBlog.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{base}-{i}'
                i += 1
        super().save(*args, **kwargs)

    def average_rating(self):
        vals = self.reviews.filter(rating__isnull=False).aggregate(avg=models.Avg('rating'))['avg']
        return round(vals, 1) if vals else 0.0

    def review_count(self):
        return self.reviews.filter(rating__isnull=False).count()

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# 3.9 ReviewComment (dùng chung cho Xe và Blog)
# ---------------------------------------------------------------------------
class ReviewComment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True, related_name='reviews')
    blog = models.ForeignKey(ShopBlog, on_delete=models.CASCADE, null=True, blank=True, related_name='reviews')
    # null/blank cho phép bình luận thêm nhiều lần sau khi đã đánh giá sao 1 lần.
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bình luận / đánh giá'
        verbose_name_plural = 'Bình luận & đánh giá'

    def __str__(self):
        return f'{self.user.username} - {self.rating}★'


# ---------------------------------------------------------------------------
# 3.10 ContactSupport - Liên hệ / Báo sự cố xe hư
# ---------------------------------------------------------------------------
class ContactSupport(models.Model):
    class IssueType(models.TextChoices):
        EMERGENCY = 'emergency_breakdown', 'Báo sự cố khẩn cấp: Xe hư dọc đường / Cần Staff hỗ trợ ngay'
        INQUIRY = 'rental_inquiry', 'Tư vấn thuê xe / Thương lượng'
        OTHER = 'other', 'Yêu cầu khác'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ hỗ trợ'
        PROCESSING = 'processing', 'Staff đang đến hỗ trợ'
        RESOLVED = 'resolved', 'Đã xử lý xong'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_requests')
    shop = models.ForeignKey(RentalShop, on_delete=models.CASCADE, related_name='support_requests')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_requests')
    order = models.ForeignKey(BookingOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_requests')
    issue_type = models.CharField(max_length=24, choices=IssueType.choices, default=IssueType.OTHER)
    current_location = models.CharField(max_length=300, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    message = models.TextField()
    image = models.ImageField(upload_to='support/', blank=True, null=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    staff_reply = models.TextField(blank=True, default='')
    is_read_by_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Yêu cầu hỗ trợ'
        verbose_name_plural = 'Yêu cầu hỗ trợ'

    def __str__(self):
        return f'{self.user.username} - {self.get_issue_type_display()}'
