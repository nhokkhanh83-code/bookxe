from django.apps import AppConfig


class RentalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rental'
    verbose_name = 'CỬA HÀNG & CHO THUÊ XE'

    def ready(self):
        """
        Tương thích Python 3.14 + Django 5.0.14.

        Django 5.0's ``BaseContext.__copy__`` calls ``super().__copy__()`` and
        then assigns ``duplicate.dicts``. Trên Python 3.14, ``super()`` trả về
        một proxy không có ``__dict__`` riêng, nên phép gán đó raise:
            AttributeError: 'super' object has no attribute 'dicts'

        Patch này tạo bản sao trực tiếp từ ``BaseContext.__new__`` và copy
        cả ``__dict__`` lẫn ``dicts``, giúp mọi trang Django Admin
        (change list / change form / add form) chạy bình thường.
        """
        from django.template.context import BaseContext

        def _fixed_base_context_copy(self):
            duplicate = BaseContext.__new__(self.__class__)
            duplicate.__dict__ = self.__dict__.copy()
            duplicate.dicts = self.dicts[:]
            return duplicate

        BaseContext.__copy__ = _fixed_base_context_copy
