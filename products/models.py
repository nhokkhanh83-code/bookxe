"""App `products` - khung quản lý Sản phẩm, Cửa hàng, Đơn hàng, Thương lượng.

Proxy model trỏ cùng bảng cũ nên không đổi dữ liệu.
"""
from rental.models import (
    BookingOrder as HistoryBase,
    PriceBargain as BargainBase,
    RentalShop as ShopBase,
    Vehicle as ProductBase,
)


class Product(ProductBase):
    class Meta:
        proxy = True
        verbose_name = 'Product'
        verbose_name_plural = 'Products'


class Shop(ShopBase):
    class Meta:
        proxy = True
        verbose_name = 'Shop'
        verbose_name_plural = 'Shops'


class History(HistoryBase):
    class Meta:
        proxy = True
        verbose_name = 'Order / History'
        verbose_name_plural = 'Orders / Historys'


class Bargain(BargainBase):
    class Meta:
        proxy = True
        verbose_name = 'Price Bargain'
        verbose_name_plural = 'Price Bargains'
