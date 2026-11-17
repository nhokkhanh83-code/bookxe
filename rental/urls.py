"""URL trang HTML của BookXe (được include từ bookxe.urls)."""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home_view, name='home'),

    # 1. PRODUCT - sản phẩm & cửa hàng
    path('products/', views.product_list_view, name='product_list'),
    path('shops/<slug:slug>/', views.shop_detail_view, name='shop_detail'),
    path('vehicles/<int:pk>/', views.vehicle_detail_view, name='vehicle_detail'),

    # 2. BLOG
    path('blogs/', views.blog_list_view, name='blog_list'),
    path('blogs/create/', views.blog_create_view, name='blog_create'),
    path('blogs/<slug:slug>/', views.blog_detail_view, name='blog_detail'),

    # 3. USER - giỏ hàng, thanh toán, đơn hàng, dashboard
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('orders/<str:order_code>/', views.order_confirmation_view, name='order_confirmation'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/users/<int:pk>/role/', views.set_user_role_view, name='set_user_role'),
    path('profile/', views.profile_view, name='profile'),
    path('contact/', views.contact_view, name='contact'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
