import uuid
from django.utils.text import slugify

def generate_unique_slug(model, field, slug_field='slug'):
    """
    Генерация уникального slug для модели
    """
    slug = slugify(field)
    unique_slug = slug
    num = 1
    
    while model.objects.filter(**{slug_field: unique_slug}).exists():
        unique_slug = f'{slug}-{num}'
        num += 1
    
    return unique_slug

def calculate_discount_price(price, discount_percent):
    """
    Расчет цены со скидкой
    """
    return price - (price * discount_percent / 100)

def format_price(price):
    """
    Форматирование цены с пробелами между разрядами
    """
    return f'{price:,.0f}'.replace(',', ' ')

def generate_order_number():
    """
    Генерация уникального номера заказа
    """
    return str(uuid.uuid4()).replace('-', '').upper()[:10]