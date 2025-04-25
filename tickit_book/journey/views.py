from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Journey, Booking, Payment, Seat
from .serializers import (
    JourneySerializer,
    BookingSerializer,
    PaymentSerializer,
    SeatSerializer,
    CreateBookingSerializer,
    CreatePaymentSerializer
)

class JourneyListCreateView(generics.ListCreateAPIView):
    serializer_class = JourneySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Journey.objects.all()
        source = self.request.query_params.get('source')
        destination = self.request.query_params.get('destination')
        
        if source:
            queryset = queryset.filter(source__icontains=source)
        if destination:
            queryset = queryset.filter(destination__icontains=destination)
        
        upcoming_only = self.request.query_params.get('upcoming', 'true').lower() == 'true'
        if upcoming_only:
            queryset = queryset.filter(departure_time__gte=timezone.now())
        
        return queryset

class JourneyRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Journey.objects.all()
    serializer_class = JourneySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class JourneySeatsListView(generics.ListAPIView):
    serializer_class = SeatSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        journey = get_object_or_404(Journey, pk=self.kwargs['pk'])
        return journey.seats.all()

class BookingListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        return CreateBookingSerializer if self.request.method == 'POST' else BookingSerializer
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        journey = serializer.validated_data['journey']
        seat_count = serializer.validated_data['seat_count']
        seat_numbers = serializer.validated_data.get('seat_numbers', [])
        
        if journey.available_seats < seat_count:
            return Response(
                {'error': 'Not enough seats available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking = Booking.objects.create(
            user=request.user,
            journey=journey,
            seat_count=seat_count,
            total_price=journey.price * seat_count,
            notes=serializer.validated_data.get('notes', '')
        )
        
        if seat_numbers:
            seats = Seat.objects.filter(
                journey=journey,
                seat_number__in=seat_numbers
            )
            for seat in seats:
                seat.is_booked = True
                seat.booking = booking
                seat.save()
        
        journey.available_seats -= seat_count
        journey.save()
        
        return Response(
            BookingSerializer(booking).data,
            status=status.HTTP_201_CREATED
        )

class BookingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        instance.cancel()

class PaymentListCreateView(generics.ListCreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(booking__user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        booking_id = request.data.get('booking')
        booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
        
        if hasattr(booking, 'payment'):
            return Response(
                {'detail': 'Payment already exists for this booking'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CreatePaymentSerializer(
            data=request.data,
            context={'booking': booking}
        )
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(booking=booking)
        
        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED
        )

class PaymentRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(booking__user=self.request.user)

class PaymentRefundView(generics.UpdateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch']
    
    def get_queryset(self):
        return Payment.objects.filter(booking__user=self.request.user)
    
    def patch(self, request, *args, **kwargs):
        payment = self.get_object()
        
        if payment.status != Payment.PaymentStatus.COMPLETED:
            return Response(
                {'detail': 'Only completed payments can be refunded'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.status = Payment.PaymentStatus.REFUNDED
        payment.save()
        
        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_200_OK
        )