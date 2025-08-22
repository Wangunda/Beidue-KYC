# management/commands/setup_kyc.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from kyc.models import Customer, Document, ComplianceAlert

class Command(BaseCommand):
    help = 'Set up KYC system with required groups and permissions'
    
    def handle(self, *args, **options):
        self.stdout.write('Setting up KYC system...')
        
        # Create groups
        kyc_officers_group, created = Group.objects.get_or_create(name='KYC Officers')
        compliance_officers_group, created = Group.objects.get_or_create(name='Compliance Officers')
        customer_service_group, created = Group.objects.get_or_create(name='Customer Service')
        
        # Get content types
        customer_ct = ContentType.objects.get_for_model(Customer)
        document_ct = ContentType.objects.get_for_model(Document)
        alert_ct = ContentType.objects.get_for_model(ComplianceAlert)
        
        # KYC Officers permissions
        kyc_permissions = [
            # Customer permissions
            Permission.objects.get_or_create(
                codename='view_customer',
                name='Can view customer',
                content_type=customer_ct
            )[0],
            Permission.objects.get_or_create(
                codename='change_customer',
                name='Can change customer',
                content_type=customer_ct
            )[0],
            Permission.objects.get_or_create(
                codename='approve_customer',
                name='Can approve customer',
                content_type=customer_ct
            )[0],
            Permission.objects.get_or_create(
                codename='reject_customer',
                name='Can reject customer',
                content_type=customer_ct
            )[0],
            # Document permissions
            Permission.objects.get_or_create(
                codename='view_document',
                name='Can view document',
                content_type=document_ct
            )[0],
            Permission.objects.get_or_create(
                codename='verify_document',
                name='Can verify document',
                content_type=document_ct
            )[0],
        ]
        
        kyc_officers_group.permissions.set(kyc_permissions)
        
        # Compliance Officers permissions (includes all KYC permissions plus more)
        compliance_permissions = kyc_permissions + [
            Permission.objects.get_or_create(
                codename='view_compliancealert',
                name='Can view compliance alert',
                content_type=alert_ct
            )[0],
            Permission.objects.get_or_create(
                codename='change_compliancealert',
                name='Can change compliance alert',
                content_type=alert_ct
            )[0],
            Permission.objects.get_or_create(
                codename='resolve_alert',
                name='Can resolve compliance alert',
                content_type=alert_ct
            )[0],
        ]
        
        compliance_officers_group.permissions.set(compliance_permissions)
        
        # Customer Service permissions (limited)
        customer_service_permissions = [
            Permission.objects.get_or_create(
                codename='view_customer_basic',
                name='Can view basic customer info',
                content_type=customer_ct
            )[0],
        ]
        
        customer_service_group.permissions.set(customer_service_permissions)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up KYC groups and permissions')
        )
        
        # Create sample data (optional)
        create_sample = input('Create sample data? (y/N): ').lower().startswith('y')
        if create_sample:
            self.create_sample_data()
    
    def create_sample_data(self):
        """Create sample customers for testing"""
        from django.contrib.auth.models import User
        from kyc.models import Customer, IndividualCustomer, KYCWorkflow, RiskAssessment
        
        # Create sample users if they don't exist
        admin_user, created = User.objects.get_or_create(
            username='kyc_admin',
            defaults={
                'email': 'admin@beidue.com',
                'first_name': 'KYC',
                'last_name': 'Administrator',
                'is_staff': True
            }
        )
        
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            
            # Add to KYC Officers group
            kyc_group = Group.objects.get(name='KYC Officers')
            admin_user.groups.add(kyc_group)
        
        # Create sample individual customer
        customer1 = Customer.objects.create(
            customer_type='individual',
            name='John Doe',
            email='john.doe@example.com',
            phone_number='+1234567890',
            kyc_type='CDD',
            risk_level='medium',
            status='pending'
        )
        
        IndividualCustomer.objects.create(
            customer=customer1,
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-15',
            nationality='US',
            residential_address='123 Main St, Anytown, ST 12345',
            residential_city='Anytown',
            residential_state='State',
            residential_country='US',
            residential_postal_code='12345',
            occupation='Software Engineer',
            id_type='passport',
            id_number='A12345678'
        )
        
        KYCWorkflow.objects.create(customer=customer1)
        RiskAssessment.objects.create(customer=customer1)
        
        self.stdout.write(
            self.style.SUCCESS('Sample data created successfully')
        )