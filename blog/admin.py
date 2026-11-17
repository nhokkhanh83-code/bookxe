"""Quản lý bài viết - app riêng `blog` (Admin và Staff đều đăng được)."""
from django.contrib import admin

from rental.admin_helpers import BookXeAdminBase, ShopScopedAdmin, is_admin, is_shop_staff
from rental.models import RentalShop

from .models import Blog, ReviewComment


@admin.register(Blog)
class BlogAdmin(ShopScopedAdmin):
    list_display = ('title', 'shop', 'promo_badge', 'created_at')
    search_fields = ('title', 'content')
    ordering = ('-created_at',)

    def save_model(self, request, obj, form, change):
        if is_shop_staff(request):
            if not obj.shop_id:
                obj.shop = getattr(request.user, 'shop', None)
            if not obj.author_id:
                obj.author = request.user
        elif is_admin(request) and not obj.shop_id:
            # Admin đăng bài mà chưa có shop -> dùng shop đầu tiên hoặc tạo mới.
            obj.shop = (
                RentalShop.objects.order_by('id').first()
                or RentalShop.objects.create(
                    owner=request.user,
                    shop_name=f'Cửa hàng của {request.user.username}',
                    city_district='Đà Nẵng',
                    exact_address='Chưa cập nhật địa chỉ cửa hàng',
                )
            )
            if not obj.author_id:
                obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(ReviewComment)
class ReviewCommentAdmin(BookXeAdminBase):
    """Review Comments - Admin thấy hết, staff thấy bình luận của shop mình."""

    staff_allowed = True
    list_display = ('id', 'user', 'rating', 'vehicle', 'blog', 'created_at')
    list_filter = ('rating',)
    ordering = ('-created_at',)

    def get_queryset(self, request):
        from django.db.models import Q
        qs = super().get_queryset(request)
        if is_shop_staff(request):
            return qs.filter(
                Q(vehicle__shop__owner=request.user) | Q(blog__shop__owner=request.user)
            )
        return qs
