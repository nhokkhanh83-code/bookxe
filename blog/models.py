"""App `blog` - khung BLOG: Blogs và Review Comments (proxy, không đổi DB)."""
from rental.models import ReviewComment as ReviewCommentBase
from rental.models import ShopBlog as ShopBlogBase


class Blog(ShopBlogBase):
    class Meta:
        proxy = True
        verbose_name = 'Blog'
        verbose_name_plural = 'Blogs'


class ReviewComment(ReviewCommentBase):
    class Meta:
        proxy = True
        verbose_name = 'Review Comment'
        verbose_name_plural = 'Review Comments'
