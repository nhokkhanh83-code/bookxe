"""App `users` - chứa TOÀN BỘ 6 bảng của khung USERS.

Dùng proxy model trỏ cùng bảng cũ nên KHÔNG mất dữ liệu, KHÔNG đổi
AUTH_USER_MODEL - chỉ đổi chỗ đăng ký admin.
"""
from rental.models import (
    BookingOrder as HistoryBase,
    Brand as BrandBase,
    Category as CategoryBase,
    Country as CountryBase,
    User as UserBase,
    Vehicle as ProductBase,
)


class User(UserBase):
    class Meta:
        proxy = True
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class Product(ProductBase):
    class Meta:
        proxy = True
        verbose_name = 'Product'
        verbose_name_plural = 'Products'


class History(HistoryBase):
    class Meta:
        proxy = True
        verbose_name = 'History'
        verbose_name_plural = 'Historys'


class Brand(BrandBase):
    class Meta:
        proxy = True
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'


class Category(CategoryBase):
    class Meta:
        proxy = True
        verbose_name = 'Category'
        verbose_name_plural = 'Categorys'


class Country(CountryBase):
    class Meta:
        proxy = True
        verbose_name = 'Country'
        verbose_name_plural = 'Countrys'
