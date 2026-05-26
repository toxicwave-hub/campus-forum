from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('users/<str:username>/', views.user_profile, name='user_profile'),
    path('boards/<slug:slug>/', views.board_detail, name='board_detail'),
    path('boards/<slug:slug>/new/', views.new_post, name='new_post'),
    path('posts/<int:pk>/', views.post_detail, name='post_detail'),
    path('posts/<int:pk>/like/', views.toggle_post_like, name='toggle_post_like'),
    path('replies/<int:pk>/like/', views.toggle_reply_like, name='toggle_reply_like'),
]
