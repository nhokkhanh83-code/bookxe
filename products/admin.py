"""Khung PRODUCT: Products, Shops, Orders / Historys, Price Bargains."""
from django.contrib import admin

from rental.admin_helpers import BookXeAdminBase, ShopScopedAdmin, is_admin, is_shop_staff
from rental.models import (
    BookingOrderItem, DepositCartItem, PriceBargain, VehicleImage,
)

from .models import Bargain, History, Product, Shop


class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1
    verbose_name = 'Ảnh xe'
    verbose_name_plural = 'Ảnh xe'

    def has_view_permission(self, request, obj=None):
        return is_admin(request) or is_shop_staff(request)

    def has_add_permission(self, request, obj=None):
        return is_admin(request) or is_shop_staff(request)

    def has_change_permission(self, request, obj=None):
        return is_admin(request) or is_shop_staff(request)

    def has_delete_permission(self, request, obj=None):
        return is_admin(request) or is_shop_staff(request)


class DepositCartItemInline(admin.TabularInline):
    model = DepositCartItem
    extra = 0
    verbose_name = 'Xe trong giỏ đặt cọc'
    verbose_name_plural = 'Xe trong giỏ đặt cọc'

    def has_view_permission(self, request, obj=None):
        return is_admin(request)

    def has_add_permission(self, request, obj=None):
        return is_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_admin(request)


class BookingOrderItemInline(admin.TabularInline):
    model = BookingOrderItem
    extra = 0
    verbose_name = 'Chi tiết xe trong đơn'
    verbose_name_plural = 'Chi tiết xe trong đơn'

    def has_view_permission(self, request, obj=None):
        return is_admin(request) or is_shop_staff(request)

    def has_add_permission(self, request, obj=None):
        return is_admin(request) or is_shop_staff(request)

    def has_change_permission(self, request, obj=None):
        return is_admin(request) or is_shop_staff(request)

    def has_delete_permission(self, request, obj=None):
        return is_admin(request) or is_shop_staff(request)


@admin.register(Product)
class ProductAdmin(ShopScopedAdmin):
    list_display = (
        'name', 'shop', 'vehicle_type', 'brand', 'base_price_per_day',
        'availability_status', 'allow_bargain',
    )
    list_editable = ('base_price_per_day', 'availability_status', 'allow_bargain')
    list_filter = ('vehicle_type', 'availability_status', 'brand', 'shop')
    search_fields = ('name', 'brand', 'license_plate')
    inlines = [VehicleImageInline, DepositCartItemInline]
    ordering = ('-id',)


@admin.register(Shop)
class ShopAdmin(BookXeAdminBase):
    staff_allowed = True
    list_display = ('shop_name', 'owner', 'city_district', 'hotline', 'created_at')
    search_fields = ('shop_name', 'city_district')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_shop_staff(request):
            return qs.filter(owner=request.user)
        return qs

    def save_model(self, request, obj, form, change):
        if is_shop_staff(request) and not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(History)
class HistoryAdmin(ShopScopedAdmin):
    list_display = (
        'order_code', 'user', 'shop', 'receiver_name', 'receiver_phone',
        'pickup_address', 'deposit_paid_amount', 'status', 'created_at',
    )
    list_editable = ('status',)
    list_filter = ('status', 'shop', 'created_at')
    search_fields = ('order_code', 'user__username', 'receiver_phone', 'receiver_name')
    inlines = [BookingOrderItemInline]
    ordering = ('-created_at',)


@admin.register(Bargain)
class BargainAdmin(ShopScopedAdmin):
    list_display = (
        'id', 'user', 'vehicle', 'shop', 'offered_price_per_day',
        'status', 'counter_price', 'created_at',
    )
    list_filter = ('status', 'customer_type')
    search_fields = ('user__username', 'vehicle__name')
    ordering = ('-created_at',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if is_shop_staff(request) and db_field.name == 'shop':
            from rental.models import RentalShop
            kwargs['queryset'] = RentalShop.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
