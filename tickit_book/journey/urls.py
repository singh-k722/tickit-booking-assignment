from django.urls import path
from .views import (
    JourneyListCreateView,
    JourneyRetrieveUpdateDestroyView,
    JourneySeatsListView,
    BookingListCreateView,
    BookingRetrieveUpdateDestroyView,
    PaymentListCreateView,
    PaymentRetrieveUpdateView,
    PaymentRefundView
)

urlpatterns = [
    # Journey endpoints
    path('journeys/', JourneyListCreateView.as_view(), name='journey-list-create'),
    path('journeys/<int:pk>/', JourneyRetrieveUpdateDestroyView.as_view(), name='journey-detail'),
    path('journeys/<int:pk>/seats/', JourneySeatsListView.as_view(), name='journey-seats'),
    
    # Booking endpoints
    path('bookings/', BookingListCreateView.as_view(), name='booking-list-create'),
    path('bookings/<int:pk>/', BookingRetrieveUpdateDestroyView.as_view(), name='booking-detail'),
    
    # Payment endpoints
    path('payments/', PaymentListCreateView.as_view(), name='payment-list-create'),
    path('payments/<int:pk>/', PaymentRetrieveUpdateView.as_view(), name='payment-detail'),
    path('payments/<int:pk>/refund/', PaymentRefundView.as_view(), name='payment-refund'),
]