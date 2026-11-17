"""
Seed dữ liệu mẫu cho BookXe (chạy ngay sau khi migrate).

Cách chạy:
    py seed_data.py

Tạo: 1 Admin, 2 Staff (2 cửa hàng), 2 User, 6 xe (xe máy + ô tô),
2 bài Blog ưu đãi và vài đánh giá mẫu. Ảnh minh hoạ được sinh tự động bằng Pillow.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookxe.settings')

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from rental.models import (  # noqa: E402
    PriceBargain, RentalShop, ReviewComment, ShopBlog, User, Vehicle, VehicleImage,
)


def make_image(rel_path, label, color):
    """Tạo ảnh placeholder đơn giản, lưu vào MEDIA_ROOT."""
    path = Path(settings.MEDIA_ROOT) / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new('RGB', (900, 560), color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 460, 900, 560], fill=(15, 23, 42))
    draw.text((30, 490), label, fill=(255, 255, 255))
    draw.text((30, 30), 'BOOKXE RENTAL', fill=(255, 255, 255))
    img.save(path, 'PNG')
    return rel_path


def reset():
    ReviewComment.objects.all().delete()
    ShopBlog.objects.all().delete()
    PriceBargain.objects.all().delete()
    VehicleImage.objects.all().delete()
    Vehicle.objects.all().delete()
    RentalShop.objects.all().delete()
    User.objects.exclude(username='admin').delete()

    # Reset AUTO_INCREMENT để ID dữ liệu mẫu luôn ổn định (1..n) sau mỗi lần seed.
    tables = [
        ReviewComment._meta.db_table, ShopBlog._meta.db_table,
        PriceBargain._meta.db_table, VehicleImage._meta.db_table,
        Vehicle._meta.db_table, RentalShop._meta.db_table, User._meta.db_table,
    ]
    with connection.cursor() as cursor:
        cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
        for table in tables:
            cursor.execute(f'ALTER TABLE `{table}` AUTO_INCREMENT = 1')
        cursor.execute('SET FOREIGN_KEY_CHECKS = 1')


def run():
    print('Bat dau seed du lieu BookXe...')
    reset()

    # ---- 1 Admin ----
    admin, _ = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@bookxe.vn', 'role': User.Role.ADMIN,
                  'first_name': 'BookXe', 'last_name': 'Admin'},
    )
    admin.set_password('admin123')
    admin.role = User.Role.ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.is_active = True
    admin.save()

    # ---- 2 Staff ----
    staff1 = User.objects.create_user(
        username='staff1', email='staff1@bookxe.vn', password='staff123',
        role=User.Role.STAFF, first_name='Nguyen', last_name='Khanh',
        phone='0905111222', address='Da Nang', is_staff=True,
    )
    staff2 = User.objects.create_user(
        username='staff2', email='staff2@bookxe.vn', password='staff123',
        role=User.Role.STAFF, first_name='Tran', last_name='Minh',
        phone='0905333444', address='TP.HCM', is_staff=True,
    )

    # ---- 2 Khach hang ----
    user1 = User.objects.create_user(
        username='user1', email='user1@example.com', password='user123',
        role=User.Role.USER, first_name='An', last_name='Nguyen',
        phone='0912345678', is_student=True, address='Da Nang',
    )
    user2 = User.objects.create_user(
        username='user2', email='user2@example.com', password='user123',
        role=User.Role.USER, first_name='Binh', last_name='Le',
        phone='0923456789', address='TP.HCM',
    )

    # ---- 2 Cua hang ----
    shop1 = RentalShop.objects.create(
        owner=staff1,
        shop_name='Khanh Xe May Da Nang',
        city_district='Da Nang',
        exact_address='123 Nguyen Van Linh, Thanh Khe, Da Nang',
        latitude=16.0544, longitude=108.2022,
        hotline='0905111222',
        description='Cua hang cho thue xe may uy tin tai Da Nang. Xe moi, bao hiem day du, giao xe tan noi.',
        banner_image=make_image('shops/banners/shop1.png', 'KHANH XE MAY - DA NANG', (37, 99, 235)),
    )
    shop2 = RentalShop.objects.create(
        owner=staff2,
        shop_name='Sai Gon Auto Rental',
        city_district='Ho Chi Minh',
        exact_address='45 Le Duan, Quan 1, TP.HCM',
        latitude=10.8231, longitude=106.6297,
        hotline='0905333444',
        description='Cho thue o to tu lai va co tai xe tai TP.HCM. Xe tap trang, gia uu dai cho khach thue dai ngay.',
        banner_image=make_image('shops/banners/shop2.png', 'SAI GON AUTO RENTAL', (16, 185, 129)),
    )

    # ---- 6 Xe ----
    vehicle_defs = [
        dict(shop=shop1, vehicle_type='motorbike', name='AirBlade 2026', brand='Honda',
             license_plate='43A-11111', model_year=2026, base_price_per_day=180000,
             min_bargain_price=130000,
             condition_status='May 95%, lop moi thay, day binh xang, bao hiem day du, 2 mu bao hoi.',
             specifications={'Hop so': 'Tu dong', 'Dung tich / So cho': '125cc', 'Tieu hao nhien lieu': '2.2L/100km'},
             color=(37, 99, 235)),
        dict(shop=shop1, vehicle_type='motorbike', name='Exciter 155', brand='Yamaha',
             license_plate='43A-22222', model_year=2025, base_price_per_day=200000,
             min_bargain_price=150000,
             condition_status='May 90%, phanh dia, lop còn 80%, co bao hoi va ao mua.',
             specifications={'Hop so': 'Co so 6 cap', 'Dung tich / So cho': '155cc', 'Tieu hao nhien lieu': '2.5L/100km'},
             color=(239, 68, 68)),
        dict(shop=shop1, vehicle_type='motorbike', name='Evo 200 (Xe dien)', brand='VinFast',
             license_plate='43A-33333', model_year=2026, base_price_per_day=150000,
             min_bargain_price=110000,
             condition_status='Pin đầy 100%, sac duoc 3 tru, khong can xang, rang khong soi.',
             specifications={'Hop so': 'Tu dong', 'Dung tich / So cho': 'Xe dien', 'Tieu hao nhien lieu': 'Pin 3.5kWh'},
             color=(16, 185, 129)),
        dict(shop=shop2, vehicle_type='car', name='Mazda 3 2024', brand='Mazda',
             license_plate='51A-44444', model_year=2024, base_price_per_day=750000,
             min_bargain_price=580000,
             condition_status='Xe 95%, moi tuan trang noi that, lop moi, day nhien lieu, bao hiem dich vu day du.',
             specifications={'Hop so': 'Tu dong 6 cap', 'Dung tich / So cho': '5 cho', 'Tieu hao nhien lieu': '6.5L/100km'},
             color=(245, 158, 11)),
        dict(shop=shop2, vehicle_type='car', name='Vios 2023', brand='Toyota',
             license_plate='51A-55555', model_year=2023, base_price_per_day=600000,
             min_bargain_price=450000,
             condition_status='Xe 90%, dieu hoa mat, lop con 70%, dang ky hop le, bao hiem TNDS.',
             specifications={'Hop so': 'Tu dong CVT', 'Dung tich / So cho': '5 cho', 'Tieu hao nhien lieu': '5.8L/100km'},
             color=(100, 116, 139)),
        dict(shop=shop2, vehicle_type='car', name='CR-V 2025', brand='Honda',
             license_plate='51A-66666', model_year=2025, base_price_per_day=1100000,
             min_bargain_price=850000,
             condition_status='Xe 98%, 7 cho, camera 360, noi that da, day nhien lieu, bao hiem cao cap.',
             specifications={'Hop so': 'Tu dong CVT', 'Dung tich / So cho': '7 cho', 'Tieu hao nhien lieu': '7.2L/100km'},
             color=(15, 23, 42)),
    ]

    vehicles = []
    for idx, data in enumerate(vehicle_defs, start=1):
        color = data.pop('color')
        img_path = make_image(
            f'vehicles/seed_{idx}.png',
            f'{data["brand"]} {data["name"]} - {data["license_plate"]}',
            color,
        )
        vehicle = Vehicle.objects.create(**data, availability_status=Vehicle.Availability.AVAILABLE)
        VehicleImage.objects.create(vehicle=vehicle, image=img_path, is_primary=True)
        vehicles.append(vehicle)

    # ---- 2 Bai blog ----
    ShopBlog.objects.create(
        shop=shop1, author=staff1,
        title='Moi nhap lo xe tay ga AirBlade 2026 - Giam 25% cho sinh vien',
        promo_badge='Giam 25% cho sinh vien',
        content=(
            'Cua hang vua nhap ve lo AirBlade 2026 hoan toan moi. Xe co bao hiem day du, '
            'giao xe tan noi trong ban kinh Da Nang. Sinh vien xuat trinh the sinh vien duoc '
            'giam ngay 25% khi thue tu 3 ngay. Hay bam "Make an Offer" de gui gia de xuat!'
        ),
        featured_vehicle=vehicles[0],
        thumbnail=make_image('blogs/blog1.png', 'AIRBLADE 2026 - GIAM 25%', (245, 158, 11)),
    )
    ShopBlog.objects.create(
        shop=shop2, author=staff2,
        title='Tan trang 5 chiec Mazda & Vios - Gia thue uu dai mua thap diem',
        promo_badge='Giam 30% xe tan trang',
        content=(
            '5 chiec Mazda 3 va Vios vua duoc tan trang noi that, thay lop moi, ve sinh kim va '
            'lam sach dieu hoa. Gia thue uu dai giam den 30% cho khach thue tu 5 ngay tro len '
            'hoac khach du lich mua thap diem. Dat coc nhanh qua QR, nhan xe tai san bay hoac khach san.'
        ),
        featured_vehicle=vehicles[3],
        thumbnail=make_image('blogs/blog2.png', 'MAZDA & VIOS - GIAM 30%', (16, 185, 129)),
    )

    # ---- Danh gia mau ----
    ReviewComment.objects.create(user=user1, vehicle=vehicles[0], rating=5,
                                 comment='Xe rat moi, chu cua hang thân thiện, giao xe đúng giờ!')
    ReviewComment.objects.create(user=user2, vehicle=vehicles[3], rating=4,
                                 comment='Mazda sạch sẽ, đi êm. Giá thuê hợp lý, sẽ thuê lại lần sau.')

    print('Seed hoan tat!')
    print('------------------------------------------------------------')
    print('Tai khoan de test:')
    print('  Admin : admin / admin123')
    print('  Staff1: staff1 / staff123  (Khanh Xe May Da Nang)')
    print('  Staff2: staff2 / staff123  (Sai Gon Auto Rental)')
    print('  User1 : user1 / user123    (da xac thuc sinh vien)')
    print('  User2 : user2 / user123')
    print('------------------------------------------------------------')
    print('Chay server: py manage.py runserver 127.0.0.1:8000')


if __name__ == '__main__':
    run()
