from django.shortcuts import render
from django.db import transaction
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.http import HttpResponseRedirect
from django.views.generic import View, DetailView

from .models import Category, Customer, CartProduct, Product, Order, SubCategory, News
from .mixins import CartMixin
from .forms import OrderForm, LoginForm, RegistrationForm, UserForm, CustomerForm
from .utils import recalculate_cart


class BaseView (CartMixin, View):

    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        sub_categories = SubCategory.objects.all()
        products = Product.objects.all()
        news = News.objects.all()
        context = {'categories': categories,
                   'sub_categories': sub_categories,
                   'products': products,
                   'cart': self.cart,
                   'news': news}
        return render(request, 'index.html', context)


# Представление страницы авторизации
class LoginView(CartMixin, View):

    # функции инициализации представления
    def get(self, request, *args, **kwargs):
        form = LoginForm(request.POST or None)
        categories = Category.objects.all()
        context = {'form': form,
                   'categories': categories,
                   'cart': self.cart}
        return render(request, 'login.html', context)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return HttpResponseRedirect('/')
        categories = Category.objects.all()
        context = {'form': form,
                   'cart': self.cart,
                   'categories': categories}
        return render(request, 'login.html', context)


# Представление страницы регистрации
class RegistrationView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        form = RegistrationForm(request.POST or None)
        categories = Category.objects.all()
        context = {'form': form,
                   'categories': categories,
                   'cart': self.cart}
        return render(request, 'registration.html', context)

    def post(self, request, *args, **kwargs):
        form = RegistrationForm(request.POST or None)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.username = form.cleaned_data['username']
            new_user.email = form.cleaned_data['email']
            new_user.first_name = form.cleaned_data['first_name']
            new_user.last_name = form.cleaned_data['last_name']
            new_user.save()
            new_user.set_password(form.cleaned_data['password'])
            new_user.save()
            Customer.objects.create(user=new_user, phone=form.cleaned_data['phone'], address=form.cleaned_data['address'])
            user = authenticate(username=new_user.username, password=form.cleaned_data['password'])
            login(request, user)
            return HttpResponseRedirect('/')
        categories = Category.objects.all()
        context = {'form': form,
                   'categories': categories,
                   'cart': self.cart}
        return render(request, 'registration.html', context)


# Представление страницы профиля
class ProfileView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        user = request.user
        user_data = {'first_name': user.first_name,
                     'last_name': user.last_name,
                     'email': user.email}
        u_form = UserForm(request.POST or None, initial=user_data)

        customer = Customer.objects.get(user=request.user)
        customer_data = {'address': customer.address,
                         'phone': customer.phone}
        c_form = CustomerForm(request.POST or None, initial=customer_data)

        orders = Order.objects.filter(customer=customer).order_by('-created_at')
        categories = Category.objects.all()
        context = {'orders': orders,
                   'cart': self.cart,
                   'categories': categories,
                   'user': user,
                   'u_form': u_form,
                   'c_form': c_form}
        return render(request, 'profile.html', context)

    def post(self, request, *args, **kwargs):

        user = request.user
        user_data = {'first_name': user.first_name,
                     'last_name': user.last_name,
                     'email': user.email}
        customer = Customer.objects.get(user=request.user)
        customer_data = {'address': customer.address,
                         'phone': customer.phone}
        orders = Order.objects.filter(customer=customer).order_by('-created_at')
        categories = Category.objects.all()

        u_form = UserForm(request.POST or None, initial=user_data, instance=user)
        c_form = CustomerForm(request.POST or None, initial=customer_data, instance=customer)

        if u_form.is_valid() and c_form.is_valid():
            u_form.save()
            c_form.save()
            messages.add_message(request, messages.INFO, 'Данные успешно обновлены')
            return HttpResponseRedirect('/profile/')

        context = {'orders': orders,
                   'cart': self.cart,
                   'categories': categories,
                   'user': user,
                   'u_form': u_form,
                   'c_form': c_form}
        return render(request, 'profile.html', context)


class AddToCartView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        product_slug = kwargs.get('slug')
        product = Product.objects.get(slug=product_slug)
        cart_product, created = CartProduct.objects.get_or_create(user=self.cart.owner, cart=self.cart, product=product)
        if created:
            self.cart.products.add(cart_product)
        recalculate_cart(self.cart)
        messages.add_message(request, messages.INFO, "Товар успешно добавлен")
        return HttpResponseRedirect('/cart/')


class DeleteFromCartView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        product_slug = kwargs.get('slug')
        product = Product.objects.get(slug=product_slug)
        cart_product = CartProduct.objects.get(user=self.cart.owner, cart=self.cart, product=product)
        self.cart.products.remove(cart_product)
        cart_product.delete()
        recalculate_cart(self.cart)
        messages.add_message(request, messages.INFO, "Товар успешно удален")
        return HttpResponseRedirect('/cart/')


