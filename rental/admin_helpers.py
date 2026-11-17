"""Các lớp/kiểm tra quyền dùng chung cho admin của 3 app: users, blog, rental."""
from django.contrib import admin

from .models import User

# Đổi toàn bộ tiêu đề mặc định sang tiếng Việt.
admin.site.site_header = 'TRANG QUẢN TRỊ BOOKXE'
admin.site.site_title = 'BookXe - Quản trị'
admin.site.index_title = 'BẢNG ĐIỀU KHIỂN BOOKXE'


def is_admin(request):
    """Điều kiện Admin duy nhất dùng cho mọi kiểm tra quyền."""
    return bool(
        request.user.is_authenticated
        and (request.user.is_superuser or getattr(request.user, 'role', '') == 'admin')
    )


def is_shop_staff(request):
    """True nếu người dùng là chủ cửa hàng (không phải superuser/admin)."""
    user = request.user
    return bool(
        user.is_authenticated
        and getattr(user, 'role', '') == User.Role.STAFF
        and not user.is_superuser
    )


class BookXeAdminBase(admin.ModelAdmin):
    """Admin thấy hết; staff chỉ thấy model được đánh dấu ``staff_allowed``."""

    staff_allowed = False

    def _allowed(self, request):
        if not request.user.is_authenticated:
            return False
        if is_admin(request):
            return True
        return is_shop_staff(request) and self.staff_allowed

    def has_module_permission(self, request):
        return self._allowed(request)

    def has_view_permission(self, request, obj=None):
        return self._allowed(request)

    def has_add_permission(self, request):
        return self._allowed(request)

    def has_change_permission(self, request, obj=None):
        return self._allowed(request)

    def has_delete_permission(self, request, obj=None):
        return self._allowed(request)


class ShopScopedAdmin(BookXeAdminBase):
    """Giới hạn dữ liệu theo đúng cửa hàng của staff đăng nhập."""

    staff_allowed = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_shop_staff(request):
            shop = getattr(request.user, 'shop', None)
            if shop is None:
                return qs.none()
            return qs.filter(shop=shop)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if is_shop_staff(request) and db_field.name == 'shop':
            from .models import RentalShop
            kwargs['queryset'] = RentalShop.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if is_shop_staff(request) and hasattr(obj, 'shop') and obj.shop_id is None:
            obj.shop = getattr(request.user, 'shop', None)
        super().save_model(request, obj, form, change)


class BaseInline(admin.TabularInline):
    """Inline dùng để giấu các bảng phụ khỏi menu trái."""

    extra = 0
    staff_allowed = False

    def _allowed(self, request):
        if is_admin(request):
            return True
        return is_shop_staff(request) and self.staff_allowed

    def has_view_permission(self, request, obj=None):
        return self._allowed(request)

    def has_add_permission(self, request, obj=None):
        return self._allowed(request)

    def has_change_permission(self, request, obj=None):
        return self._allowed(request)

    def has_delete_permission(self, request, obj=None):
        return self._allowed(request)
