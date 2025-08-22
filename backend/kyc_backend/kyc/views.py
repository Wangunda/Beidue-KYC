# views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from .models import Customer, Document, ComplianceAlert, AuditTrail
from .serializers import (
    CustomerListSerializer, CustomerDetailSerializer, 
    CustomerCreateSerializer, DocumentSerializer,
    ComplianceAlertSerializer, AuditTrailSerializer
)
from .permissions import IsKYCOfficer, IsComplianceOfficer
import hashlib

class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Customer.objects.select_related(
            'individual_details', 'corporate_details', 'reviewed_by',
            'compliance_officer', 'risk_assessment', 'workflow'
        ).prefetch_related(
            'documents', 'compliance_alerts', 'audit_trail'
        )
        
        # Filter parameters
        status_filter = self.request.query_params.get('status', None)
        risk_level = self.request.query_params.get('risk_level', None)
        kyc_type = self.request.query_params.get('kyc_type', None)
        customer_type = self.request.query_params.get('customer_type', None)
        search = self.request.query_params.get('search', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        if kyc_type:
            queryset = queryset.filter(kyc_type=kyc_type)
        if customer_type:
            queryset = queryset.filter(customer_type=customer_type)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(customer_reference__icontains=search)
            )
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        elif self.action == 'create':
            return CustomerCreateSerializer
        return CustomerDetailSerializer
    
    def perform_create(self, serializer):
        customer = serializer.save()
        self.log_audit_trail(customer, 'create', 'Customer profile created')
    
    def perform_update(self, serializer):
        old_instance = self.get_object()
        customer = serializer.save()
        self.log_audit_trail(customer, 'update', 'Customer profile updated')
    
    def log_audit_trail(self, customer, action_type, description):
        AuditTrail.objects.create(
            customer=customer,
            action_type=action_type,
            description=description,
            performed_by=self.request.user,
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    @action(detail=True, methods=['post'], permission_classes=[IsKYCOfficer])
    def approve(self, request, pk=None):
        customer = self.get_object()
        customer.status = 'approved'
        customer.reviewed_by = request.user
        customer.approved_at = timezone.now()
        customer.review_notes = request.data.get('notes', '')
        customer.save()
        
        # Update workflow
        if hasattr(customer, 'workflow'):
            customer.workflow.current_step = 'completed'
            customer.workflow.completed_at = timezone.now()
            customer.workflow.compliance_approved = True
            customer.workflow.save()
        
        self.log_audit_trail(customer, 'approve', 'Customer approved for onboarding')
        
        return Response({
            'status': 'success',
            'message': 'Customer approved successfully'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsKYCOfficer])
    def reject(self, request, pk=None):
        customer = self.get_object()
        customer.status = 'rejected'
        customer.reviewed_by = request.user
        customer.rejected_at = timezone.now()
        customer.review_notes = request.data.get('notes', '')
        customer.save()
        
        # Update workflow
        if hasattr(customer, 'workflow'):
            customer.workflow.current_step = 'rejected'
            customer.workflow.completed_at = timezone.now()
            customer.workflow.save()
        
        self.log_audit_trail(customer, 'reject', f"Customer rejected: {customer.review_notes}")
        
        return Response({
            'status': 'success',
            'message': 'Customer rejected successfully'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsKYCOfficer])
    def request_additional_info(self, request, pk=None):
        customer = self.get_object()
        customer.status = 'requires_additional_info'
        customer.reviewed_by = request.user
        customer.review_notes = request.data.get('notes', '')
        customer.save()
        
        self.log_audit_trail(customer, 'status_change', 'Additional information requested')
        
        return Response({
            'status': 'success',
            'message': 'Additional information requested'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsComplianceOfficer])
    def assign_compliance_officer(self, request, pk=None):
        customer = self.get_object()
        officer_id = request.data.get('officer_id')
        
        try:
            from django.contrib.auth.models import User
            officer = User.objects.get(id=officer_id)
            customer.compliance_officer = officer
            customer.save()
            
            self.log_audit_trail(customer, 'update', f'Assigned to compliance officer: {officer.username}')
            
            return Response({
                'status': 'success',
                'message': f'Customer assigned to {officer.first_name} {officer.last_name}'
            })
        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Officer not found'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        queryset = self.get_queryset()
        
        stats = {
            'total_customers': queryset.count(),
            'pending_review': queryset.filter(status='pending').count(),
            'under_review': queryset.filter(status='under_review').count(),
            'approved': queryset.filter(status='approved').count(),
            'rejected': queryset.filter(status='rejected').count(),
            'requires_additional_info': queryset.filter(status='requires_additional_info').count(),
            'high_risk': queryset.filter(risk_level='high').count(),
            'critical_risk': queryset.filter(risk_level='critical').count(),
            'ecdd_customers': queryset.filter(kyc_type='ECDD').count(),
            'active_alerts': ComplianceAlert.objects.filter(status='open').count(),
            'recent_activity': queryset.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count()
        }
        
        # Risk distribution
        risk_distribution = queryset.values('risk_level').annotate(
            count=Count('id')
        ).order_by('risk_level')
        
        # Monthly trends (last 12 months)
        monthly_stats = []
        for i in range(12):
            start_date = timezone.now().replace(day=1) - timedelta(days=30*i)
            end_date = start_date + timedelta(days=32)
            end_date = end_date.replace(day=1) - timedelta(days=1)
            
            monthly_count = queryset.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).count()
            
            monthly_stats.append({
                'month': start_date.strftime('%Y-%m'),
                'count': monthly_count
            })
        
        return Response({
            'stats': stats,
            'risk_distribution': list(risk_distribution),
            'monthly_trends': monthly_stats[::-1]  # Reverse to get chronological order
        })


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            return Document.objects.filter(customer_id=customer_id)
        return Document.objects.all()
    
    def perform_create(self, serializer):
        # Calculate file hash
        file_obj = self.request.FILES['file_path']
        file_hash = hashlib.sha256()
        for chunk in file_obj.chunks():
            file_hash.update(chunk)
        
        document = serializer.save(
            file_size=file_obj.size,
            file_hash=file_hash.hexdigest()
        )
        
        # Log audit trail
        AuditTrail.objects.create(
            customer=document.customer,
            action_type='document_upload',
            description=f'Document uploaded: {document.document_name}',
            performed_by=self.request.user,
            ip_address=self.get_client_ip(),
            additional_data={'document_type': document.document_type}
        )
        
        # Update workflow if all required documents are uploaded
        self.check_document_completeness(document.customer)
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def check_document_completeness(self, customer):
        required_docs = ['passport', 'utility_bill'] if customer.customer_type == 'individual' else [
            'incorporation_certificate', 'memorandum_articles', 'financial_statements'
        ]
        
        uploaded_docs = customer.documents.values_list('document_type', flat=True)
        all_required_uploaded = all(doc in uploaded_docs for doc in required_docs)
        
        if all_required_uploaded and hasattr(customer, 'workflow'):
            customer.workflow.documents_complete = True
            customer.workflow.current_step = 'initial_review'
            customer.workflow.save()
    
    @action(detail=True, methods=['post'], permission_classes=[IsKYCOfficer])
    def verify(self, request, pk=None):
        document = self.get_object()
        document.verification_status = 'verified'
        document.verified_by = request.user
        document.verified_at = timezone.now()
        document.verification_notes = request.data.get('notes', '')
        document.save()
        
        AuditTrail.objects.create(
            customer=document.customer,
            action_type='document_verify',
            description=f'Document verified: {document.document_name}',
            performed_by=request.user,
            ip_address=self.get_client_ip()
        )
        
        return Response({'status': 'success', 'message': 'Document verified'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsKYCOfficer])
    def reject_document(self, request, pk=None):
        document = self.get_object()
        document.verification_status = 'rejected'
        document.verified_by = request.user
        document.verified_at = timezone.now()
        document.verification_notes = request.data.get('notes', '')
        document.save()
        
        AuditTrail.objects.create(
            customer=document.customer,
            action_type='document_verify',
            description=f'Document rejected: {document.document_name}',
            performed_by=request.user,
            ip_address=self.get_client_ip()
        )
        
        return Response({'status': 'success', 'message': 'Document rejected'})


