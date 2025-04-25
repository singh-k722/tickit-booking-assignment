from rest_framework import serializers
from .models import Journey, Booking, Seat, Payment
from authentication.serializers import UserSerializer
from django.utils import timezone

class JourneySerializer(serializers.ModelSerializer):
    class Meta:
        model = Journey
        fields = '__all__'
        read_only_fields = ('available_seats', 'created_at', 'updated_at')

    def validate(self, data):
        if data['departure_time'] >= data['arrival_time']:
            raise serializers.ValidationError("Arrival time must be after departure time")
        if data['available_seats'] > data['total_seats']:
            raise serializers.ValidationError("Available seats cannot exceed total seats")
        return data

class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = '__all__'
        read_only_fields = ('is_booked', 'booking')

class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    journey = JourneySerializer(read_only=True)
    seats = SeatSerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ('booking_reference', 'total_price', 'booking_time', 'cancelled_time')

    def get_payment(self, obj):
        if hasattr(obj, 'payment'):
            return PaymentSerializer(obj.payment).data
        return None

class CreateBookingSerializer(serializers.ModelSerializer):
    seat_numbers = serializers.ListField(
        child=serializers.CharField(max_length=10),
        write_only=True,
        required=False
    )

    class Meta:
        model = Booking
        fields = ['journey', 'seat_count', 'seat_numbers', 'notes']
        extra_kwargs = {
            'journey': {'required': True},
            'seat_count': {'required': True}
        }

    def validate(self, data):
        journey = data['journey']
        seat_count = data['seat_count']

        if journey.departure_time < timezone.now():
            raise serializers.ValidationError("Cannot book a journey that has already departed")

        if journey.available_seats < seat_count:
            raise serializers.ValidationError("Not enough seats available")

        if 'seat_numbers' in data:
            if len(data['seat_numbers']) != seat_count:
                raise serializers.ValidationError("Number of seat numbers must match seat count")

            unavailable_seats = Seat.objects.filter(
                journey=journey,
                seat_number__in=data['seat_numbers'],
                is_booked=True
            ).exists()

            if unavailable_seats:
                raise serializers.ValidationError("One or more selected seats are already booked")

        return data

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('payment_time',)

class CreatePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'payment_details']
        extra_kwargs = {
            'amount': {'required': True},
            'payment_method': {'required': True}
        }

    def validate_amount(self, value):
        booking = self.context['booking']
        if value != booking.total_price:
            raise serializers.ValidationError("Payment amount must match booking total")
        return value