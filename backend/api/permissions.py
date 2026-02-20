from rest_framework import permissions
from .models import UserDetails

class IsAdminOrSuperUser(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Check for Superuser
        if request.user.is_superuser:
            return True
            
        # Check for Admin type in UserDetails
        try:
            user_details = UserDetails.objects.get(user=request.user)
            return user_details.type == 'ADMIN'
        except UserDetails.DoesNotExist:
            return False
