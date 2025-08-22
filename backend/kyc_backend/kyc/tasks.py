# tasks.py - Celery background tasks
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Customer, Document, ComplianceAlert, RiskAssessment
import requests
import logging

logger = logging.getLogger(__name__)

@shared_task
def perform_sanctions_screening(customer_id):
    """
    Background task to perform sanctions screening for a customer
    """
    try:
        customer = Customer.objects.get(id=customer_id)
        
        # Mock API call to sanctions screening service
        screening_data = {
            'name': customer.name,
            'date_of_birth': getattr(customer.individual_details, 'date_of_birth', None),
            'nationality': getattr(customer.individual_details, 'nationality', None),
            'customer_type': customer.customer_type
        }
        
        # Example API call (replace with actual sanctions screening service)
        # response = requests.post(
        #     'https://sanctions-api.example.com/screen',
        #     json=screening_data,
        #     headers={'Authorization': 'Bearer YOUR_API_KEY'}
        # )
        
        # Mock response for demonstration
        mock_response = {
            'sanctions_hit': False,
            'pep_hit': False,
            'adverse_media_hit': False,
            'confidence_score': 0.95,
            'matches': []
        }
        
        # Update customer screening status
        customer.sanctions_checked = True
        customer.pep_checked = True
        customer.adverse_media_checked = True
        
        # Create alerts if hits are found
        if mock_response['sanctions_hit']:
            ComplianceAlert.objects.create(
                customer=customer,
                alert_type='sanctions_hit',
                severity='critical',
                title=f'Sanctions screening hit for {customer.name}',
                description='Potential sanctions match found during automated screening',
                triggered_by='automated_screening',
                source_data=mock_response
            )
        
        if mock_response['pep_hit']:
            ComplianceAlert.objects.create(
                customer=customer,
                alert_type='pep_match',
                severity='high',
                title=f'PEP match for {customer.name}',
                description='Politically Exposed Person match found',
                triggered_by='automated_screening',
                source_data=mock_response
            )
        
        customer.save()
        
        # Update workflow
        if hasattr(customer, 'workflow'):
            customer.workflow.sanctions_cleared = not mock_response['sanctions_hit']
            customer.workflow.pep_cleared = not mock_response['pep_hit']
            customer.workflow.adverse_media_cleared = not mock_response['adverse_media_hit']
            customer.workflow.save()
        
        logger.info(f'Sanctions screening completed for customer {customer.id}')
        
    except Customer.DoesNotExist:
        logger.error(f'Customer {customer_id} not found for sanctions screening')
    except Exception as e:
        logger.error(f'Error during sanctions screening for customer {customer_id}: {str(e)}')

