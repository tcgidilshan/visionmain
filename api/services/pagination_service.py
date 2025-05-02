# visionmain/api/pagination.py
from rest_framework.pagination import PageNumberPagination

class PaginationService(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'  # Optional: allow client to override
    max_page_size = 100  # Optional: limit max page size