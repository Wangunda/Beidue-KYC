# permissions.py
from rest_framework import permissions

class IsKYCOfficer(permissions.BasePermission):
    """
    Permission for KYC officers who can review and approve/reject customers
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.groups.filter(name='KYC Officers').exists() or 
             request.user.is_superuser)
        )

class IsComplianceOfficer(permissions.BasePermission):
    """
    Permission for compliance officers who can handle alerts and risk assessments
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.groups.filter(name__in=['Compliance Officers', 'KYC Officers']).exists() or 
             request.user.is_superuser)
        )

class IsCustomerOwnerOrKYCOfficer(permissions.BasePermission):
    """
    Permission that allows customers to view their own data or KYC officers to view all
    """
    def has_object_permission(self, request, view, obj):
        # KYC officers can access all customers
        if request.user.groups.filter(name__in=['KYC Officers', 'Compliance Officers']).exists():
            return True
        
        # Customers can only access their own data (if implementing customer portal)
        return False