@shared_task
def calculate_risk_assessment(customer_id):
    """
    Background task to calculate comprehensive risk assessment
    """
    try:
        customer = Customer.objects.get(id=customer_id)
        risk_assessment = customer.risk_assessment
        
        # Risk calculation logic
        country_risk = calculate_country_risk(customer)
        customer_risk = calculate_customer_risk(customer)
        product_risk = calculate_product_risk(customer)
        transaction_risk = calculate_transaction_risk(customer)
        
        # Update risk assessment
        risk_assessment.country_risk_score = country_risk
        risk_assessment.customer_risk_score = customer_risk
        risk_assessment.product_risk_score = product_risk
        risk_assessment.transaction_risk_score = transaction_risk
        
        # Calculate overall risk score
        weights = settings.KYC_SETTINGS.get('RISK_ASSESSMENT_WEIGHTS', {
            'country_risk': 0.25,
            'customer_risk': 0.30,
            'product_risk': 0.20,
            'transaction_risk': 0.25,
        })
        
        overall_score = (
            country_risk * weights['country_risk'] +
            customer_risk * weights['customer_risk'] +
            product_risk * weights['product_risk'] +
            transaction_risk * weights['transaction_risk']
        )
        
        risk_assessment.overall_risk_score = overall_score
        risk_assessment.assessment_method = 'automated'
        
        # Determine risk level
        if overall_score >= 75:
            risk_level = 'critical'
        elif overall_score >= 50:
            risk_level = 'high'
        elif overall_score >= 25:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        risk_assessment.risk_level = risk_level
        risk_assessment.save()
        
        # Update customer risk level
        customer.risk_level = risk_level
        customer.aml_risk_score = overall_score
        
        # Determine KYC type based on risk
        if risk_level in ['high', 'critical'] or customer.customer_type == 'corporate':
            customer.kyc_type = 'ECDD'
        else:
            customer.kyc_type = 'CDD'
        
        customer.save()
        
        # Update workflow
        if hasattr(customer, 'workflow'):
            customer.workflow.risk_assessed = True
            if customer.workflow.current_step == 'initial_review':
                customer.workflow.current_step = 'risk_assessment'
            customer.workflow.save()
        
        # Create high-risk alert
        if risk_level in ['high', 'critical']:
            ComplianceAlert.objects.create(
                customer=customer,
                alert_type='high_risk_country' if country_risk > 50 else 'unusual_activity',
                severity='high' if risk_level == 'high' else 'critical',
                title=f'High risk customer identified: {customer.name}',
                description=f'Customer risk assessment resulted in {risk_level} risk level (score: {overall_score})',
                triggered_by='risk_assessment',
                source_data={
                    'overall_score': float(overall_score),
                    'risk_breakdown': {
                        'country': float(country_risk),
                        'customer': float(customer_risk),
                        'product': float(product_risk),
                        'transaction': float(transaction_risk)
                    }
                }
            )
        
        logger.info(f'Risk assessment completed for customer {customer.id}: {risk_level} ({overall_score})')
        
    except Customer.DoesNotExist:
        logger.error(f'Customer {customer_id} not found for risk assessment')
    except Exception as e:
        logger.error(f'Error during risk assessment for customer {customer_id}: {str(e)}')

def calculate_country_risk(customer):
    """Calculate country-based risk score"""
    # High-risk countries (example list)
    high_risk_countries = [
        'Afghanistan', 'Iran', 'North Korea', 'Syria', 'Yemen',
        # Add more countries based on FATF and sanctions lists
    ]
    
    if customer.customer_type == 'individual':
        if hasattr(customer, 'individual_details'):
            nationality = customer.individual_details.nationality
            if nationality in high_risk_countries:
                return 80.0
            # Add more logic for medium-risk countries
            return 20.0
    else:
        if hasattr(customer, 'corporate_details'):
            country = customer.corporate_details.incorporation_country
            if country in high_risk_countries:
                return 85.0
            return 25.0
    
    return 30.0

def calculate_customer_risk(customer):
    """Calculate customer-specific risk score"""
    risk_score = 0.0
    
    if customer.customer_type == 'corporate':
        risk_score += 30.0  # Corporate entities have higher base risk
        
        if hasattr(customer, 'corporate_details'):
            # High-risk business types
            high_risk_businesses = [
                'money_services', 'cryptocurrency', 'gaming', 'precious_metals',
                'art_dealers', 'cash_intensive', 'shell_company'
            ]
            
            if customer.corporate_details.business_type in high_risk_businesses:
                risk_score += 40.0
            
            # Check for beneficial owners
            if customer.corporate_details.beneficial_owners.count() == 0:
                risk_score += 20.0  # No beneficial owners identified
    
    else:  # Individual
        if hasattr(customer, 'individual_details'):
            # High-risk occupations
            high_risk_occupations = [
                'politician', 'government_official', 'military_officer',
                'casino_owner', 'arms_dealer', 'precious_metals_dealer'
            ]
            
            if customer.individual_details.occupation.lower() in high_risk_occupations:
                risk_score += 50.0
    
    return min(risk_score, 100.0)

def calculate_product_risk(customer):
    """Calculate product/service risk score"""
    # This would be based on the products/services the customer is applying for
    # For now, returning a default score
    return 20.0

def calculate_transaction_risk(customer):
    """Calculate expected transaction risk score"""
    # This would be based on expected transaction patterns
    # For now, returning a default score
    return 25.0

