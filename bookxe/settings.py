"""
Django settings for the BookXe multi-vendor vehicle rental marketplace.
"""
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security / debug
# ---------------------------------------------------------------------------
# SECRET_KEY: Đọc từ .env (BẮT BUỘC cho production). Fallback cho dev.
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-only-change-me-in-production')

# DEBUG: Đọc từ .env, mặc định True cho dễ test
DEBUG = config('DEBUG', default='True', cast=lambda x: x.lower() in ('true', '1', 'yes'))

ALLOWED_HOSTS = [h.strip() for h in config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',') if h.strip()]

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',

    # Local - tách 3 phần ngang hàng: PRODUCT / BLOG / USER
    'blog',
    'products',
    'users',
    'rental',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bookxe.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'rental.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'bookxe.wsgi.application'
ASGI_APPLICATION = 'bookxe.asgi.application'

# ---------------------------------------------------------------------------
# Database - MySQL on XAMPP (phpMyAdmin)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='bookxe'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'rental.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'vi-vn'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 24,
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M',
}

# ---------------------------------------------------------------------------
# Gmail SMTP - email xac nhan don thue xe
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = int(config('EMAIL_PORT', default='587'))
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default='True', cast=lambda x: x.lower() in ('true', '1', 'yes'))
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='nhokkhanh83@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='abietvtwywahkedr')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='BookXe Rental <nhokkhanh83@gmail.com>')

# ---------------------------------------------------------------------------
# Thong tin tai khoan ngan hang de tao noi dung QR chuyen khoan
# ---------------------------------------------------------------------------
BOOKXE_BANK_NAME = config('BOOKXE_BANK_NAME', default='TPBank')
BOOKXE_BANK_ACCOUNT = config('BOOKXE_BANK_ACCOUNT', default='00003771572')
BOOKXE_BANK_HOLDER = config('BOOKXE_BANK_HOLDER', default='NGO DINH BAO KHANH')

# Ti le dat coc mac dinh (30% tong tien thue)
BOOKXE_DEPOSIT_RATE = 0.30
