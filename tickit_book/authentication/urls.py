from django.urls import path
from .views import UserRegistrationView, UserLoginView, UserLogoutView, UserProfileView, ChangePasswordView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-registration'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/<str:username>/', UserProfileView.as_view(), name='user-profile-by-username'), # Added username path
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
