# additional_views.py - Additional API views for KYC operations
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
import json

class BulkAssignView(APIView):
    permission_classes = [IsComplianceOfficer]
    
    def post(self, request):
        customer_ids = request.data.get('customer_ids', [])
        officer_id = request.data.get('officer_id')
        
        try:
            from django.contrib.auth.models import User
            officer = User.objects.get(id=officer_id)
            
            customers = Customer.objects.filter(id__in=customer_ids)
            customers.update(compliance_officer=officer)
            
            return Response({
                'status': 'success',
                'message': f'{customers.count()} customers assigned to {officer.username}'
            })
        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Officer not found'
            }, status=status.HTTP_400_BAD_REQUEST)

class BulkResolveAlertsView(APIView):
    permission_classes = [IsComplianceOfficer]
    
    def post(self, request):
        alert_ids = request.data.get('alert_ids', [])
        resolution_notes = request.data.get('notes', '')
        
        alerts = ComplianceAlert.objects.filter(id__in=alert_ids, status='open')
        alerts.update(
            status='resolved',
            resolved_by=request.user,
            resolved_at=timezone.now(),
            resolution_notes=resolution_notes
        )
        
        return Response({
            'status': 'success',
            'message': f'{alerts.count()} alerts resolved'
        })

class KYCSummaryReportView(APIView):
    permission_classes = [IsKYCOfficer]
    
    def get(self, request):
        # Date range
        start_date = request.query_params.get('start_date', 
            timezone.now() - timedelta(days=30))
        end_date = request.query_params.get('end_date', timezone.now())
        
        customers = Customer.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        report_data = {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_applications': customers.count(),
                'approved': customers.filter(status='approved').count(),
                'rejected': customers.filter(status='rejected').count(),
                'pending': customers.filter(status='pending').count(),
                'ecdd_cases': customers.filter(kyc_type='ECDD').count(),
            },
            'risk_breakdown': customers.values('risk_level').annotate(
                count=Count('id')
            ),
            'processing_times': {
                'average_days': customers.filter(
                    approved_at__isnull=False
                ).aggregate(
                    avg_time=Avg('approved_at') - Avg('created_at')
                ),
            },
            'document_stats': {
                'total_documents': Document.objects.filter(
                    customer__in=customers
                ).count(),
                'verified_documents': Document.objects.filter(
                    customer__in=customers,
                    verification_status='verified'
                ).count(),
            }
        }
        
        return Response(report_data)

class ComplianceMetricsView(APIView):
    permission_classes = [IsComplianceOfficer]
    
    def get(self, request):
        # Get metrics for compliance dashboard
        active_alerts = ComplianceAlert.objects.filter(status='open')
        
        metrics = {
            'alerts': {
                'total_open': active_alerts.count(),
                'critical': active_alerts.filter(severity='critical').count(),
                'high': active_alerts.filter(severity='high').count(),
                'overdue': active_alerts.filter(
                    created_at__lt=timezone.now() - timedelta(days=7)
                ).count(),
            },
            'customers': {
                'high_risk': Customer.objects.filter(risk_level='high').count(),
                'critical_risk': Customer.objects.filter(risk_level='critical').count(),
                'pending_review': Customer.objects.filter(status='pending').count(),
                'reviews_due': Customer.objects.filter(
                    next_review_date__lte=timezone.now()
                ).count(),
            },
            'documents': {
                'pending_verification': Document.objects.filter(
                    verification_status='pending'
                ).count(),
                'expired_documents': Document.objects.filter(
                    expiry_date__lte=timezone.now(),
                    verification_status='verified'
                ).count(),
            },
            'workflow_efficiency': {
                'avg_approval_time': Customer.objects.filter(
                    status='approved',
                    approved_at__isnull=False
                ).aggregate(
                    avg_time=Avg(
                        timezone.now() - models.F('created_at')
                    )
                )
            }
        }
        
        return Response(metrics)

class SanctionsWebhookView(APIView):
    """
    Webhook endpoint for receiving sanctions screening results from external providers
    """
    permission_classes = []  # Allow external systems
    
    def post(self, request):
        try:
            data = request.data
            customer_id = data.get('customer_id')
            screening_result = data.get('screening_result')
            
            customer = Customer.objects.get(id=customer_id)
            
            if screening_result.get('sanctions_hit'):
                # Create compliance alert
                ComplianceAlert.objects.create(
                    customer=customer,
                    alert_type='sanctions_hit',
                    severity='critical',
                    title=f'Sanctions screening hit for {customer.name}',
                    description=f'Potential sanctions match found: {screening_result.get("match_details", "")}',
                    triggered_by='external_screening',
                    source_data=screening_result
                )
                
                # Update customer status
                customer.sanctions_checked = True
                customer.status = 'under_review'
                customer.save()
                
            return Response({'status': 'success'})
            
        except Customer.DoesNotExist:
            return Response({
                'status': 'error', 
                'message': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error', 
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class ExternalRiskAssessmentView(APIView):
    """
    API endpoint for external systems to submit risk assessment data
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            customer_id = request.data.get('customer_id')
            risk_data = request.data.get('risk_assessment')
            
            customer = Customer.objects.get(id=customer_id)
            risk_assessment = customer.risk_assessment
            
            # Update risk assessment with external data
            risk_assessment.country_risk_score = risk_data.get('country_risk', 0)
            risk_assessment.customer_risk_score = risk_data.get('customer_risk', 0)
            risk_assessment.overall_risk_score = risk_data.get('overall_risk', 0)
            risk_assessment.risk_level = risk_data.get('risk_level', 'medium')
            risk_assessment.assessment_method = 'external_api'
            risk_assessment.risk_factors = risk_data.get('risk_factors', {})
            risk_assessment.save()
            
            # Update customer risk level
            customer.risk_level = risk_assessment.risk_level
            customer.aml_risk_score = risk_assessment.overall_risk_score
            customer.save()
            
            # Log audit trail
            AuditTrail.objects.create(
                customer=customer,
                action_type='risk_assess',
                description='Risk assessment updated via external API',
                performed_by=request.user,
                additional_data=risk_data
            )
            
            return Response({
                'status': 'success',
                'risk_level': customer.risk_level,
                'overall_score': float(risk_assessment.overall_risk_score)
            })
            
        except Customer.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)