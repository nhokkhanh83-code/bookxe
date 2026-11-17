"""DRF Serializers for the BookXe API."""
from django.conf import settings
from rest_framework import serializers

from .models import (
    BookingOrder, BookingOrderItem, DepositCart, DepositCartItem,
    PriceBargain, RentalShop, ReviewComment, ShopBlog, User, Vehicle, VehicleImage,
)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class UserBriefSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role', 'is_student', 'avatar_url']

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------
class RentalShopSerializer(serializers.ModelSerializer):
    banner_url = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    vehicle_count = serializers.SerializerMethodField()

    class Meta:
        model = RentalShop
        fields = [
            'id', 'owner', 'owner_name', 'shop_name', 'slug', 'city_district',
            'exact_address', 'latitude', 'longitude', 'hotline', 'description',
            'banner_url', 'vehicle_count', 'created_at',
        ]

    def get_banner_url(self, obj):
        return obj.banner_image.url if obj.banner_image else None

    def get_vehicle_count(self, obj):
        return obj.vehicles.count()


# ---------------------------------------------------------------------------
# Vehicle images / list / detail
# ---------------------------------------------------------------------------
class VehicleImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = VehicleImage
        fields = ['id', 'image_url', 'is_primary']

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None


class VehicleListSerializer(serializers.ModelSerializer):
    primary_image_url = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    shop_name = serializers.CharField(source='shop.shop_name', read_only=True)
    shop_slug = serializers.CharField(source='shop.slug', read_only=True)
    city_district = serializers.CharField(source='shop.city_district', read_only=True)
    vehicle_type_display = serializers.CharField(source='get_vehicle_type_display', read_only=True)
    availability_display = serializers.CharField(source='get_availability_status_display', read_only=True)
    specs_summary = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            'id', 'shop', 'shop_name', 'shop_slug', 'city_district', 'name', 'brand', 'license_plate',
            'model_year', 'vehicle_type', 'vehicle_type_display', 'base_price_per_day',
            'allow_bargain', 'condition_status', 'availability_status', 'availability_display',
            'specifications', 'specs_summary', 'primary_image_url',
            'average_rating', 'review_count',
        ]

    def get_primary_image_url(self, obj):
        img = obj.primary_image
        return img.url if img else None

    def get_specs_summary(self, obj):
        specs = obj.specifications or {}
        parts = []
        for key in ('Hộp số', 'Dung tích / Số chỗ', 'Tiêu hao nhiên liệu'):
            if specs.get(key):
                parts.append(f'{key}: {specs[key]}')
        return ' • '.join(parts) if parts else 'Đang cập nhật thông số'


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()

    class Meta:
        model = ReviewComment
        fields = ['id', 'user', 'user_name', 'user_avatar', 'vehicle', 'blog', 'target',
                  'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'user', 'created_at', 'target']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_user_avatar(self, obj):
        return obj.user.avatar.url if obj.user.avatar else None

    def get_target(self, obj):
        return 'vehicle' if obj.vehicle_id else 'blog'


class VehicleDetailSerializer(VehicleListSerializer):
    images = VehicleImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    shop = RentalShopSerializer(read_only=True)
    my_bargains = serializers.SerializerMethodField()
    min_bargain_price = serializers.SerializerMethodField()

    class Meta(VehicleListSerializer.Meta):
        fields = VehicleListSerializer.Meta.fields + [
            'images', 'reviews', 'shop', 'my_bargains', 'min_bargain_price',
        ]

    def get_min_bargain_price(self, obj):
        # Giá sàn là thông tin nội bộ - KHÔNG trả về cho khách thuê.
        return None

    def get_my_bargains(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        qs = obj.bargains.filter(user=request.user).select_related('vehicle')
        return PriceBargainSerializer(qs, many=True, context=self.context).data


# ---------------------------------------------------------------------------
# Bargain
# ---------------------------------------------------------------------------
class PriceBargainSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    customer_type_display = serializers.CharField(source='get_customer_type_display', read_only=True)
    final_price = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    vehicle_name = serializers.CharField(source='vehicle.name', read_only=True)
    vehicle_plate = serializers.CharField(source='vehicle.license_plate', read_only=True)

    class Meta:
        model = PriceBargain
        fields = [
            'id', 'vehicle', 'vehicle_name', 'vehicle_plate', 'user', 'user_name', 'shop',
            'offered_price_per_day', 'rental_days', 'customer_type', 'customer_type_display',
            'note', 'status', 'status_display', 'counter_price', 'final_price',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'user_name', 'shop', 'status', 'counter_price',
            'created_at', 'updated_at', 'vehicle_name', 'vehicle_plate',
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def validate(self, attrs):
        vehicle = attrs.get('vehicle')
        request = self.context.get('request')
        if vehicle and not vehicle.allow_bargain:
            raise serializers.ValidationError({'vehicle': 'Chiếc xe này không cho phép thương lượng giá.'})
        if vehicle and vehicle.availability_status != Vehicle.Availability.AVAILABLE:
            raise serializers.ValidationError({'vehicle': 'Xe hiện không sẵn sàng để thương lượng.'})
        offered = attrs.get('offered_price_per_day')
        if offered is not None and vehicle and offered >= vehicle.base_price_per_day:
            raise serializers.ValidationError(
                {'offered_price_per_day': 'Mức giá đề xuất phải thấp hơn giá niêm yết để được coi là thương lượng.'}
            )
        customer_type = attrs.get('customer_type')
        if customer_type == PriceBargain.CustomerType.STUDENT:
            if request and request.user.is_authenticated and not request.user.is_student:
                raise serializers.ValidationError(
                    {'customer_type': 'Tài khoản của bạn chưa được xác thực là sinh viên. Vui lòng chọn đối tượng khác.'}
                )
        return attrs


class BargainRespondSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[PriceBargain.Status.ACCEPTED,
                                              PriceBargain.Status.COUNTERED,
                                              PriceBargain.Status.REJECTED])
    counter_price = serializers.DecimalField(max_digits=12, decimal_places=0, required=False, allow_null=True)

    def validate(self, attrs):
        if attrs['status'] == PriceBargain.Status.COUNTERED and attrs.get('counter_price') in (None, ''):
            raise serializers.ValidationError({'counter_price': 'Vui lòng nhập giá báo lại khi chọn Counter Offer.'})
        return attrs


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
class CartItemSerializer(serializers.ModelSerializer):
    vehicle = VehicleListSerializer(read_only=True)
    vehicle_id = serializers.IntegerField(write_only=True)
    line_total = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    original_price_per_day = serializers.DecimalField(
        source='vehicle.base_price_per_day', max_digits=12, decimal_places=0, read_only=True,
    )

    class Meta:
        model = DepositCartItem
        fields = [
            'id', 'vehicle', 'vehicle_id', 'start_date', 'end_date', 'total_days',
            'applied_price_per_day', 'original_price_per_day', 'is_bargain_price',
            'deposit_amount', 'line_total',
        ]
        read_only_fields = ['id', 'vehicle', 'applied_price_per_day', 'is_bargain_price', 'deposit_amount']


class CartAddSerializer(serializers.Serializer):
    vehicle_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs['end_date'] <= attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'Ngày trả phải sau ngày nhận xe.'})
        try:
            vehicle = Vehicle.objects.get(pk=attrs['vehicle_id'])
        except Vehicle.DoesNotExist:
            raise serializers.ValidationError({'vehicle_id': 'Không tìm thấy chiếc xe này.'})
        if vehicle.availability_status != Vehicle.Availability.AVAILABLE:
            raise serializers.ValidationError({'vehicle_id': 'Chiếc xe hiện không sẵn sàng để đặt cọc.'})
        attrs['vehicle'] = vehicle
        return attrs


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_rental_amount = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    total_deposit = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    total_days = serializers.IntegerField(read_only=True)
    count = serializers.IntegerField(read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = DepositCart
        fields = [
            'id', 'items', 'total_rental_amount', 'total_deposit', 'total_amount',
            'total_days', 'count', 'updated_at',
        ]

    def get_total_amount(self, obj):
        return (obj.total_rental_amount or 0) + (obj.total_deposit or 0)


class CartUpdateSerializer(serializers.Serializer):
    """Cập nhật số ngày thuê từ bộ nút [-] [số ngày] [+] trên trang giỏ hàng."""

    total_days = serializers.IntegerField(min_value=1, max_value=60)


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------
class CheckoutSerializer(serializers.Serializer):
    pickup_address = serializers.CharField()
    receiver_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    receiver_phone = serializers.CharField(max_length=20)
    customer_note = serializers.CharField(required=False, allow_blank=True, default='')
    payment_method = serializers.ChoiceField(
        choices=BookingOrder.PaymentMethod.choices, default=BookingOrder.PaymentMethod.QR_TRANSFER,
    )

    def validate_receiver_phone(self, value):
        cleaned = ''.join(ch for ch in value if ch.isdigit() or ch == '+')
        if len(cleaned) < 9:
            raise serializers.ValidationError('Số điện thoại liên hệ không hợp lệ.')
        return value


class BookingOrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)

    class Meta:
        model = BookingOrderItem
        fields = ['id', 'vehicle', 'vehicle_name', 'license_plate', 'start_date', 'end_date',
                  'total_days', 'price_per_day', 'was_bargain_price', 'line_total']


