#TimezoneConverterService class 
from datetime import datetime, time as datetime_time  # ✅ Fixed import
from django.utils import timezone


class TimezoneConverterService:

    @staticmethod
    def format_date_with_timezone(start_date, end_date):
        """
        Convert date strings to timezone-aware datetime objects.
        
        Args:
            start_date (str): Start date string in format 'YYYY-MM-DD'
            end_date (str): End date string in format 'YYYY-MM-DD'
            
        Returns:
            tuple: (start_datetime, end_datetime) or (None, None) if error
        """
        try:
            if start_date and end_date:
                # Parse date strings to date objects
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                start_datetime = timezone.make_aware(
                    datetime.combine(start_date_obj, datetime_time.min)
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(end_date_obj, datetime_time.max)
                )
 
            elif start_date and not end_date:
                # Use start_date for both start and end
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                
                start_datetime = timezone.make_aware(
                    datetime.combine(start_date_obj, datetime_time.min)
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(start_date_obj, datetime_time.max)
                )
                
            elif not start_date and not end_date:
                # Use today's date
                today = timezone.localdate()
                start_datetime = timezone.make_aware(
                    datetime.combine(today, datetime_time.min)
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(today, datetime_time.max)
                )
            else:
                # No valid dates provided
                return None, None

            return start_datetime, end_datetime
            
        except Exception as e:
            print(f'Date conversion failed: {str(e)}')
            return None, None

