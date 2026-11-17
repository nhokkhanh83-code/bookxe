"""RBAC permission classes for the BookXe API."""
from rest_framework.permissions import BasePermission

from .models import RentalShop


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsStaff(BasePermission):
    """Chủ cửa hàng (staff) hoặc admin đều được phép truy cập khu vực quản lý."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('staff', 'admin')


class IsShopOwnerOrAdmin(BasePermission):
    """Chỉ chủ cửa hàng sở hữu tài nguyên (hoặc admin) mới được thao tác."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role == 'admin':
            return True

        shop = None
        if isinstance(obj, RentalShop):
            shop = obj
        elif hasattr(obj, 'shop'):
            shop = obj.shop
        elif hasattr(obj, 'vehicle') and obj.vehicle and hasattr(obj.vehicle, 'shop'):
            shop = obj.vehicle.shop

        return bool(shop and shop.owner_id == user.id)
