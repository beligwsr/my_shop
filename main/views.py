from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import *

def get_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart

def index(request):
    banners = Banner.objects.filter(is_active=True)
    categories = Category.objects.filter(parent=None)
    new_products = Product.objects.filter(is_active=True, is_new=True)[:8]
    bestsellers = Product.objects.filter(is_active=True, is_bestseller=True)[:8]
    brands = Brand.objects.filter(is_active=True)
    
    context = {
        'banners': banners,
        'categories': categories,
        'new_products': new_products,
        'bestsellers': bestsellers,
        'brands': brands,
    }
    return render(request, 'main/index.html', context)

def catalog(request):
    products = Product.objects.filter(is_active=True)
    
    # Фильтры
    category_slug = request.GET.get('category')
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    gender = request.GET.get('gender')
    if gender:
        products = products.filter(gender=gender)
    
    brand_id = request.GET.get('brand')
    if brand_id:
        products = products.filter(brand_id=brand_id)
    
    size = request.GET.get('size')
    if size:
        products = products.filter(stocks__size__size=size, stocks__quantity__gt=0).distinct()
    
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    q = request.GET.get('q')
    if q:
        products = products.filter(Q(name__icontains=q) | Q(brand__name__icontains=q))
    
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-created_at')
    elif sort == 'popular':
        products = products.order_by('-sales')
    
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    categories = Category.objects.filter(parent=None)
    brands = Brand.objects.filter(is_active=True)
    sizes = Size.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'brands': brands,
        'sizes': sizes,
        'current_filters': request.GET,
    }
    return render(request, 'main/catalog.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    product.views += 1
    product.save()
    
    sizes = Stock.objects.filter(product=product, quantity__gt=0).select_related('size')
    related = Product.objects.filter(category=product.category, is_active=True).exclude(id=product.id)[:4]
    in_wishlist = request.user.is_authenticated and Wishlist.objects.filter(user=request.user, product=product).exists()
    
    context = {
        'product': product,
        'sizes': sizes,
        'related': related,
        'in_wishlist': in_wishlist,
    }
    return render(request, 'main/product_detail.html', context)

def cart_view(request):
    cart = get_cart(request)
    
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            CartItem.objects.filter(id=item_id, cart=cart).delete()
        else:
            item = get_object_or_404(CartItem, id=item_id, cart=cart)
            item.quantity = quantity
            item.save()
        return redirect('cart')
    
    return render(request, 'main/cart.html', {'cart': cart})

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    size_id = request.POST.get('size')
    
    if not size_id:
        messages.error(request, 'Выберите размер')
        return redirect('product_detail', slug=product.slug)
    
    size = get_object_or_404(Size, id=size_id)
    stock = Stock.objects.filter(product=product, size=size).first()
    
    if not stock or stock.quantity == 0:
        messages.error(request, 'Нет в наличии')
        return redirect('product_detail', slug=product.slug)
    
    cart = get_cart(request)
    cart_item = CartItem.objects.filter(cart=cart, product=product, size=size).first()
    
    if cart_item:
        cart_item.quantity += 1
        cart_item.save()
    else:
        CartItem.objects.create(cart=cart, product=product, size=size, quantity=1)
    
    messages.success(request, f'{product.name} добавлен в корзину')
    return redirect('cart')

def remove_from_cart(request, item_id):
    cart = get_cart(request)
    CartItem.objects.filter(id=item_id, cart=cart).delete()
    messages.success(request, 'Товар удален')
    return redirect('cart')

@login_required
def checkout(request):
    cart = get_cart(request)
    
    if cart.items.count() == 0:
        return redirect('cart')
    
    if request.method == 'POST':
        order = Order.objects.create(
            user=request.user,
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address'),
            city=request.POST.get('city'),
            total=cart.get_total(),
        )
        
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                size=item.size,
                quantity=item.quantity,
                price=item.product.price,
            )
            stock = Stock.objects.get(product=item.product, size=item.size)
            stock.quantity -= item.quantity
            stock.save()
        
        cart.delete()
        messages.success(request, f'Заказ #{order.order_number} оформлен!')
        return redirect('checkout_success', order_id=order.id)
    
    return render(request, 'main/checkout.html', {'cart': cart})

def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'main/checkout_success.html', {'order': order})

@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
        return redirect('wishlist')
    
    return render(request, 'main/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/profile.html', {'orders': orders})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'main/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('index')

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'main/register.html', {'form': form})

def search_suggestions(request):
    q = request.GET.get('q', '')
    if len(q) >= 2:
        products = Product.objects.filter(
            Q(name__icontains=q) | Q(brand__name__icontains=q),
            is_active=True
        )[:5]
        data = [{'name': p.name, 'url': p.get_absolute_url()} for p in products]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)