# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from . import views

router = DefaultRouter()
router.register(r'customers', views.CustomerViewSet, basename='customer')
router.register(r'documents', views.DocumentViewSet, basename='document')
router.register(r'alerts', views.ComplianceAlertViewSet, basename='alert')
router.register(r'audit-trail', views.AuditTrailViewSet, basename='audit-trail')

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('api/v1/auth/token/', obtain_auth_token, name='api_token_auth'),
    path('api/v1/auth/', include('rest_framework.urls')),
]

# Additional API endpoints for specific KYC functions
kyc_patterns = [
    # Customer specific endpoints
    path('api/v1/customers/<uuid:customer_id>/documents/', 
         views.DocumentViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='customer-documents'),
    
    path('api/v1/customers/<uuid:customer_id>/alerts/', 
         views.ComplianceAlertViewSet.as_view({'get': 'list'}), 
         name='customer-alerts'),
    
    path('api/v1/customers/<uuid:customer_id>/audit-trail/', 
         views.AuditTrailViewSet.as_view({'get': 'list'}), 
         name='customer-audit-trail'),
    
    # Bulk operations
    path('api/v1/customers/bulk-assign/', 
         views.BulkAssignView.as_view(), 
         name='bulk-assign-customers'),
    
    path('api/v1/alerts/bulk-resolve/', 
         views.BulkResolveAlertsView.as_view(), 
         name='bulk-resolve-alerts'),
    
    # Reporting endpoints
    path('api/v1/reports/kyc-summary/', 
         views.KYCSummaryReportView.as_view(), 
         name='kyc-summary-report'),
    
    path('api/v1/reports/compliance-metrics/', 
         views.ComplianceMetricsView.as_view(), 
         name='compliance-metrics'),
    
    # Integration endpoints
    path('api/v1/webhooks/sanctions-screening/', 
         views.SanctionsWebhookView.as_view(), 
         name='sanctions-webhook'),
    
    path('api/v1/external/risk-assessment/', 
         views.ExternalRiskAssessmentView.as_view(), 
         name='external-risk-assessment'),
]

urlpatterns.extend(kyc_patterns)