from typing import Callable

from django.contrib.auth import login, logout
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View, UpdateView, ListView, DetailView, CreateView

from .forms import SignInForm, SignUpForm, ProfileForm, ProfileDetailForm, PostForm
from django.contrib.auth import get_user_model

from .models import Post, Comment, Notification, Message, Chat

User = get_user_model()


def only_for_not_authed(f: Callable):
    def wrapper(_, request: HttpRequest, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/')
        return f(_, request, *args, **kwargs)

    return wrapper


def only_for_authed(f: Callable):
    def wrapper(_, request: HttpRequest, *args, **kwargs):
        if request.user.is_authenticated:
            return f(_, request, *args, **kwargs)
        return redirect(reverse_lazy('sign_in'))

    return wrapper


class IndexView(ListView):
    template_name = 'index.html'
    model = Post
    paginate_by = 10
    queryset = Post.objects.all()


class ProfileUpdateView(UpdateView):
    model = User
    fields = ['first_name', 'last_name', 'email', 'description', 'profile_picture']
    success_url = reverse_lazy('profile')
    template_name = 'profile_update.html'


class ProfileSelfDetailView(DetailView):
    model = User
    form_class = ProfileForm()
    template_name = 'profile_update.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        return {'form': ProfileForm(instance=kwargs.get('object')), 'profile_user': kwargs.get('object')}


class ProfileDetailView(DetailView):
    model = User
    form_class = ProfileDetailForm()
    template_name = 'profile_detail.html'

    def get_context_data(self, **kwargs):
        return {'form': ProfileDetailForm(instance=kwargs.get('object')), 'profile_user': kwargs.get('object')}


class SignInView(TemplateView):
    template_name = 'sign_in.html'
    context = {}

    @only_for_not_authed
    def get(self, request, *args, **kwargs):
        self.context.update({'form': SignInForm()})
        return render(request, self.template_name, self.context)

    @only_for_not_authed
    def post(self, request, *args, **kwargs):
        form_data = SignInForm(request.POST)
        if form_data.is_valid():
            login(request, User.objects.get(username=form_data.cleaned_data.get('username')))
            return redirect('/')
        self.context.update({'form': form_data})
        return render(request, self.template_name, self.context)


class SignUpView(TemplateView):
    template_name = 'sign_up.html'
    context = {}

    @only_for_not_authed
    def get(self, request, *args, **kwargs):
        self.context.update({'form': SignUpForm()})
        return render(request, self.template_name, self.context, status=401)

    @only_for_not_authed
    def post(self, request, *args, **kwargs):
        form_data = SignUpForm(request.POST)
        if form_data.is_valid():
            form_data.cleaned_data.pop('password_confirm')
            user = User.objects.create_user(**form_data.cleaned_data)
            login(request, user)
            return redirect('/')
        self.context.update({'form': form_data})
        return render(request, self.template_name, self.context, status=401)


class Logout(View):
    @staticmethod
    def get(request, *args, **kwargs):
        logout(request)
        return redirect('/')


class PostDetailView(DetailView):
    model = Post
    template_name = 'post_detail.html'


class PostListView(ListView):
    model = Post
    template_name = 'posts.html'

    def get(self, request, *args, **kwargs):
        for notification in Notification.objects.filter(type='forum', user=request.user):
            notification.is_read = True
            notification.save()
        return super(PostListView, self).get(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class CommentCreateView(View):
    def post(self, request, *args, **kwargs):
        Comment.objects.create(author=request.user, content=request.POST.get('content'),
                               post_id=request.POST.get('post_id'))
        return HttpResponse('OK')


class MessageListView(ListView):
    model = Chat
    template_name = 'messenger.html'
    paginate_by = 10

    def get_queryset(self):
        return Chat.objects.filter(Q(author=self.request.user) | Q(recipient=self.request.user))

    def get(self, request, *args, **kwargs):
        for notification in Notification.objects.filter(type='message', user=request.user):
            notification.is_read = True
            notification.save()
        return super(MessageListView, self).get(request, *args, **kwargs)


class ChatDetailView(DetailView):
    model = Chat
    template_name = 'chat_detail.html'
    context_object_name = 'chat'


class ChatDetailSimple(DetailView):
    model = Chat
    template_name = 'chat_detail_simple.html'
    context_object_name = 'chat'


@method_decorator(csrf_exempt, name='dispatch')
class MessageCreateView(View):
    def post(self, request, *args, **kwargs):
        chat = Chat.objects.get(id=request.POST.get('chat_id'))
        Message.objects.create(author=request.user, content=request.POST.get('content'), chat=chat,
                               recipient=chat.recipient if chat.recipient != request.user else chat.author)
        return HttpResponse('OK')


@method_decorator(csrf_exempt, name='dispatch')
class PostUpView(View):
    def post(self, request, *args, **kwargs):
        _post = Post.objects.get(id=request.POST.get('post_id'))
        if request.user in _post.vote_up.all():
            _post.vote_up.remove(request.user)
        else:
            _post.vote_up.add(request.user)
            _post.vote_down.remove(request.user)
        return HttpResponse('OK')


@method_decorator(csrf_exempt, name='dispatch')
class PostDownView(View):
    def post(self, request, *args, **kwargs):
        _post = Post.objects.get(id=request.POST.get('post_id'))
        if request.user in _post.vote_down.all():
            _post.vote_down.remove(request.user)
        else:
            _post.vote_down.add(request.user)
            _post.vote_up.remove(request.user)
        return HttpResponse('OK')


class PostCreateView(CreateView):
    model = Post
    template_name = 'post_create.html'
    fields = ['title', 'content']
    success_url = reverse_lazy('home')

    def get_context_data(self, **kwargs):
        return {'form': PostForm()}

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.author = self.request.user
        obj.save()
        return super(PostCreateView, self).form_valid(form)