@shared_task
def check_document_expiry():
    """
    Periodic task to check for expiring documents and create alerts
    """
    try:
        # Check for documents expiring in the next 30 days
        expiring_soon = Document.objects.filter(
            expiry_date__lte=timezone.now() + timedelta(days=30),
            expiry_date__gt=timezone.now(),
            verification_status='verified'
        )
        
        for document in expiring_soon:
            # Check if alert already exists
            existing_alert = ComplianceAlert.objects.filter(
                customer=document.customer,
                alert_type='document_expiry',
                status__in=['open', 'investigating']
            ).exists()
            
            if not existing_alert:
                ComplianceAlert.objects.create(
                    customer=document.customer,
                    alert_type='document_expiry',
                    severity='medium',
                    title=f'Document expiring soon: {document.document_name}',
                    description=f'Document {document.document_name} expires on {document.expiry_date}',
                    triggered_by='automated_check',
                    source_data={'document_id': str(document.id)}
                )
        
        logger.info(f'Document expiry check completed. Found {expiring_soon.count()} expiring documents.')
        
    except Exception as e:
        logger.error(f'Error during document expiry check: {str(e)}')

@shared_task
def periodic_customer_review():
    """
    Periodic task to identify customers due for review
    """
    try:
        customers_due_review = Customer.objects.filter(
            next_review_date__lte=timezone.now(),
            status='approved'
        )
        
        for customer in customers_due_review:
            # Create review alert
            ComplianceAlert.objects.create(
                customer=customer,
                alert_type='review_due',
                severity='medium',
                title=f'Periodic review due: {customer.name}',
                description=f'Customer {customer.name} is due for periodic review',
                triggered_by='automated_check',
                source_data={
                    'last_review_date': customer.next_review_date.isoformat() if customer.next_review_date else None,
                    'risk_level': customer.risk_level
                }
            )
            
            # Update next review date based on risk level
            review_frequency = settings.KYC_SETTINGS.get('REVIEW_FREQUENCY_DAYS', {
                'low': 365,
                'medium': 180,
                'high': 90,
                'critical': 30,
            })
            
            days_to_add = review_frequency.get(customer.risk_level, 180)
            customer.next_review_date = timezone.now() + timedelta(days=days_to_add)
            customer.save()
        
        logger.info(f'Periodic review check completed. {customers_due_review.count()} customers due for review.')
        
    except Exception as e:
        logger.error(f'Error during periodic review check: {str(e)}')

@shared_task
def send_kyc_notification(customer_id, notification_type, recipient_email=None):
    """
    Send KYC-related email notifications
    """
    try:
        customer = Customer.objects.get(id=customer_id)
        
        email_templates = {
            'application_received': {
                'subject': 'KYC Application Received',
                'message': f'Dear {customer.name},\n\nWe have received your KYC application and it is currently being processed.\n\nReference: {customer.customer_reference}\n\nThank you.'
            },
            'additional_info_required': {
                'subject': 'Additional Information Required - KYC Application',
                'message': f'Dear {customer.name},\n\nWe need additional information to complete your KYC application.\n\nReference: {customer.customer_reference}\n\nPlease log in to your account to provide the required information.\n\nThank you.'
            },
            'application_approved': {
                'subject': 'KYC Application Approved',
                'message': f'Dear {customer.name},\n\nCongratulations! Your KYC application has been approved.\n\nReference: {customer.customer_reference}\n\nYou can now access all services.\n\nThank you.'
            },
            'application_rejected': {
                'subject': 'KYC Application Status Update',
                'message': f'Dear {customer.name},\n\nWe regret to inform you that your KYC application could not be approved at this time.\n\nReference: {customer.customer_reference}\n\nFor more information, please contact our support team.\n\nThank you.'
            }
        }
        
        template = email_templates.get(notification_type)
        if template:
            recipient = recipient_email or customer.email
            
            send_mail(
                subject=template['subject'],
                message=template['message'],
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            
            logger.info(f'Email notification sent to {recipient} for customer {customer.id}')
        
    except Customer.DoesNotExist:
        logger.error(f'Customer {customer_id} not found for notification')
    except Exception as e:
        logger.error(f'Error sending notification for customer {customer_id}: {str(e)}')