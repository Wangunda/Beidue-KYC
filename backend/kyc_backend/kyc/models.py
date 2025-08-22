# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid

class Customer(models.Model):
    CUSTOMER_TYPES = [
        ('individual', 'Individual'),
        ('corporate', 'Corporate'),
    ]
    
    RISK_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
        ('requires_additional_info', 'Requires Additional Information'),
    ]
    
    KYC_TYPES = [
        ('CDD', 'Customer Due Diligence'),
        ('ECDD', 'Enhanced Customer Due Diligence'),
        ('SDD', 'Simplified Due Diligence'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_reference = models.CharField(max_length=20, unique=True, editable=False)
    
    # Basic Information
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # KYC Information
    kyc_type = models.CharField(max_length=10, choices=KYC_TYPES, default='CDD')
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default='medium')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    
    # Risk Assessment
    aml_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    sanctions_checked = models.BooleanField(default=False)
    pep_checked = models.BooleanField(default=False)  # Politically Exposed Person
    adverse_media_checked = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    
    # Review Information
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_customers')
    review_notes = models.TextField(blank=True)
    
    # Compliance
    next_review_date = models.DateTimeField(null=True, blank=True)
    compliance_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_customers')

    class Meta:
        db_table = 'customers'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.customer_reference:
            self.customer_reference = self.generate_customer_reference()
        super().save(*args, **kwargs)

    def generate_customer_reference(self):
        prefix = 'CUST'
        timestamp = timezone.now().strftime('%Y%m%d')
        count = Customer.objects.filter(created_at__date=timezone.now().date()).count() + 1
        return f"{prefix}-{timestamp}-{count:04d}"

    def __str__(self):
        return f"{self.name} ({self.customer_reference})"


class IndividualCustomer(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='individual_details')
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField()
    place_of_birth = models.CharField(max_length=100, blank=True)
    nationality = models.CharField(max_length=50)
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True)
    
    # Address Information
    residential_address = models.TextField()
    residential_city = models.CharField(max_length=100)
    residential_state = models.CharField(max_length=100)
    residential_country = models.CharField(max_length=50)
    residential_postal_code = models.CharField(max_length=20)
    
    # Employment Information
    occupation = models.CharField(max_length=100)
    employer_name = models.CharField(max_length=200, blank=True)
    employer_address = models.TextField(blank=True)
    annual_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    source_of_funds = models.CharField(max_length=100, blank=True)
    
    # Identification
    id_type = models.CharField(max_length=50)  # passport, national_id, driver_license
    id_number = models.CharField(max_length=50)
    id_expiry_date = models.DateField(null=True, blank=True)
    id_issuing_authority = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'individual_customers'


class CorporateCustomer(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='corporate_details')
    
    # Company Information
    legal_name = models.CharField(max_length=255)
    trading_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=50, unique=True)
    incorporation_date = models.DateField()
    incorporation_country = models.CharField(max_length=50)
    legal_form = models.CharField(max_length=100)  # LLC, Corp, Partnership, etc.
    
    # Business Information
    business_type = models.CharField(max_length=100)
    industry_sector = models.CharField(max_length=100)
    business_description = models.TextField()
    website = models.URLField(blank=True)
    
    # Address Information
    registered_address = models.TextField()
    registered_city = models.CharField(max_length=100)
    registered_state = models.CharField(max_length=100)
    registered_country = models.CharField(max_length=50)
    registered_postal_code = models.CharField(max_length=20)
    
    operating_address = models.TextField(blank=True)
    operating_city = models.CharField(max_length=100, blank=True)
    operating_state = models.CharField(max_length=100, blank=True)
    operating_country = models.CharField(max_length=50, blank=True)
    operating_postal_code = models.CharField(max_length=20, blank=True)
    
    # Financial Information
    annual_turnover = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    number_of_employees = models.PositiveIntegerField(null=True, blank=True)
    
    # Regulatory Information
    tax_id = models.CharField(max_length=50, blank=True)
    vat_number = models.CharField(max_length=50, blank=True)
    regulatory_licenses = models.TextField(blank=True)  # JSON field for multiple licenses
    
    class Meta:
        db_table = 'corporate_customers'


