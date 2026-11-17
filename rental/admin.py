"""App `rental` KHÔNG đăng ký bảng nào trong admin nữa.

Tất cả bảng được quản lý ở 2 app riêng:
    - `blog/admin.py`  -> khung BLOG (Blogs)
    - `users/admin.py` -> khung USERS (Brands, Categorys, Countrys,
                                       Historys, Products, Users)
Việc gỡ đăng ký ở đây giúp khung "BOOKXE - CHO THUÊ XE ĐA CỬA HÀNG"
biến mất hoàn toàn khỏi /admin/.
"""
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.models import Group

from .models import (
    BookingOrder, BookingOrderItem, DepositCart, DepositCartItem,
    PriceBargain, RentalShop, ReviewComment, ShopBlog, User, Vehicle,
    VehicleImage,
)

# Gỡ mọi đăng ký cũ của app rental (phòng trường hợp autodiscover chạy bản cũ).
for _model in (
    User, RentalShop, Vehicle, VehicleImage, PriceBargain,
    BookingOrder, BookingOrderItem, ShopBlog, ReviewComment,
    DepositCart, DepositCartItem,
):
    try:
        admin.site.unregister(_model)
    except NotRegistered:
        pass

# Gỡ luôn nhóm mặc định "Authentication and Authorization" để /admin/
# chỉ còn đúng 2 khung: BLOG và USERS.
try:
    admin.site.unregister(Group)
except NotRegistered:
    pass
