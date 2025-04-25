from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone

class Journey(models.Model):
    class TransportType(models.TextChoices):
        BUS = 'BUS', 'Bus'
        TRAIN = 'TRAIN', 'Train'
        PLANE = 'PLANE', 'Plane'
        SHIP = 'SHIP', 'Ship'

    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    transport_type = models.CharField(
        max_length=5,
        choices=TransportType.choices,
        default=TransportType.BUS
    )
    transport_name = models.CharField(max_length=100)  # e.g., "Express 123"
    transport_number = models.CharField(max_length=50)  # e.g., "FL123"
    total_seats = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    available_seats = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['departure_time']
        verbose_name_plural = "Journeys"
        constraints = [
            models.CheckConstraint(
                check=models.Q(departure_time__lt=models.F('arrival_time')),
                name='departure_before_arrival'
            ),
            models.CheckConstraint(
                check=models.Q(available_seats__lte=models.F('total_seats')),
                name='available_seats_lte_total'
            )
        ]

    def __str__(self):
        return f"{self.transport_type} {self.transport_number} from {self.source} to {self.destination}"

    def is_upcoming(self):
        return self.departure_time > timezone.now()

    def duration(self):
        return self.arrival_time - self.departure_time


class Booking(models.Model):
    class BookingStatus(models.TextChoices):
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        PENDING = 'PENDING', 'Pending'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='bookings')
    booking_reference = models.CharField(max_length=12, unique=True)
    seat_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=BookingStatus.choices,
        default=BookingStatus.CONFIRMED
    )
    booking_time = models.DateTimeField(auto_now_add=True)
    cancelled_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-booking_time']
        indexes = [
            models.Index(fields=['booking_reference']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"Booking {self.booking_reference} - {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
        if not self.total_price:
            self.total_price = self.journey.price * self.seat_count
        super().save(*args, **kwargs)

    def generate_booking_reference(self):
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    def cancel(self):
        if self.status != self.BookingStatus.CANCELLED:
            self.status = self.BookingStatus.CANCELLED
            self.cancelled_time = timezone.now()
            self.journey.available_seats += self.seat_count
            self.journey.save()
            self.save()


class Seat(models.Model):
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)  # e.g., "A1", "B12"
    is_booked = models.BooleanField(default=False)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seats'
    )
    seat_class = models.CharField(max_length=20, default='Standard')  # e.g., "Business", "Economy"

    class Meta:
        unique_together = ('journey', 'seat_number')
        ordering = ['seat_number']

    def __str__(self):
        return f"Seat {self.seat_number} on {self.journey}"


class Payment(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)  # e.g., "Credit Card", "PayPal"
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    payment_time = models.DateTimeField(auto_now_add=True)
    payment_details = models.JSONField(default=dict)  # Store additional payment info

    def __str__(self):
        return f"Payment {self.transaction_id} for {self.booking}"