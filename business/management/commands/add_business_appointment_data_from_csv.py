import os
import csv
import random
from django.core.management.base import BaseCommand
from business.models import BusinessAccount, Appointment, Service, Employee

class Command(BaseCommand):
    help = "Add fake data to a business from a CSV file"

    def handle(self, *args, **kwargs):
        csv_file = 'sample_january_updated.csv' # Remember to change this to the correct path

        if not os.path.exists(csv_file):
            self.stderr.write(f"CSV file '{csv_file}' not found.")
            return

        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                date = row['Date']
                time = row['Time']
                customer_name = row['Customer Name']
                customer_email = row['Customer Email']
                payment_method = row['Payment Method']
                duration_minutes = row['Duration (minutes)']
                customer_satisfaction = row['Customer Satisfaction']
                repeat_customer = row['Repeat Customer']
                no_show = row['No-show']
                status = row['Status']

                business_name = "BarberGreg" # Change this to the actual business name you want to use
                
                try:
                    business = BusinessAccount.objects.filter(name__iexact=business_name).first()
                    service = random.choice(Service.objects.filter(business=business))
                    barber = random.choice(Employee.objects.filter(business=business))
                    Appointment.objects.create(
                        business=business,
                        date=date,
                        time=time,
                        customer_name=customer_name,
                        customer_email=customer_email,
                        service=service,
                        price=service.price,
                        payment_method=payment_method,
                        duration_minutes=duration_minutes,
                        barber=barber,
                        customer_satisfaction=customer_satisfaction,
                        repeat_customer=repeat_customer.lower() == 'yes',
                        no_show=no_show.lower() == 'yes',
                        status=status
                    )

                    self.stdout.write(self.style.SUCCESS(f"Updated: {business_name} - {service} - {date} - {time}"))

                except BusinessAccount.DoesNotExist:
                    self.stderr.write(f"Business not found: {business_name}")
                except Exception as e:
                    self.stderr.write(f"Failed to update {business_name}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f"Finished adding new appointment data to {business.name} from CSV."))
