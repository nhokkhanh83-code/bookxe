"""DRF API views for the BookXe marketplace (AJAX / Fetch API backend)."""
import json
import logging
import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    BookingOrder, BookingOrderItem, ContactSupport, DepositCart, DepositCartItem,
    Brand, Category, Country, PriceBargain, RentalShop, ReviewComment, ShopBlog,
    User, Vehicle, VehicleImage,
)
from .permissions import IsAdmin, IsShopOwnerOrAdmin, IsStaff
from .serializers import (
    AdminUserSerializer, BargainRespondSerializer, BlogCreateSerializer,
    BlogDetailSerializer, BlogListSerializer, BookingOrderSerializer,
    CartAddSerializer, CartSerializer, CartUpdateSerializer, CheckoutSerializer,
    PriceBargainSerializer, RentalShopSerializer, ReviewSerializer,
    UserRoleUpdateSerializer, VehicleDetailSerializer, VehicleListSerializer,
)
from .utils import send_order_confirmation_email


def _money(value):
    """Làm tròn số tiền VND về số nguyên."""
    return Decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def make_order_code():
    return f'BKX{timezone.now().strftime("%Y%m%d%H%M%S")}{uuid.uuid4().hex[:4].upper()}'


def is_admin_user(user):
    return bool(
        user.is_authenticated
        and (user.is_superuser or getattr(user, 'role', '') == 'admin')
    )


def can_manage_order(user, order):
    """Khách chủ đơn, admin, hoặc staff chủ cửa hàng được thao tác đơn."""
    if not user.is_authenticated:
        return False
    if is_admin_user(user):
        return True
    if order.user_id == user.id:
        return True
    return (
        getattr(user, 'role', '') == 'staff'
        and getattr(order.shop, 'owner_id', None) == user.id
    )


def get_applicable_price(user, vehicle):
    """Trả về (giá áp dụng, có phải giá thương lượng không)."""
    bargain = (
        PriceBargain.objects
        .filter(
            user=user,
            vehicle=vehicle,
            status__in=[PriceBargain.Status.ACCEPTED, PriceBargain.Status.COUNTERED],
        )
        .order_by('-updated_at')
        .first()
    )
    if bargain and bargain.final_price is not None:
        return _money(bargain.final_price), True
    return _money(vehicle.base_price_per_day), False


# ---------------------------------------------------------------------------
# 1. Shops
# ---------------------------------------------------------------------------
class ShopListAPIView(generics.ListAPIView):
    serializer_class = RentalShopSerializer

    def get_queryset(self):
        qs = RentalShop.objects.select_related('owner').all()
        params = self.request.query_params
        search = params.get('search', '').strip()
        city = params.get('city', '').strip()

        if city:
            qs = qs.filter(city_district__icontains=city)
        if search:
            qs = qs.filter(
                Q(shop_name__icontains=search)
                | Q(city_district__icontains=search)
                | Q(exact_address__icontains=search)
                | Q(description__icontains=search)
            )
        return qs


# ---------------------------------------------------------------------------
# 2. Vehicles of a shop
# ---------------------------------------------------------------------------
class ShopVehiclesAPIView(generics.ListAPIView):
    serializer_class = VehicleListSerializer

    def get_queryset(self):
        shop_pk = self.kwargs.get('pk')
        qs = Vehicle.objects.filter(shop_id=shop_pk).select_related('shop').prefetch_related('images', 'reviews')

        params = self.request.query_params
        search = params.get('search', '').strip()
        vehicle_type = params.get('vehicle_type', '').strip()
        min_price = params.get('min_price', '').strip()
        max_price = params.get('max_price', '').strip()
        sort = params.get('sort', '').strip()

        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(brand__icontains=search)
                | Q(license_plate__icontains=search)
                | Q(vehicle_type__icontains=search)
            )
        if vehicle_type in (Vehicle.VehicleType.MOTORBIKE, Vehicle.VehicleType.CAR):
            qs = qs.filter(vehicle_type=vehicle_type)
        if min_price:
            try:
                qs = qs.filter(base_price_per_day__gte=Decimal(min_price))
            except Exception:
                pass
        if max_price:
            try:
                qs = qs.filter(base_price_per_day__lte=Decimal(max_price))
            except Exception:
                pass

        sort_map = {
            'price_asc': 'base_price_per_day',
            'price_desc': '-base_price_per_day',
            'newest': '-id',
            'rating': '-average_rating',
        }
        if sort in sort_map:
            if sort == 'rating':
                from django.db.models import Avg
                qs = qs.annotate(average_rating=Avg('reviews__rating')).order_by('-average_rating')
            else:
                qs = qs.order_by(sort_map[sort])
        return qs


# ---------------------------------------------------------------------------
# 3. Vehicle detail
# ---------------------------------------------------------------------------
class VehicleDetailAPIView(generics.RetrieveAPIView):
    queryset = Vehicle.objects.select_related('shop', 'shop__owner').prefetch_related(
        'images', 'reviews', 'reviews__user',
    )
    serializer_class = VehicleDetailSerializer


