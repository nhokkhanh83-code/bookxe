"""URL routes cho BookXe REST API."""
from django.urls import path

from . import api_views as api

urlpatterns = [
    # 1. Shops
    path('shops/', api.ShopListAPIView.as_view(), name='api-shops'),

    # 2. Vehicles in shop
    path('shops/<int:pk>/vehicles/', api.ShopVehiclesAPIView.as_view(), name='api-shop-vehicles'),

    # 3. PRODUCT - danh sách & quản lý xe (multipart upload ảnh)
    path('products/', api.ProductListAPIView.as_view(), name='api-products'),
    path('products/create/', api.ProductManageAPIView.as_view(), name='api-product-create'),
    path('products/<int:pk>/', api.ProductManageAPIView.as_view(), name='api-product-manage'),
    path('shop/mine/', api.StaffShopAPIView.as_view(), name='api-shop-mine'),
    path('catalog/', api.CatalogAPIView.as_view(), name='api-catalog'),

    # Vehicle detail
    path('vehicles/<int:pk>/', api.VehicleDetailAPIView.as_view(), name='api-vehicle-detail'),

    # 4. Bargains
    path('bargains/create/', api.BargainCreateAPIView.as_view(), name='api-bargain-create'),
    path('bargains/<int:pk>/respond/', api.BargainRespondAPIView.as_view(), name='api-bargain-respond'),
    path('bargains/mine/', api.MyBargainsAPIView.as_view(), name='api-bargains-mine'),
    path('bargains/shop/', api.StaffBargainsAPIView.as_view(), name='api-bargains-shop'),

    # 6. Cart
    path('cart/add/', api.CartAddAPIView.as_view(), name='api-cart-add'),
    path('cart/', api.CartAPIView.as_view(), name='api-cart'),
    path(
        'cart/items/<int:item_id>/update/',
        api.CartItemUpdateAPIView.as_view(),
        name='api-cart-item-update',
    ),
    path(
        'cart/items/<int:item_id>/remove/',
        api.CartItemDeleteAPIView.as_view(),
        name='api-cart-item-remove',
    ),
    # Giữ route cũ để tương thích với client cũ.
    path('cart/items/<int:item_id>/delete/', api.CartItemDeleteAPIView.as_view(), name='api-cart-delete'),

    # 7. Checkout
    path('checkout/', api.CheckoutAPIView.as_view(), name='api-checkout'),

    # 8. Blogs & Reviews
    path('blogs/', api.BlogListAPIView.as_view(), name='api-blogs'),
    path('blogs/create/', api.BlogCreateAPIView.as_view(), name='api-blog-create'),
    path('blogs/<slug:slug>/', api.BlogDetailAPIView.as_view(), name='api-blog-detail'),
    path('reviews/', api.ReviewCreateAPIView.as_view(), name='api-reviews'),

    # Dashboards
    path('orders/', api.MyOrdersAPIView.as_view(), name='api-orders'),
    path('staff/orders/', api.StaffOrdersAPIView.as_view(), name='api-staff-orders'),
    path('admin/stats/', api.AdminStatsAPIView.as_view(), name='api-admin-stats'),

    # Luồng trạng thái đơn hàng
    path('orders/<int:pk>/confirm-deposit/', api.OrderConfirmDepositAPIView.as_view(), name='api-order-confirm-deposit'),
    path('orders/<int:pk>/complete/', api.OrderCompleteAPIView.as_view(), name='api-order-complete'),

    # Admin: quản lý user & lịch sử đơn
    path('admin/users/', api.AdminUserListAPIView.as_view(), name='api-admin-users'),
    path('admin/users/<int:pk>/role/', api.AdminUserRoleUpdateAPIView.as_view(), name='api-admin-user-role'),
    path('admin/orders/', api.AdminOrderListAPIView.as_view(), name='api-admin-orders'),

    # Liên hệ / báo sự cố xe hư
    path('contact/create/', api.ContactCreateAPIView.as_view(), name='api-contact-create'),
    path('contact/mine/', api.ContactMyAPIView.as_view(), name='api-contact-mine'),
    path('contact/shop/', api.ContactShopAPIView.as_view(), name='api-contact-shop'),
    path('contact/<int:pk>/update/', api.ContactUpdateAPIView.as_view(), name='api-contact-update'),
]
