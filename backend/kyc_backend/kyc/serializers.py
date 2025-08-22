# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Customer, IndividualCustomer, CorporateCustomer, 
    BeneficialOwner, Document, RiskAssessment, 
    KYCWorkflow, AuditTrail, ComplianceAlert
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class DocumentSerializer(serializers.ModelSerializer):
    verified_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'document_type', 'document_name', 'file_path',
            'file_size', 'verification_status', 'verified_by',
            'verified_at', 'verification_notes', 'document_number',
            'issue_date', 'expiry_date', 'issuing_authority',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'file_hash', 'verified_by', 'verified_at']

class BeneficialOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeneficialOwner
        fields = [
            'id', 'first_name', 'last_name', 'date_of_birth',
            'nationality', 'ownership_percentage', 'position',
            'address', 'city', 'country', 'id_type', 'id_number',
            'is_pep', 'sanctions_hit', 'created_at', 'updated_at'
        ]

class IndividualCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndividualCustomer
        fields = [
            'first_name', 'last_name', 'middle_name', 'date_of_birth',
            'place_of_birth', 'nationality', 'gender', 'residential_address',
            'residential_city', 'residential_state', 'residential_country',
            'residential_postal_code', 'occupation', 'employer_name',
            'employer_address', 'annual_income', 'source_of_funds',
            'id_type', 'id_number', 'id_expiry_date', 'id_issuing_authority'
        ]

class CorporateCustomerSerializer(serializers.ModelSerializer):
    beneficial_owners = BeneficialOwnerSerializer(many=True, read_only=True)
    
    class Meta:
        model = CorporateCustomer
        fields = [
            'legal_name', 'trading_name', 'registration_number',
            'incorporation_date', 'incorporation_country', 'legal_form',
            'business_type', 'industry_sector', 'business_description',
            'website', 'registered_address', 'registered_city',
            'registered_state', 'registered_country', 'registered_postal_code',
            'operating_address', 'operating_city', 'operating_state',
            'operating_country', 'operating_postal_code', 'annual_turnover',
            'number_of_employees', 'tax_id', 'vat_number',
            'regulatory_licenses', 'beneficial_owners'
        ]

class RiskAssessmentSerializer(serializers.ModelSerializer):
    assessed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = RiskAssessment
        fields = [
            'country_risk_score', 'jurisdiction_risk_score',
            'product_risk_score', 'transaction_risk_score',
            'customer_risk_score', 'business_relationship_risk_score',
            'overall_risk_score', 'risk_level', 'assessment_method',
            'assessment_date', 'assessed_by', 'risk_factors',
            'next_assessment_date', 'created_at', 'updated_at'
        ]

class KYCWorkflowSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(read_only=True)
    
    class Meta:
        model = KYCWorkflow
        fields = [
            'current_step', 'documents_complete', 'identity_verified',
            'address_verified', 'sanctions_cleared', 'pep_cleared',
            'adverse_media_cleared', 'risk_assessed', 'compliance_approved',
            'initiated_at', 'completed_at', 'estimated_completion',
            'assigned_to'
        ]

class AuditTrailSerializer(serializers.ModelSerializer):
    performed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = AuditTrail
        fields = [
            'id', 'action_type', 'description', 'performed_by',
            'ip_address', 'field_changed', 'old_value', 'new_value',
            'timestamp', 'additional_data'
        ]

class ComplianceAlertSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(read_only=True)
    resolved_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ComplianceAlert
        fields = [
            'id', 'alert_type', 'severity', 'status', 'title',
            'description', 'triggered_by', 'source_data',
            'assigned_to', 'resolved_by', 'resolution_notes',
            'resolved_at', 'created_at', 'updated_at'
        ]

class CustomerListSerializer(serializers.ModelSerializer):
    reviewed_by = UserSerializer(read_only=True)
    compliance_officer = UserSerializer(read_only=True)
    document_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_reference', 'customer_type', 'name',
            'email', 'phone_number', 'kyc_type', 'risk_level',
            'status', 'aml_risk_score', 'created_at', 'updated_at',
            'reviewed_by', 'compliance_officer', 'document_count'
        ]
    
    def get_document_count(self, obj):
        return obj.documents.count()

class CustomerDetailSerializer(serializers.ModelSerializer):
    individual_details = IndividualCustomerSerializer(read_only=True)
    corporate_details = CorporateCustomerSerializer(read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    risk_assessment = RiskAssessmentSerializer(read_only=True)
    workflow = KYCWorkflowSerializer(read_only=True)
    compliance_alerts = ComplianceAlertSerializer(many=True, read_only=True)
    audit_trail = AuditTrailSerializer(many=True, read_only=True)
    reviewed_by = UserSerializer(read_only=True)
    compliance_officer = UserSerializer(read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_reference', 'customer_type', 'name',
            'email', 'phone_number', 'kyc_type', 'risk_level',
            'status', 'aml_risk_score', 'sanctions_checked',
            'pep_checked', 'adverse_media_checked', 'created_at',
            'updated_at', 'approved_at', 'rejected_at', 'reviewed_by',
            'review_notes', 'next_review_date', 'compliance_officer',
            'individual_details', 'corporate_details', 'documents',
            'risk_assessment', 'workflow', 'compliance_alerts',
            'audit_trail'
        ]

class CustomerCreateSerializer(serializers.ModelSerializer):
    individual_details = IndividualCustomerSerializer(required=False)
    corporate_details = CorporateCustomerSerializer(required=False)
    
    class Meta:
        model = Customer
        fields = [
            'customer_type', 'name', 'email', 'phone_number',
            'individual_details', 'corporate_details'
        ]
    
    def create(self, validated_data):
        individual_data = validated_data.pop('individual_details', None)
        corporate_data = validated_data.pop('corporate_details', None)
        
        # Determine KYC type based on customer type and risk factors
        kyc_type = 'CDD'
        risk_level = 'medium'
        
        if validated_data['customer_type'] == 'corporate':
            kyc_type = 'ECDD'
            risk_level = 'high'
        
        validated_data['kyc_type'] = kyc_type
        validated_data['risk_level'] = risk_level
        
        customer = Customer.objects.create(**validated_data)
        
        # Create related models
        if individual_data and validated_data['customer_type'] == 'individual':
            IndividualCustomer.objects.create(customer=customer, **individual_data)
        
        if corporate_data and validated_data['customer_type'] == 'corporate':
            CorporateCustomer.objects.create(customer=customer, **corporate_data)
        
        # Create workflow
        KYCWorkflow.objects.create(customer=customer)
        
        # Create initial risk assessment
        RiskAssessment.objects.create(customer=customer)
        
        return customer