class BookingOrderSerializer(serializers.ModelSerializer):
    items = BookingOrderItemSerializer(many=True, read_only=True)
    qr_code_url = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    shop_name = serializers.CharField(source='shop.shop_name', read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = BookingOrder
        fields = [
            'id', 'order_code', 'shop', 'shop_name', 'user_name', 'pickup_address', 'receiver_name',
            'receiver_phone', 'delivery_time_note', 'customer_note',
            'total_rental_amount', 'deposit_paid_amount', 'payment_method',
            'payment_method_display', 'qr_code_url', 'status', 'status_display',
            'created_at', 'items',
        ]

    def get_qr_code_url(self, obj):
        return obj.qr_code_image.url if obj.qr_code_image else None

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


# ---------------------------------------------------------------------------
# Blog
# ---------------------------------------------------------------------------
class BlogListSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    shop_name = serializers.CharField(source='shop.shop_name', read_only=True)
    shop_slug = serializers.CharField(source='shop.slug', read_only=True)
    featured_vehicle_name = serializers.CharField(source='featured_vehicle.name', read_only=True, allow_null=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = ShopBlog
        fields = [
            'id', 'title', 'slug', 'thumbnail_url', 'promo_badge', 'shop', 'shop_name',
            'shop_slug', 'featured_vehicle', 'featured_vehicle_name', 'comment_count', 'created_at',
        ]

    def get_thumbnail_url(self, obj):
        return obj.thumbnail.url if obj.thumbnail else None

    def get_comment_count(self, obj):
        return obj.reviews.count()


class BlogDetailSerializer(BlogListSerializer):
    content = serializers.CharField(read_only=True)
    author = UserBriefSerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    featured_vehicle_detail = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)

    class Meta(BlogListSerializer.Meta):
        fields = BlogListSerializer.Meta.fields + [
            'content', 'author', 'reviews', 'featured_vehicle_detail', 'average_rating',
        ]

    def get_featured_vehicle_detail(self, obj):
        if not obj.featured_vehicle_id:
            return None
        return {
            'id': obj.featured_vehicle.id,
            'name': obj.featured_vehicle.name,
            'price': obj.featured_vehicle.base_price_per_day,
            'plate': obj.featured_vehicle.license_plate,
            'primary_image': obj.featured_vehicle.primary_image.url if obj.featured_vehicle.primary_image else None,
        }


# ---------------------------------------------------------------------------
# Đăng Blog mới (Admin & Staff)
# ---------------------------------------------------------------------------
class BlogCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=250)
    content = serializers.CharField()
    promo_badge = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    featured_vehicle = serializers.IntegerField(required=False, allow_null=True)

    def validate_featured_vehicle(self, value):
        if value is None:
            return None
        from .models import Vehicle
        if not Vehicle.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Không tìm thấy chiếc xe được giới thiệu.')
        return value


# ---------------------------------------------------------------------------
# Admin: liệt kê user & đổi role nhanh
# ---------------------------------------------------------------------------
class AdminUserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'role', 'role_display',
                  'is_active', 'is_staff', 'is_superuser', 'date_joined']


class UserRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[('user', 'user'), ('staff', 'staff'), ('admin', 'admin')])