# ---------------------------------------------------------------------------
# 4. Bargains
# ---------------------------------------------------------------------------
class BargainCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = PriceBargainSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data
        vehicle = vdata['vehicle']

        # Nếu đã có phiên thương lượng chờ duyệt, cập nhật lại thay vì tạo mới.
        existing = PriceBargain.objects.filter(
            user=request.user, vehicle=vehicle, status=PriceBargain.Status.PENDING,
        ).first()

        if existing:
            for field in ('offered_price_per_day', 'rental_days', 'customer_type', 'note'):
                setattr(existing, field, vdata[field])
            existing.save()
            out = PriceBargainSerializer(existing, context={'request': request}).data
            return Response(out, status=status.HTTP_200_OK)

        bargain = PriceBargain.objects.create(
            vehicle=vehicle,
            user=request.user,
            shop=vehicle.shop,
            offered_price_per_day=vdata['offered_price_per_day'],
            rental_days=vdata['rental_days'],
            customer_type=vdata['customer_type'],
            note=vdata.get('note', ''),
        )
        out = PriceBargainSerializer(bargain, context={'request': request}).data
        return Response(out, status=status.HTTP_201_CREATED)


class BargainRespondAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStaff, IsShopOwnerOrAdmin]

    def get_object(self, pk):
        obj = generics.get_object_or_404(PriceBargain.objects.select_related('shop', 'vehicle'), pk=pk)
        self.check_object_permissions(self.request, obj)
        return obj

    def patch(self, request, pk, *args, **kwargs):
        bargain = self.get_object(pk)
        serializer = BargainRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        bargain.status = data['status']
        if data['status'] == PriceBargain.Status.COUNTERED:
            bargain.counter_price = _money(data['counter_price'])
        elif data['status'] == PriceBargain.Status.ACCEPTED:
            bargain.counter_price = None
        bargain.save()

        out = PriceBargainSerializer(bargain, context={'request': request}).data
        return Response(out, status=status.HTTP_200_OK)


class MyBargainsAPIView(generics.ListAPIView):
    serializer_class = PriceBargainSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PriceBargain.objects.filter(user=self.request.user).select_related('vehicle', 'shop')


class StaffBargainsAPIView(generics.ListAPIView):
    serializer_class = PriceBargainSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaff]

    def get_queryset(self):
        qs = PriceBargain.objects.select_related('vehicle', 'shop', 'user')
        user = self.request.user
        if user.role != 'admin':
            qs = qs.filter(shop__owner=user)
        status_filter = self.request.query_params.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


# ---------------------------------------------------------------------------
# 6. Cart
# ---------------------------------------------------------------------------
class CartAddAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data
        vehicle = vdata['vehicle']

        price, is_bargain = get_applicable_price(request.user, vehicle)
        total_days = (vdata['end_date'] - vdata['start_date']).days
        deposit = _money(Decimal(total_days) * price * Decimal(str(settings.BOOKXE_DEPOSIT_RATE)))

        cart, _ = DepositCart.objects.get_or_create(user=request.user)
        DepositCartItem.objects.update_or_create(
            cart=cart,
            vehicle=vehicle,
            defaults={
                'start_date': vdata['start_date'],
                'end_date': vdata['end_date'],
                'total_days': total_days,
                'applied_price_per_day': price,
                'is_bargain_price': is_bargain,
                'deposit_amount': deposit,
            },
        )
        out = CartSerializer(cart, context={'request': request}).data
        return Response(out, status=status.HTTP_200_OK)


class CartAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cart, _ = DepositCart.objects.get_or_create(user=request.user)
        out = CartSerializer(cart, context={'request': request}).data
        return Response(out, status=status.HTTP_200_OK)


