from django.urls import path

from .views import IndexView, SignInView, SignUpView, Logout, ProfileUpdateView, ProfileDetailView, \
    ProfileSelfDetailView, PostDetailView, PostListView, CommentCreateView, MessageListView, ChatDetailView, \
    MessageCreateView, ChatDetailSimple, PostUpView, PostDownView, PostCreateView

urlpatterns = [
    path('', IndexView.as_view(), name='home'),
    path('sign_in/', SignInView.as_view(), name='sign_in'),
    path('sign_up/', SignUpView.as_view(), name='sign_up'),
    path('logout/', Logout.as_view(), name='logout'),
    path('profile/', ProfileSelfDetailView.as_view(), name='profile'),
    path('profile/<int:pk>/', ProfileUpdateView.as_view(), name='profile_update'),
    path('profile/detail/<int:pk>/', ProfileDetailView.as_view(), name='profile_detail'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post_detail'),
    path('post/', PostListView.as_view(), name='posts'),
    path('post/add/', PostCreateView.as_view(), name='post_add'),
    path('comment/add/', CommentCreateView.as_view(), name='comment_add'),
    path('messenger/', MessageListView.as_view(), name='messenger'),
    path('chat/<int:pk>/', ChatDetailView.as_view(), name='chat'),
    path('chat/simple/<int:pk>/', ChatDetailSimple.as_view(), name='chat_simple'),
    path('message/add/', MessageCreateView.as_view(), name='message_add'),
    path('post/up/', PostUpView.as_view(), name='post_up'),
    path('post/down/', PostDownView.as_view(), name='post_down'),
]
