import datetime
from .models import Shift, Availability, Appointment

def get_available_times(employee, selected_date, slot_minutes=30):
    day_of_week = selected_date.weekday()

    shifts = Shift.objects.filter(
        schedule__employee=employee,
        schedule__is_active=True,
        #schedule__start_date__lte=selected_date,
        #schedule__end_date__gte=selected_date,
        day_of_week=day_of_week
    )

    availability = Availability.objects.filter(
        employee=employee,
        date=selected_date
    ).first()

    if availability and not availability.is_available:
        return [], f"No disponible: {availability.reason}"

    if not shifts:
        return [], "No hay turnos programados para este día"

    existing_appointments = Appointment.objects.filter(
        barber=employee,
        date=selected_date,
        status='scheduled'
    )

    available_times = []
    for shift in shifts:
        current_time = shift.start_time
        end_time = shift.end_time

        while current_time < end_time:
            time_available = True
            for appointment in existing_appointments:
                app_end_time = (datetime.datetime.combine(datetime.date.today(), appointment.time) +
                                datetime.timedelta(minutes=appointment.duration_minutes)).time()

                if (current_time >= appointment.time and current_time < app_end_time) or \
                   (current_time <= appointment.time and
                    (datetime.datetime.combine(datetime.date.today(), current_time) +
                     datetime.timedelta(minutes=slot_minutes)).time() > appointment.time):
                    time_available = False
                    break

            if time_available:
                available_times.append(current_time.strftime('%H:%M'))

            current_time = (datetime.datetime.combine(datetime.date.today(), current_time) +
                            datetime.timedelta(minutes=slot_minutes)).time()

    return available_times, None


from django.core.exceptions import ValidationError

def create_appointment(form, business, customer=None):
    appointment = form.save(commit=False)
    appointment.business = business

    if customer:
        appointment.customer = customer
        appointment.customer_name = f"{customer.first_name} {customer.last_name}"
        appointment.customer_email = customer.user.email

    if hasattr(appointment, 'service'):
        service = appointment.service
        appointment.duration_minutes = getattr(service, 'duration_minutes', 30)
        appointment.price = getattr(service, 'price', 0.0)  # 👈 Aquí se asigna el precio

    appointment.clean()  # Ejecuta validaciones personalizadas del modelo
    appointment.save()

    return appointment