class ComplianceAlertViewSet(viewsets.ModelViewSet):
    serializer_class = ComplianceAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = ComplianceAlert.objects.select_related(
            'customer', 'assigned_to', 'resolved_by'
        )
        
        # Filter parameters
        status_filter = self.request.query_params.get('status', None)
        severity = self.request.query_params.get('severity', None)
        alert_type = self.request.query_params.get('alert_type', None)
        customer_id = self.request.query_params.get('customer_id', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if severity:
            queryset = queryset.filter(severity=severity)
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsComplianceOfficer])
    def assign(self, request, pk=None):
        alert = self.get_object()
        officer_id = request.data.get('officer_id')
        
        try:
            from django.contrib.auth.models import User
            officer = User.objects.get(id=officer_id)
            alert.assigned_to = officer
            alert.status = 'investigating'
            alert.save()
            
            return Response({
                'status': 'success',
                'message': f'Alert assigned to {officer.first_name} {officer.last_name}'
            })
        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Officer not found'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsComplianceOfficer])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.status = 'resolved'
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.resolution_notes = request.data.get('notes', '')
        alert.save()
        
        return Response({
            'status': 'success',
            'message': 'Alert resolved successfully'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsComplianceOfficer])
    def mark_false_positive(self, request, pk=None):
        alert = self.get_object()
        alert.status = 'false_positive'
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.resolution_notes = request.data.get('notes', 'Marked as false positive')
        alert.save()
        
        return Response({
            'status': 'success',
            'message': 'Alert marked as false positive'
        })


class AuditTrailViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditTrailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = AuditTrail.objects.select_related('customer', 'performed_by')
        
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        action_type = self.request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset