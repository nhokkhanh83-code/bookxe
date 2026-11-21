"""Khung USER: chỉ bảng Users - Admin chọn đổi quyền trực tiếp trên bảng."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from rental.admin_helpers import BookXeAdminBase, is_admin
from rental.models import DepositCart, RentalShop

from .models import Brand, Category, Country, User


class DepositCartInline(admin.TabularInline):
    model = DepositCart
    extra = 0
    can_delete = False
    readonly_fields = ('created_at', 'updated_at')
    fields = ('created_at', 'updated_at')
    verbose_name = 'Giỏ đặt cọc'
    verbose_name_plural = 'Giỏ đặt cọc'

    def has_view_permission(self, request, obj=None):
        return is_admin(request)

    def has_add_permission(self, request, obj=None):
        return is_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_admin(request)


@admin.register(User)
class BookXeUserAdmin(UserAdmin, BookXeAdminBase):
    """Bảng Users - chỉ Admin được xem/sửa, staff bị ẩn hoàn toàn."""

    staff_allowed = False
    inlines = [DepositCartInline]

    # Cột QUYỀN là menu thả xuống ngay trên bảng; bấm "Lưu" là áp dụng.
    list_display = ('username', 'email', 'role', 'is_student', 'phone', 'is_staff', 'is_active')
    list_editable = ('role', 'is_student', 'is_active')
    list_display_links = ('username', 'email')
    list_filter = ('role', 'is_student', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone')
    ordering = ('username',)

    fieldsets = (
        ('Phân quyền & thông tin BookXe', {
            'fields': ('role', 'phone', 'address', 'is_student'),
        }),
        ('Thông tin đăng nhập', {
            'fields': ('username', 'password'),
        }),
        ('Thông tin cá nhân', {
            'fields': ('first_name', 'last_name', 'email', 'avatar'),
        }),
        ('Trạng thái & quyền hệ thống', {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Thời gian', {
            'classes': ('collapse',),
            'fields': ('last_login', 'date_joined'),
        }),
    )
    add_fieldsets = (
        ('Phân quyền & thông tin BookXe', {
            'fields': ('role', 'phone', 'address', 'is_student'),
        }),
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )

    NHAN_TRUONG = {
        'username': 'Tên đăng nhập', 'password': 'Mật khẩu (đã mã hóa)',
        'password1': 'Mật khẩu', 'password2': 'Xác nhận mật khẩu',
        'role': 'Quyền', 'phone': 'Số điện thoại', 'address': 'Địa chỉ',
        'is_student': 'Đã xác thực sinh viên', 'first_name': 'Họ', 'last_name': 'Tên',
        'email': 'Email', 'is_active': 'Đang hoạt động',
        'is_staff': 'Cho phép vào trang quản trị', 'is_superuser': 'Quản trị hệ thống',
        'groups': 'Nhóm quyền', 'user_permissions': 'Quyền riêng',
        'last_login': 'Lần đăng nhập cuối', 'date_joined': 'Ngày tham gia',
    }

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change=change, **kwargs)
        for ten_truong, nhan in self.NHAN_TRUONG.items():
            if ten_truong in form.base_fields:
                form.base_fields[ten_truong].label = nhan
        return form

    def has_module_permission(self, request):
        return is_admin(request)

    def has_view_permission(self, request, obj=None):
        return is_admin(request)

    def has_add_permission(self, request):
        return is_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_admin(request)

    def save_model(self, request, obj, form, change):
        if obj.role == User.Role.ADMIN:
            obj.is_staff = True
            obj.is_superuser = True
        elif obj.role == User.Role.STAFF:
            obj.is_staff = True
            obj.is_superuser = False
        elif obj.role == User.Role.USER:
            obj.is_staff = False
            obj.is_superuser = False
        elif obj.is_superuser:
            obj.role = User.Role.ADMIN
            obj.is_staff = True

        super().save_model(request, obj, form, change)

        if obj.role == User.Role.STAFF and not hasattr(obj, 'shop'):
            RentalShop.objects.get_or_create(
                owner=obj,
                defaults={
                    'shop_name': f'Cửa hàng của {obj.username}',
                    'city_district': 'Đà Nẵng',
                    'exact_address': 'Chưa cập nhật địa chỉ cửa hàng',
                    'description': 'Cửa hàng cho thuê xe BookXe - đang cập nhật thông tin.',
                },
            )


@admin.register(Brand)
class BrandAdmin(BookXeAdminBase):
    """Bảng Brands - danh mục hãng xe. Chỉ Admin được quản lý."""

    staff_allowed = False
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Category)
class CategoryAdmin(BookXeAdminBase):
    """Bảng Categorys - danh mục loại xe. Chỉ Admin được quản lý."""

    staff_allowed = False
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Country)
class CountryAdmin(BookXeAdminBase):
    """Quản lý Thành phố / Khu vực - CHỈ ADMIN được thêm/sửa/xóa/sắp xếp."""

    staff_allowed = False
    list_display = ('id', 'name', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)
