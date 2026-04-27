from .models import Category, Cart

def cart_count(request):
    """Возвращает количество товаров в корзине"""
    count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            count = cart.get_total_items()
    else:
        if request.session.session_key:
            cart = Cart.objects.filter(session_key=request.session.session_key).first()
            if cart:
                count = cart.get_total_items()
    return {'cart_count': count}

def main_categories(request):
    """Возвращает все активные категории для меню"""
    return {'categories': Category.objects.filter(parent=None)}