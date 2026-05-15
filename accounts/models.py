from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # AbstractUser provides id, username, password, etc.
    car_efficiency = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10.00,
        help_text="차량 공인 연비 (km/L)"
    )

class Card(models.Model):
    DISCOUNT_TYPES = (
        ('FIXED', '정액 할인 (원)'),
        ('PERCENT', '정률 할인 (%)'),
    )

    card_company = models.CharField(max_length=50, help_text="카드사 (신한, KB 등)")
    card_name = models.CharField(max_length=100, help_text="카드 상품명")
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    target_brand = models.CharField(max_length=50, null=True, blank=True, help_text="할인 적용 대상 정유사 (전체일 경우 비워둠)")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="할인 수치 (원 또는 %)")

    users = models.ManyToManyField(User, related_name='cards', blank=True)

    def __str__(self):
        return f"[{self.card_company}] {self.card_name}"
