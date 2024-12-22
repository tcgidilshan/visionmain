from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import LensPower
from ..serializers import LensPowerSerializer
from django.db import transaction

# List, Create, and Bulk Update Lens Powers
class LensPowerListCreateView(APIView):
    def get(self, request, *args, **kwargs):
        """
        List all lens powers.
        """
        queryset = LensPower.objects.all()
        serializer = LensPowerSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Create one or more lens powers.
        """
        if isinstance(request.data, list):  # Handle multiple objects
            serializer = LensPowerSerializer(data=request.data, many=True)
        else:  # Handle a single object
            serializer = LensPowerSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def put(self, request, *args, **kwargs):
        """
        Bulk update lens powers. Each object must contain its `id`.
        """
        if not isinstance(request.data, list):
            return Response(
                {"error": "Expected a list of objects for bulk update."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Collect all updates
        response_data = []
        for item in request.data:
            if 'id' not in item:
                return Response(
                    {"error": "Each object must contain an 'id' for update."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                instance = LensPower.objects.get(id=item['id'])
            except LensPower.DoesNotExist:
                return Response(
                    {"error": f"LensPower with id {item['id']} does not exist."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = LensPowerSerializer(instance, data=item, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            response_data.append(serializer.data)

        return Response(response_data, status=status.HTTP_200_OK)


# Retrieve, Update (Single), and Delete Lens Powers
class LensPowerRetrieveUpdateDeleteView(APIView):
    def get(self, request, pk, *args, **kwargs):
        """
        Retrieve a single lens power.
        """
        try:
            instance = LensPower.objects.get(pk=pk)
            serializer = LensPowerSerializer(instance)
            return Response(serializer.data)
        except LensPower.DoesNotExist:
            return Response(
                {"error": "LensPower not found."}, status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, pk, *args, **kwargs):
        """
        Update a single lens power.
        """
        try:
            instance = LensPower.objects.get(pk=pk)
            serializer = LensPowerSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except LensPower.DoesNotExist:
            return Response(
                {"error": "LensPower not found."}, status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, pk, *args, **kwargs):
        """
        Delete a single lens power.
        """
        try:
            instance = LensPower.objects.get(pk=pk)
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except LensPower.DoesNotExist:
            return Response(
                {"error": "LensPower not found."}, status=status.HTTP_404_NOT_FOUND
            )
