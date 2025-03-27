# services/branch_protections_service.py

from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from api.models import Branch  # Import your Branch model

class BranchProtectionsService:
    
    @staticmethod
    def validate_branch_id(request):
        """
        Validates the provided branch_id and ensures the branch exists.
        """
        branch_id = request.query_params.get('branch_id')
        if not branch_id:
            raise ValidationError("current branch  can not identifyed  ")
        
        # Check if the branch exists in the database
        branch = get_object_or_404(Branch, id=branch_id)
        return branch
