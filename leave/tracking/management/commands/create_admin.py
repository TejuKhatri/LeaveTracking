from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

class Command(BaseCommand):
    help = 'Create an admin user for the leave management system'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Admin username', default='admin')
        parser.add_argument('--email', type=str, help='Admin email', default='admin@example.com')
        parser.add_argument('--password', type=str, help='Admin password', default='admin123')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        try:
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already exists!')
                )
                # Update existing user to admin role
                user = User.objects.get(username=username)
                user.role = 'admin'
                user.is_staff = True
                user.is_superuser = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated "{username}" to admin role!')
                )
            else:
                # Create new admin user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role='admin',
                    is_staff=True,
                    is_superuser=True
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Admin user "{username}" created successfully!')
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'\nLogin Details:\n'
                    f'Username: {username}\n'
                    f'Password: {password}\n'
                    f'Admin Dashboard: http://127.0.0.1:8000/dashboard/admin/\n'
                    f'Django Admin: http://127.0.0.1:8000/admin/'
                )
            )

        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {e}')
            )