class ChangeQTYView(CartMixin, View):

    def post(self, request, *args, **kwargs):
        product_slug = kwargs.get('slug')
        product = Product.objects.get(slug=product_slug)
        cart_product = CartProduct.objects.get(user=self.cart.owner, cart=self.cart, product=product)
        qty = int(request.POST.get('qty'))
        cart_product.qty = qty
        cart_product.save()
        recalculate_cart(self.cart)
        messages.add_message(request, messages.INFO, "Количество успешно изменено")
        return HttpResponseRedirect('/cart/')


class CartView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        form = OrderForm(request.POST or None)
        context = {'cart': self.cart,
                   'categories': categories,
                   'form': form}
        return render(request, 'cart.html', context)


class CheckoutView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        user = request.user
        customer = Customer.objects.get(user=user)
        initial_data = {'first_name': user.first_name,
                        'last_name': user.last_name,
                        'address': customer.address,
                        'phone': customer.phone}
        form = OrderForm(request.POST or None, initial=initial_data)
        context = {'cart': self.cart,
                   'categories': categories,
                   'form': form}
        return render(request, 'checkout.html', context)


class MakeOrderView(CartMixin, View):

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = OrderForm(request.POST or None)
        customer = Customer.objects.get(user=request.user)
        if form.is_valid():
            new_order = form.save(commit=False)
            new_order.customer = customer
            new_order.first_name = form.cleaned_data['first_name']
            new_order.last_name = form.cleaned_data['last_name']
            new_order.phone = form.cleaned_data['phone']
            new_order.address = form.cleaned_data['address']
            new_order.buying_type = form.cleaned_data['buying_type']
            new_order.comment = form.cleaned_data['comment']
            new_order.cart = self.cart
            new_order.cart.in_order = True
            new_order.save()
            self.cart.save()
            customer.orders.add(new_order)
            messages.add_message(request, messages.INFO, 'Спасибо за заказ! Менеджер с Вами свяжется')
            return HttpResponseRedirect('/profile/')
        return HttpResponseRedirect('/checkout/')


class AllNewsView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        news = News.objects.all().order_by('-published')
        context = {'cart': self.cart,
                   'news': news}
        return render(request, 'news.html', context)


class BlanksView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        category = 1
        subcategories = SubCategory.objects.all().filter(category=category)
        categories = Category.objects.all()
        products = Product.objects.all()

        context = {'cart': self.cart,
                   'categories': categories,
                   'subcategories': subcategories,
                   'products': products}
        return render(request, 'blanks.html', context)


class BooksView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        category = 2
        subcategories = SubCategory.objects.all().filter(category=category)
        categories = Category.objects.all()
        products = Product.objects.all()

        context = {'cart': self.cart,
                   'categories': categories,
                   'subcategories': subcategories,
                   'products': products}
        return render(request, 'books.html', context)


class ArtProductsView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        category = 3
        subcategories = SubCategory.objects.all().filter(category=category)
        categories = Category.objects.all()
        products = Product.objects.all()

        context = {'cart': self.cart,
                   'categories': categories,
                   'subcategories': subcategories,
                   'products': products}
        return render(request, 'art_products.html', context)


class OPServiceView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        category = 4
        subcategories = SubCategory.objects.all().filter(category=category)
        products = Product.objects.all().filter(category=subcategories[0])
        context = {'cart': self.cart,
                   'products': products}
        return render(request, 'op_service.html', context)


class PPServiceView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        category = 4
        subcategories = SubCategory.objects.all().filter(category=category)
        products = Product.objects.all().filter(category=subcategories[0])
        context = {'cart': self.cart,
                   'products': products}
        return render(request, 'pp_service.html', context)


class COPServiceView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        category = 4
        subcategories = SubCategory.objects.all().filter(category=category)
        products = Product.objects.all().filter(category=subcategories[0])
        context = {'cart': self.cart,
                   'products': products}
        return render(request, 'cop_service.html', context)


class PrePServiceView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        category = 4
        subcategories = SubCategory.objects.all().filter(category=category)
        products = Product.objects.all().filter(category=subcategories[0])
        context = {'cart': self.cart,
                   'products': products}
        return render(request, 'prep_service.html', context)


class FullPServiceView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        category = 4
        subcategories = SubCategory.objects.all().filter(category=category)
        products = Product.objects.all().filter(category=subcategories[0])
        context = {'cart': self.cart,
                   'products': products}
        return render(request, 'fp_service.html', context)


class AboutView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        context = {'cart': self.cart}
        return render(request, 'about.html', context)


class ContactsView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        context = {'cart': self.cart}
        return render(request, 'contacts.html', context)


class ProductDetailView(CartMixin, DetailView):

    model = Product
    context_object_name = 'product'
    template_name = 'product_detail.html'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = self.get_object().category.__class__.objects.all()
        context['cart'] = self.cart
        return context
