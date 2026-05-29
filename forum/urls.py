from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),

    # 简单的用户名+密码注册/登录，不走 allauth
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('me/profile/edit/', views.profile_edit, name='profile_edit'),
    path('me/bookmarks/', views.my_bookmarks, name='bookmarks'),
    path('me/drafts/', views.my_drafts, name='drafts'),

    path('users/<str:username>/', views.user_profile, name='user_profile'),
    path('users/<str:username>/follow/', views.toggle_follow, name='toggle_follow'),
    path('users/<str:username>/followers/', views.followers_list, name='followers'),
    path('users/<str:username>/following/', views.following_list, name='following'),

    path('boards/<slug:slug>/', views.board_detail, name='board_detail'),
    path('boards/<slug:slug>/new/', views.new_post, name='new_post'),
    path('boards/<slug:slug>/subscribe/', views.toggle_subscribe, name='toggle_subscribe'),
    path('boards/<slug:slug>/mod/', views.mod_dashboard, name='mod_dashboard'),

    path('posts/<int:pk>/', views.post_detail, name='post_detail'),
    path('posts/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('posts/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('posts/<int:pk>/vote/', views.post_vote_view, name='post_vote'),
    path('posts/<int:pk>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('posts/<int:pk>/report/', views.report_post, name='report_post'),

    path('replies/<int:pk>/edit/', views.reply_edit, name='reply_edit'),
    path('replies/<int:pk>/delete/', views.reply_delete, name='reply_delete'),
    path('replies/<int:pk>/vote/', views.reply_vote_view, name='reply_vote'),
    path('replies/<int:pk>/bookmark/', views.toggle_reply_bookmark, name='toggle_reply_bookmark'),
    path('replies/<int:pk>/report/', views.report_reply, name='report_reply'),

    path('attachments/<int:pk>/delete/', views.attachment_delete, name='attachment_delete'),

    path('messages/', views.conversations_list, name='conversations'),
    path('messages/<str:username>/', views.conversation_view, name='conversation'),
    path('api/messages/unread/', views.conversations_unread_count, name='messages_unread_api'),

    path('mod/reports/<int:pk>/', views.mod_report_resolve, name='mod_report_resolve'),

    path('api/users/search/', views.user_search_api, name='user_search_api'),

    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/read-all/', views.notifications_mark_all_read, name='notifications_mark_all_read'),
    path('notifications/<int:pk>/open/', views.notification_open, name='notification_open'),
]