class BeneficialOwner(models.Model):
    corporate_customer = models.ForeignKey(CorporateCustomer, on_delete=models.CASCADE, related_name='beneficial_owners')
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=50)
    
    # Ownership Information
    ownership_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    position = models.CharField(max_length=100)  # CEO, Director, Shareholder, etc.
    
    # Address
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=50)
    
    # Identification
    id_type = models.CharField(max_length=50)
    id_number = models.CharField(max_length=50)
    
    # Risk Indicators
    is_pep = models.BooleanField(default=False)  # Politically Exposed Person
    sanctions_hit = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'beneficial_owners'


class Document(models.Model):
    DOCUMENT_TYPES = [
        ('passport', 'Passport'),
        ('national_id', 'National ID'),
        ('driver_license', 'Driver License'),
        ('utility_bill', 'Utility Bill'),
        ('bank_statement', 'Bank Statement'),
        ('incorporation_certificate', 'Certificate of Incorporation'),
        ('memorandum_articles', 'Memorandum & Articles of Association'),
        ('board_resolution', 'Board Resolution'),
        ('financial_statements', 'Financial Statements'),
        ('tax_certificate', 'Tax Certificate'),
        ('regulatory_license', 'Regulatory License'),
        ('other', 'Other'),
    ]
    
    VERIFICATION_STATUS = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='documents')
    
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document_name = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='kyc_documents/')
    file_size = models.PositiveIntegerField()  # in bytes
    file_hash = models.CharField(max_length=64, blank=True)  # SHA-256 hash
    
    # Verification
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    # Document Details
    document_number = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    issuing_authority = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents'


class RiskAssessment(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='risk_assessment')
    
    # Geographic Risk
    country_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    jurisdiction_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Product/Service Risk
    product_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    transaction_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Customer Risk
    customer_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    business_relationship_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Overall Risk
    overall_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    risk_level = models.CharField(max_length=10, choices=Customer.RISK_LEVELS, default='medium')
    
    # Assessment Details
    assessment_method = models.CharField(max_length=50, default='automated')
    assessment_date = models.DateTimeField(auto_now=True)
    assessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Risk Factors (JSON field to store various risk indicators)
    risk_factors = models.JSONField(default=dict, blank=True)
    
    # Monitoring
    next_assessment_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'risk_assessments'


class KYCWorkflow(models.Model):
    WORKFLOW_STATUS = [
        ('initiated', 'Initiated'),
        ('documents_uploaded', 'Documents Uploaded'),
        ('initial_review', 'Initial Review'),
        ('risk_assessment', 'Risk Assessment'),
        ('compliance_review', 'Compliance Review'),
        ('final_approval', 'Final Approval'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='workflow')
    current_step = models.CharField(max_length=30, choices=WORKFLOW_STATUS, default='initiated')
    
    # Step Completion Tracking
    documents_complete = models.BooleanField(default=False)
    identity_verified = models.BooleanField(default=False)
    address_verified = models.BooleanField(default=False)
    sanctions_cleared = models.BooleanField(default=False)
    pep_cleared = models.BooleanField(default=False)
    adverse_media_cleared = models.BooleanField(default=False)
    risk_assessed = models.BooleanField(default=False)
    compliance_approved = models.BooleanField(default=False)
    
    # Workflow Metadata
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_completion = models.DateTimeField(null=True, blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'kyc_workflows'


class AuditTrail(models.Model):
    ACTION_TYPES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('suspend', 'Suspended'),
        ('document_upload', 'Document Uploaded'),
        ('document_verify', 'Document Verified'),
        ('risk_assess', 'Risk Assessed'),
        ('status_change', 'Status Changed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='audit_trail')
    
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField()
    
    # User Information
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Change Details
    field_changed = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    additional_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'audit_trail'
        ordering = ['-timestamp']


class ComplianceAlert(models.Model):
    ALERT_TYPES = [
        ('sanctions_hit', 'Sanctions Hit'),
        ('pep_match', 'PEP Match'),
        ('adverse_media', 'Adverse Media'),
        ('high_risk_country', 'High Risk Country'),
        ('document_expiry', 'Document Expiry'),
        ('review_due', 'Review Due'),
        ('unusual_activity', 'Unusual Activity'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='compliance_alerts')
    
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Alert Details
    triggered_by = models.CharField(max_length=100)  # system, user, external_source
    source_data = models.JSONField(default=dict, blank=True)
    
    # Resolution
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'compliance_alerts'
        ordering = ['-created_at']