class CartItemUpdateAPIView(APIView):
    """Cập nhật số ngày thuê: [-] [số ngày] [+].

    Tự động tính end_date = start_date + timedelta(days=total_days),
    tính lại tiền thuê (line_total) và tiền cọc 30%.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _update(self, request, item_id, *args, **kwargs):
        cart, _ = DepositCart.objects.get_or_create(user=request.user)
        item = get_object_or_404(DepositCartItem, pk=item_id, cart=cart)

        serializer = CartUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        total_days = serializer.validated_data['total_days']

        item.total_days = total_days
        item.end_date = item.start_date + timedelta(days=total_days)
        item.deposit_amount = _money(
            Decimal(total_days)
            * item.applied_price_per_day
            * Decimal(str(settings.BOOKXE_DEPOSIT_RATE))
        )
        item.save(update_fields=['total_days', 'end_date', 'deposit_amount'])

        out = CartSerializer(cart, context={'request': request}).data
        return Response(out, status=status.HTTP_200_OK)

    def post(self, request, item_id, *args, **kwargs):
        return self._update(request, item_id, *args, **kwargs)

    def patch(self, request, item_id, *args, **kwargs):
        return self._update(request, item_id, *args, **kwargs)


class CartItemDeleteAPIView(APIView):
    """Xóa đúng item theo id + user, trả về tổng tiền mới và số item còn lại."""

    permission_classes = [permissions.IsAuthenticated]

    def _delete(self, request, item_id, *args, **kwargs):
        cart, _ = DepositCart.objects.get_or_create(user=request.user)
        item = DepositCartItem.objects.filter(pk=item_id, cart=cart).first()
        if item is None:
            return Response({'detail': 'Không tìm thấy xe trong giỏ.'}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        out = CartSerializer(cart, context={'request': request}).data
        return Response(out, status=status.HTTP_200_OK)

    def delete(self, request, item_id, *args, **kwargs):
        return self._delete(request, item_id, *args, **kwargs)

    def post(self, request, item_id, *args, **kwargs):
        return self._delete(request, item_id, *args, **kwargs)


# ---------------------------------------------------------------------------
# 7. Checkout - tao don, QR, gui email
# ---------------------------------------------------------------------------
class CheckoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data

        cart, _ = DepositCart.objects.get_or_create(user=request.user)
        items = list(cart.cart_items.select_related('vehicle', 'vehicle__shop'))
        if not items:
            return Response({'detail': 'Giỏ đặt cọc của bạn đang trống.'}, status=status.HTTP_400_BAD_REQUEST)

        # Gom các xe theo cửa hàng -> mỗi cửa hàng một đơn hàng.
        grouped = {}
        for item in items:
            grouped.setdefault(item.vehicle.shop_id, []).append(item)

        created_orders = []
        with transaction.atomic():
            for shop_id, group in grouped.items():
                total_rental = sum(_money(i.line_total) for i in group)
                deposit_paid = sum(_money(i.deposit_amount) for i in group)

                order = BookingOrder.objects.create(
                    order_code=make_order_code(),
                    user=request.user,
                    shop_id=shop_id,
                    pickup_address=vdata['pickup_address'],
                    receiver_name=vdata.get('receiver_name', ''),
                    receiver_phone=vdata['receiver_phone'],
                    customer_note=vdata.get('customer_note', ''),
                    total_rental_amount=total_rental,
                    deposit_paid_amount=deposit_paid,
                    payment_method=vdata['payment_method'],
                )

                for i in group:
                    BookingOrderItem.objects.create(
                        order=order,
                        vehicle=i.vehicle,
                        vehicle_name=i.vehicle.name,
                        license_plate=i.vehicle.license_plate,
                        start_date=i.start_date,
                        end_date=i.end_date,
                        total_days=i.total_days,
                        price_per_day=i.applied_price_per_day,
                        was_bargain_price=i.is_bargain_price,
                    )

                # VietQR URL và email chỉ là bước phụ: lỗi/chậm cũng KHÔNG được làm đơn hàng fail.
                # generate_booking_qr() bị xóa - chỉ trả về URL ảnh VietQR từ remote.
                # Mã QR sẽ được load từ VietQR URL trên giao diện web và email.
                try:
                    from rental.utils import build_vietqr_url
                    _vietqr_url = build_vietqr_url(
                        amount=int(order.deposit_paid_amount),
                        note=order.order_code,
                    )
                except Exception as exc:
                    logging.getLogger(__name__).exception(
                        'Tạo VietQR URL thất bại cho đơn %s: %s', order.order_code, exc,
                    )

                try:
                    send_order_confirmation_email(order, request.user)
                except Exception as exc:
                    logging.getLogger(__name__).exception(
                        'Gửi email xác nhận thất bại cho đơn %s: %s', order.order_code, exc,
                    )

                created_orders.append(order)

            cart.cart_items.all().delete()

        out = BookingOrderSerializer(created_orders, many=True, context={'request': request}).data
        return Response(
            {
                'order': out[0],
                'orders': out,
                'message': 'Đặt cọc thành công! Đơn hàng đã được tạo. Vui lòng xem mã QR và thông tin thanh toán tại trang xác nhận.',
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# 8. Blogs & Reviews
# ---------------------------------------------------------------------------
class BlogListAPIView(generics.ListAPIView):
    serializer_class = BlogListSerializer

    def get_queryset(self):
        qs = ShopBlog.objects.select_related('shop', 'featured_vehicle').all()
        shop_id = self.request.query_params.get('shop_id', '').strip()
        shop_slug = self.request.query_params.get('shop_slug', '').strip()
        if shop_id:
            qs = qs.filter(shop_id=shop_id)
        if shop_slug:
            qs = qs.filter(shop__slug=shop_slug)
        return qs


class BlogDetailAPIView(generics.RetrieveAPIView):
    queryset = ShopBlog.objects.select_related(
        'shop', 'author', 'featured_vehicle',
    ).prefetch_related('reviews', 'reviews__user')
    serializer_class = BlogDetailSerializer
    lookup_field = 'slug'


class ReviewCreateAPIView(APIView):
    """Đánh giá sao (1 lần) + bình luận (không giới hạn số lần).

    - Chưa nhập comment -> 400, tuyệt đối không lưu/đánh giá.
    - Chưa từng đánh giá sao -> bắt buộc rating 1..5 + comment.
    - Đã đánh giá sao rồi -> bỏ qua rating, lưu bản ghi mới với rating=None.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        payload = dict(request.data)
        # DRF QueryDict -> list values; serializer cần scalar.
        if hasattr(request.data, 'dict'):
            payload = request.data.dict()

        vehicle_id = payload.get('vehicle') or payload.get('vehicle_id')
        blog_id = payload.get('blog') or payload.get('blog_id')

        if bool(vehicle_id) == bool(blog_id):
            return Response(
                {'detail': 'Vui lòng gửi đánh giá cho đúng một đối tượng: vehicle hoặc blog.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = (payload.get('comment') or '').strip()
        if not comment:
            return Response(
                {'detail': 'Vui lòng nhập nội dung bình luận trước khi gửi!'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_lookup = {'vehicle_id' if vehicle_id else 'blog_id': vehicle_id or blog_id}
        has_rated = ReviewComment.objects.filter(
            user=request.user, rating__isnull=False, **target_lookup,
        ).exists()

        data = {'comment': comment}
        if vehicle_id:
            data['vehicle'] = vehicle_id
        else:
            data['blog'] = blog_id

        if has_rated:
            # Đã đánh giá sao -> chỉ lưu comment, rating luôn là None.
            data['rating'] = None
        else:
            raw_rating = payload.get('rating')
            try:
                rating = int(raw_rating)
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'Vui lòng chọn từ 1 đến 5 sao trước khi gửi!'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if rating < 1 or rating > 5:
                return Response(
                    {'detail': 'Điểm đánh giá phải nằm trong khoảng 1 đến 5.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data['rating'] = rating

        serializer = ReviewSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data

        review_kwargs = {'user': request.user, 'comment': comment, 'rating': vdata.get('rating')}
        if 'vehicle' in vdata:
            review_kwargs['vehicle'] = vdata['vehicle']
        else:
            review_kwargs['blog'] = vdata['blog']

        review = ReviewComment.objects.create(**review_kwargs)
        out = ReviewSerializer(review, context={'request': request}).data
        return Response(out, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Dashboards support APIs
# ---------------------------------------------------------------------------
class MyOrdersAPIView(generics.ListAPIView):
    serializer_class = BookingOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BookingOrder.objects.filter(user=self.request.user).select_related('shop').prefetch_related('items')


class StaffOrdersAPIView(generics.ListAPIView):
    serializer_class = BookingOrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaff]

    def get_queryset(self):
        qs = BookingOrder.objects.select_related('shop', 'user').prefetch_related('items')
        if self.request.user.role != 'admin':
            qs = qs.filter(shop__owner=self.request.user)
        return qs


class AdminStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request, *args, **kwargs):
        from .models import User
        return Response({
            'total_users': User.objects.count(),
            'total_staff': User.objects.filter(role='staff').count(),
            'total_shops': RentalShop.objects.count(),
            'total_vehicles': Vehicle.objects.count(),
            'total_orders': BookingOrder.objects.count(),
            'total_deposit': BookingOrder.objects.aggregate(s=Sum('deposit_paid_amount'))['s'] or 0,
            'pending_bargains': PriceBargain.objects.filter(status='pending').count(),
            'total_blogs': ShopBlog.objects.count(),
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 9. Luồng trạng thái đơn hàng (Historys)
# ---------------------------------------------------------------------------
class OrderConfirmDepositAPIView(APIView):
    """Khách bấm "Tôi đã chuyển khoản" hoặc staff bấm "Xác nhận đã nhận cọc".

    pending_deposit -> confirmed. Lưu delivery_time_note và giữ pickup_address.
    """

    permission_classes = [permissions.IsAuthenticated]

    DEFAULT_DELIVERY_NOTE = 'Giao xe trong vòng 1 - 2 giờ tới'

    def post(self, request, pk, *args, **kwargs):
        return self._confirm(request, pk)

    def patch(self, request, pk, *args, **kwargs):
        return self._confirm(request, pk)

    def _confirm(self, request, pk):
        order = get_object_or_404(
            BookingOrder.objects.select_related('shop', 'user').prefetch_related('items'), pk=pk,
        )
        if not can_manage_order(request.user, order):
            return Response(
                {'detail': 'Bạn không có quyền thao tác đơn hàng này.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if order.status == BookingOrder.Status.CONFIRMED:
            out = BookingOrderSerializer(order, context={'request': request}).data
            return Response(out, status=status.HTTP_200_OK)
        if order.status != BookingOrder.Status.PENDING_DEPOSIT:
            return Response(
                {'detail': 'Chỉ có thể xác nhận đơn đang ở trạng thái chờ đặt cọc.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = BookingOrder.Status.CONFIRMED
        order.delivery_time_note = (
            (request.data.get('delivery_time_note') or '').strip() or self.DEFAULT_DELIVERY_NOTE
        )
        order.save(update_fields=['status', 'delivery_time_note'])
        out = BookingOrderSerializer(order, context={'request': request}).data
        return Response(out, status=status.HTTP_200_OK)


class OrderCompleteAPIView(APIView):
    """Staff/admin bấm "Hoàn thiện đơn": confirmed -> completed (xe đã giao)."""

    permission_classes = [permissions.IsAuthenticated, IsStaff]

    def post(self, request, pk, *args, **kwargs):
        return self._complete(request, pk)

    def patch(self, request, pk, *args, **kwargs):
        return self._complete(request, pk)

    def _complete(self, request, pk):
        order = get_object_or_404(
            BookingOrder.objects.select_related('shop', 'user').prefetch_related('items'), pk=pk,
        )
        if not can_manage_order(request.user, order):
            return Response(
                {'detail': 'Bạn không có quyền hoàn thiện đơn hàng này.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if order.status == BookingOrder.Status.COMPLETED:
            out = BookingOrderSerializer(order, context={'request': request}).data
            return Response(out, status=status.HTTP_200_OK)
        if order.status != BookingOrder.Status.CONFIRMED:
            return Response(
                {'detail': 'Chỉ có thể hoàn thiện đơn đã xác nhận chuyển khoản.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = BookingOrder.Status.COMPLETED
        if not order.delivery_time_note:
            order.delivery_time_note = OrderConfirmDepositAPIView.DEFAULT_DELIVERY_NOTE
        order.save(update_fields=['status', 'delivery_time_note'])
        out = BookingOrderSerializer(order, context={'request': request}).data
        return Response(out, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 10. Admin: đổi role nhanh & xem toàn bộ lịch sử đặt xe
# ---------------------------------------------------------------------------
class AdminUserListAPIView(generics.ListAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return User.objects.all().order_by('id')


class AdminUserRoleUpdateAPIView(APIView):
    """Admin đổi role user/staff/admin trực tiếp trên dashboard_admin.html."""

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request, pk, *args, **kwargs):
        return self._update(request, pk)

    def patch(self, request, pk, *args, **kwargs):
        return self._update(request, pk)

    def _update(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = UserRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.role = serializer.validated_data['role']
        user.save()  # User.save() đồng bộ is_staff/is_superuser + tạo shop cho staff.
        out = AdminUserSerializer(user, context={'request': request}).data
        return Response(
            {'detail': f'Đã cập nhật quyền của {user.username} thành {user.get_role_display()}.', 'user': out},
            status=status.HTTP_200_OK,
        )


class AdminOrderListAPIView(generics.ListAPIView):
    serializer_class = BookingOrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return BookingOrder.objects.select_related(
            'shop', 'user',
        ).prefetch_related('items').all().order_by('-created_at')


# ---------------------------------------------------------------------------
# 11. Đăng Blog mới (Admin & Staff)
# ---------------------------------------------------------------------------
class BlogCreateAPIView(APIView):
    """Admin (is_superuser/role=admin) và staff (role=staff) đều đăng được blog."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if not (is_admin_user(user) or getattr(user, 'role', '') == 'staff'):
            return Response(
                {'detail': 'Chỉ Admin hoặc Chủ cửa hàng được đăng bài viết.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BlogCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data

        if is_admin_user(user):
            shop = getattr(user, 'shop', None)
            if shop is None:
                shop = RentalShop.objects.order_by('id').first()
            if shop is None:
                shop = RentalShop.objects.create(
                    owner=user,
                    shop_name=f'Cửa hàng của {user.username}',
                    city_district='Đà Nẵng',
                    exact_address='Chưa cập nhật địa chỉ cửa hàng',
                    description='Cửa hàng cho thuê xe BookXe - đang cập nhật thông tin.',
                )
        else:
            shop = getattr(user, 'shop', None)
            if shop is None:
                return Response(
                    {'detail': 'Tài khoản staff chưa có cửa hàng. Vui lòng liên hệ Admin.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        blog = ShopBlog.objects.create(
            shop=shop,
            author=user,
            title=vdata['title'],
            content=vdata['content'],
            promo_badge=vdata.get('promo_badge', ''),
            featured_vehicle_id=vdata.get('featured_vehicle'),
        )

        # Upload ảnh đại diện bài viết (FormData / multipart).
        thumbnail = request.FILES.get('thumbnail')
        if thumbnail:
            blog.thumbnail = thumbnail
            blog.save(update_fields=['thumbnail'])

        out = BlogListSerializer(blog, context={'request': request}).data
        return Response(
            {'detail': 'Đăng bài thành công!', 'blog': out},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# 12. Upload ảnh: Cửa hàng & Sản phẩm xe (multipart/form-data)
# ---------------------------------------------------------------------------
def _shop_for_user(user):
    """Lấy cửa hàng của staff/admin; tự tạo nếu chưa có."""
    shop = getattr(user, 'shop', None)
    if shop is not None:
        return shop
    if is_admin_user(user):
        shop = RentalShop.objects.order_by('id').first()
        if shop is not None:
            return shop
    if is_admin_user(user) or getattr(user, 'role', '') == 'staff':
        return RentalShop.objects.create(
            owner=user,
            shop_name=f'Cửa hàng của {user.username}',
            city_district='Đà Nẵng',
            exact_address='Chưa cập nhật địa chỉ cửa hàng',
            description='Cửa hàng cho thuê xe BookXe - đang cập nhật thông tin.',
        )
    return None


def _can_manage_vehicle(user, vehicle):
    return is_admin_user(user) or (
        getattr(user, 'role', '') == 'staff'
        and getattr(vehicle.shop, 'owner_id', None) == user.id
    )


class ProductListAPIView(generics.ListAPIView):
    """Danh sách mọi xe cho thuê, lọc theo từ khóa / giá / loại / khu vực."""

    serializer_class = VehicleListSerializer

    def get_queryset(self):
        qs = Vehicle.objects.select_related('shop').prefetch_related('images', 'reviews')
        params = self.request.query_params
        search = params.get('search', '').strip()
        vehicle_type = params.get('vehicle_type', '').strip()
        city = params.get('city', '').strip()
        min_price = params.get('min_price', '').strip()
        max_price = params.get('max_price', '').strip()
        sort = params.get('sort', '').strip()

        if params.get('mine') and self.request.user.is_authenticated:
            qs = qs.filter(shop__owner=self.request.user)
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(brand__icontains=search)
                | Q(license_plate__icontains=search) | Q(shop__shop_name__icontains=search)
                | Q(shop__city_district__icontains=search)
            )
        if vehicle_type in (Vehicle.VehicleType.MOTORBIKE, Vehicle.VehicleType.CAR):
            qs = qs.filter(vehicle_type=vehicle_type)
        if city:
            qs = qs.filter(shop__city_district__icontains=city)
        if min_price:
            try:
                qs = qs.filter(base_price_per_day__gte=Decimal(min_price))
            except Exception:
                pass
        if max_price:
            try:
                qs = qs.filter(base_price_per_day__lte=Decimal(max_price))
            except Exception:
                pass

        sort_map = {
            'price_asc': 'base_price_per_day', 'price_desc': '-base_price_per_day',
            'newest': '-id',
        }
        if sort == 'rating':
            from django.db.models import Avg
            qs = qs.annotate(average_rating=Avg('reviews__rating')).order_by('-average_rating')
        elif sort in sort_map:
            qs = qs.order_by(sort_map[sort])
        return qs.order_by('-id') if not qs.ordered else qs


class ProductManageAPIView(APIView):
    """Staff/Admin đăng, sửa, đổi ảnh, đổi trạng thái hoặc xóa xe (Product)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        vehicle = get_object_or_404(Vehicle.objects.select_related('shop'), pk=pk)
        out = VehicleListSerializer(vehicle, context={'request': request}).data
        out['images'] = [
            {'id': img.id, 'url': img.image.url, 'is_primary': img.is_primary}
            for img in vehicle.images.all()
        ]
        return Response(out, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        return self._save(request, None)

    def patch(self, request, pk, *args, **kwargs):
        return self._save(request, pk)

    def put(self, request, pk, *args, **kwargs):
        return self._save(request, pk)

    def delete(self, request, pk, *args, **kwargs):
        vehicle = get_object_or_404(Vehicle.objects.select_related('shop'), pk=pk)
        if not _can_manage_vehicle(request.user, vehicle):
            return Response({'detail': 'Bạn không có quyền xóa chiếc xe này.'},
                            status=status.HTTP_403_FORBIDDEN)
        vehicle.delete()
        return Response({'detail': 'Đã xóa sản phẩm xe.'}, status=status.HTTP_200_OK)

    def _save(self, request, pk):
        user = request.user
        if not (is_admin_user(user) or getattr(user, 'role', '') == 'staff'):
            return Response({'detail': 'Chỉ Admin hoặc Chủ cửa hàng được đăng sản phẩm xe.'},
                            status=status.HTTP_403_FORBIDDEN)

        vehicle = None
        if pk:
            vehicle = get_object_or_404(Vehicle.objects.select_related('shop'), pk=pk)
            if not _can_manage_vehicle(user, vehicle):
                return Response({'detail': 'Bạn không có quyền sửa chiếc xe này.'},
                                status=status.HTTP_403_FORBIDDEN)

        data = request.data
        def get(name, default=None):
            value = data.get(name, default)
            return value if value not in (None, '') else default

        name = (get('name', vehicle.name if vehicle else '') or '').strip()
        brand = (get('brand', vehicle.brand if vehicle else '') or '').strip()
        plate = (get('license_plate', vehicle.license_plate if vehicle else '') or '').strip()
        if not name or not brand or not plate:
            return Response({'detail': 'Vui lòng nhập Tên xe, Hãng xe và Biển số.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            year = int(get('model_year', vehicle.model_year if vehicle else 2026))
            base_price = Decimal(str(get('base_price_per_day',
                                        vehicle.base_price_per_day if vehicle else 0)))
            min_price = Decimal(str(get('min_bargain_price',
                                        vehicle.min_bargain_price if vehicle else 0)))
        except (TypeError, ValueError):
            return Response({'detail': 'Năm sản xuất / giá thuê không hợp lệ.'},
                            status=status.HTTP_400_BAD_REQUEST)

        specs = get('specifications', None)
        if specs is not None and not isinstance(specs, dict):
            try:
                specs = json.loads(specs)
            except Exception:
                return Response({'detail': 'Thông số kỹ thuật phải là JSON hợp lệ.'},
                                status=status.HTTP_400_BAD_REQUEST)
        if specs is None and vehicle:
            specs = vehicle.specifications

        category = (data.get('category') or '').strip()
        if category:
            specs = dict(specs or {})
            specs['Danh mục'] = category

        shop = vehicle.shop if vehicle else _shop_for_user(user)
        if shop is None:
            return Response({'detail': 'Tài khoản chưa có cửa hàng.'},
                            status=status.HTTP_400_BAD_REQUEST)

        fields = {
            'shop': shop,
            'name': name,
            'vehicle_type': get('vehicle_type', vehicle.vehicle_type if vehicle else 'motorbike'),
            'brand': brand,
            'license_plate': plate,
            'model_year': year,
            'base_price_per_day': base_price,
            'min_bargain_price': min_price,
            'condition_status': get('condition_status', vehicle.condition_status if vehicle else ''),
            'allow_bargain': str(get('allow_bargain', 'true')).lower() in ('1', 'true', 'on'),
            'specifications': specs or {},
        }
        if vehicle is None:
            vehicle = Vehicle.objects.create(**fields)
            created = True
        else:
            for key, value in fields.items():
                setattr(vehicle, key, value)
            status_value = data.get('availability_status')
            if status_value:
                vehicle.availability_status = status_value
            vehicle.save()
            created = False

        # Upload ảnh: ảnh đầu tiên làm ảnh đại diện (is_primary=True).
        images = list(request.FILES.getlist('images')) + list(request.FILES.getlist('images[]'))
        if images:
            if not created:
                vehicle.images.all().delete()
            for index, image in enumerate(images):
                VehicleImage.objects.create(
                    vehicle=vehicle, image=image, is_primary=(index == 0),
                )

        out = VehicleListSerializer(vehicle, context={'request': request}).data
        return Response(
            {'detail': 'Đăng sản phẩm xe thành công!' if created else 'Cập nhật xe thành công!',
             'product': out},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class StaffShopAPIView(APIView):
    """Staff tạo/cập nhật thông tin cửa hàng (kèm upload ảnh bìa)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        shop = getattr(request.user, 'shop', None)
        if shop is None:
            return Response({'shop': None}, status=status.HTTP_200_OK)
        return Response(
            {'shop': RentalShopSerializer(shop, context={'request': request}).data},
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        return self._save(request)

    def patch(self, request, *args, **kwargs):
        return self._save(request)

    def put(self, request, *args, **kwargs):
        return self._save(request)

    def _save(self, request):
        user = request.user
        if not (is_admin_user(user) or getattr(user, 'role', '') == 'staff'):
            return Response({'detail': 'Chỉ Admin hoặc Chủ cửa hàng được cập nhật cửa hàng.'},
                            status=status.HTTP_403_FORBIDDEN)

        shop = getattr(user, 'shop', None)
        if shop is None and is_admin_user(user):
            shop = RentalShop.objects.order_by('id').first()
        if shop is not None and not (is_admin_user(user) or shop.owner_id == user.id):
            return Response({'detail': 'Bạn không có quyền cập nhật cửa hàng này.'},
                            status=status.HTTP_403_FORBIDDEN)

        data = request.data
        defaults = {
            'shop_name': 'Cửa hàng của ' + user.username,
            'city_district': 'Đà Nẵng',
            'exact_address': 'Chưa cập nhật địa chỉ cửa hàng',
            'hotline': '',
            'description': '',
        }
        if shop is None:
            shop = RentalShop(owner=user, **defaults)
        for field in defaults:
            value = data.get(field)
            if value is not None and str(value).strip():
                setattr(shop, field, str(value).strip())

        banner = request.FILES.get('banner_image')
        if banner:
            shop.banner_image = banner
        shop.save()

        return Response(
            {'detail': 'Lưu thông tin cửa hàng thành công!',
             'shop': RentalShopSerializer(shop, context={'request': request}).data},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# 13. Danh mục do Admin tạo (Brand / Category / Country) cho form Staff
# ---------------------------------------------------------------------------
class CatalogAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({
            'brands': list(Brand.objects.order_by('name').values_list('name', flat=True)),
            'categories': list(Category.objects.order_by('name').values_list('name', flat=True)),
            'countries': list(
                Country.objects.filter(is_active=True)
                .order_by('display_order', 'name')
                .values_list('name', flat=True)
            ),
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 14. Liên hệ / Báo sự cố xe hư
# ---------------------------------------------------------------------------
def _contact_payload(item):
    return {
        'id': item.id,
        'user_name': item.user.get_full_name() or item.user.username,
        'shop_name': item.shop.shop_name,
        'vehicle_name': f'{item.vehicle.brand} {item.vehicle.name}' if item.vehicle else '',
        'order_code': item.order.order_code if item.order else '',
        'issue_type': item.issue_type,
        'issue_type_display': item.get_issue_type_display(),
        'current_location': item.current_location,
        'phone': item.phone,
        'message': item.message,
        'image_url': item.image.url if item.image else None,
        'status': item.status,
        'status_display': item.get_status_display(),
        'staff_reply': item.staff_reply,
        'is_read_by_staff': item.is_read_by_staff,
        'created_at': item.created_at.strftime('%Y-%m-%d %H:%M'),
    }


class ContactCreateAPIView(APIView):
    """Khách gửi liên hệ / báo sự cố (chấp nhận multipart/form-data + ảnh).

    Các lưu ý quan trọng:
    - Dùng request.data.get() với default '' cho tất cả trường để tránh None.
    - vehicle: chỉ tìm nếu gửi non-empty string; tìm theo pk. Nếu tìm không thấy -> vẫn save (NOT NULL sai).
    - order: tìm theo order_code hoặc order_id; nếu không tìm thấy -> vẫn save, không báo lỗi.
    - phone: nếu trống, tự lấy từ user.phone.
    - issue_type: nếu không trong choices, dùng OTHER.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # --- Lấy shop_id (required) ---
        shop_id = str(request.data.get('shop') or request.data.get('shop_id') or '').strip()
        message = (request.data.get('message') or '').strip()
        if not shop_id:
            return Response({'detail': 'Vui lòng chọn cửa hàng.'},
                            status=status.HTTP_400_BAD_REQUEST)
        shop_exists = RentalShop.objects.filter(pk=shop_id).exists()
        if not shop_exists:
            return Response({'detail': 'Không tìm thấy cửa hàng.'}, status=status.HTTP_400_BAD_REQUEST)

        # --- Lấy vehicle (optional, nullable FK) ---
        vehicle_id_str = str(request.data.get('vehicle') or '').strip()
        vehicle = None
        if vehicle_id_str:
            vehicle = Vehicle.objects.filter(pk=vehicle_id_str).first()
            # Nếu user chọn xe không khớp với cửa hàng này, vẫn chỉ dùng nếu tồn tại

        # --- Lấy order (optional, nullable FK) ---
        order_id = None
        order_code_str = str(request.data.get('order') or request.data.get('order_code') or '').strip()
        if order_code_str:
            booking = BookingOrder.objects.filter(order_code=order_code_str).first()
            if booking:
                order_id = booking.id

        # --- Issue type (default to OTHER if invalid) ---
        issue_type = str(request.data.get('issue_type') or '').strip()
        valid_issue_types = {v for v, _ in ContactSupport.IssueType.choices}
        if issue_type not in valid_issue_types:
            issue_type = ContactSupport.IssueType.OTHER

        # --- Phone: auto-fill from user if empty ---
        phone = str(request.data.get('phone') or '').strip()
        if not phone and request.user.is_authenticated:
            phone = request.user.phone or ''

        # --- Create ContactSupport ---
        try:
            item = ContactSupport.objects.create(
                user=request.user,
                shop_id=shop_id,
                vehicle_id=vehicle.pk if vehicle else None,
                order_id=order_id,
                issue_type=issue_type,
                current_location=str(request.data.get('current_location') or '').strip(),
                phone=phone,
                message=message,
                image=request.FILES.get('image'),
            )
        except Exception as exc:
            return Response({'detail': f'Có lỗi xảy ra khi lưu yêu cầu: {exc}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {'detail': 'Đã gửi yêu cầu hỗ trợ!', 'ticket': _contact_payload(item)},
            status=status.HTTP_201_CREATED,
        )


class ContactMyAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        items = ContactSupport.objects.filter(user=request.user).select_related(
            'shop', 'vehicle', 'order',
        )
        return Response([_contact_payload(i) for i in items], status=status.HTTP_200_OK)


class ContactShopAPIView(APIView):
    """Staff chủ shop / Admin xem các yêu cầu hỗ trợ của cửa hàng mình."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        qs = ContactSupport.objects.select_related('shop', 'vehicle', 'order', 'user')
        if not is_admin_user(user):
            if getattr(user, 'role', '') != 'staff':
                return Response({'detail': 'Không có quyền xem mục này.'},
                                status=status.HTTP_403_FORBIDDEN)
            qs = qs.filter(shop__owner=user)
        items = list(qs)
        # Đánh dấu đã đọc khi staff mở bảng.
        qs.update(is_read_by_staff=True)
        return Response([_contact_payload(i) for i in items], status=status.HTTP_200_OK)


class ContactUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, *args, **kwargs):
        return self._update(request, pk)

    def post(self, request, pk, *args, **kwargs):
        return self._update(request, pk)

    def _update(self, request, pk):
        item = get_object_or_404(ContactSupport.objects.select_related('shop'), pk=pk)
        user = request.user
        if not is_admin_user(user) and not (
            getattr(user, 'role', '') == 'staff' and item.shop.owner_id == user.id
        ):
            return Response({'detail': 'Bạn không có quyền xử lý yêu cầu này.'},
                            status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        if new_status in ContactSupport.Status.values:
            item.status = new_status
        if 'staff_reply' in request.data:
            item.staff_reply = request.data.get('staff_reply') or ''
        item.is_read_by_staff = True
        item.save(update_fields=['status', 'staff_reply', 'is_read_by_staff'])
        return Response(
            {'detail': 'Đã cập nhật yêu cầu hỗ trợ.', 'ticket': _contact_payload(item)},
            status=status.HTTP_200_OK,
        )
