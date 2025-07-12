#TimezoneConverterService class 
from datetime import datetime, timezone, time
from django.utils import timezone as django_timezone
from django.conf import settings
import pytz

class TimezoneConverterService:

    @staticmethod
    def convert_date_with_timezone(date_string, from_timezone='UTC', to_timezone='Asia/Colombo'):
        """
        Convert a date string to a specific timezone with timezone awareness.
        
        Args:
            date_string (str): Date string in format 'YYYY/MM/DD' or 'YYYY-MM-DD'
            from_timezone (str): Source timezone (default: 'UTC')
            to_timezone (str): Target timezone (default: 'Asia/Colombo')
            
        Returns:
            dict: Dictionary containing converted date, timezone info, and original date
        """
        try:
            # Parse the date string
            if '/' in date_string:
                date_obj = datetime.strptime(date_string, '%Y/%m/%d')
            else:
                date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            
            # Make the datetime timezone-aware
            from_tz = pytz.timezone(from_timezone)
            aware_datetime = from_tz.localize(date_obj)
            
            # Convert to target timezone
            to_tz = pytz.timezone(to_timezone)
            converted_datetime = aware_datetime.astimezone(to_tz)
            
            return {
                'original_date': date_string,
                'converted_date': converted_datetime.strftime('%Y-%m-%d'),
                'converted_datetime': converted_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'timezone': to_timezone,
                'is_timezone_aware': True,
                'utc_offset': converted_datetime.strftime('%z'),
                'formatted_date': converted_datetime.strftime('%B %d, %Y'),
                'iso_format': converted_datetime.isoformat()
            }
        except Exception as e:
            return {
                'error': f'Date conversion failed: {str(e)}',
                'original_date': date_string
            }

    @staticmethod
    def convert_to_django_timezone(date_string, target_timezone=None):
        """
        Convert date to Django's configured timezone with USE_TZ support.
        
        Args:
            date_string (str): Date string in format 'YYYY/MM/DD' or 'YYYY-MM-DD'
            target_timezone (str): Optional target timezone, uses Django's TIME_ZONE if None
            
        Returns:
            dict: Dictionary containing Django timezone-aware datetime
        """
        try:
            # Parse the date string
            if '/' in date_string:
                date_obj = datetime.strptime(date_string, '%Y/%m/%d')
            else:
                date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            
            # Use Django's timezone utilities
            if settings.USE_TZ:
                # Make timezone-aware using Django's timezone
                django_datetime = django_timezone.make_aware(date_obj)
                
                # Convert to target timezone if specified
                if target_timezone:
                    target_tz = pytz.timezone(target_timezone)
                    django_datetime = django_datetime.astimezone(target_tz)
                else:
                    # Use Django's configured timezone
                    django_datetime = django_datetime.astimezone(
                        pytz.timezone(settings.TIME_ZONE)
                    )
            else:
                # If USE_TZ is False, return naive datetime
                django_datetime = date_obj
            
            return {
                'original_date': date_string,
                'django_datetime': django_datetime,
                'formatted_date': django_datetime.strftime('%Y-%m-%d'),
                'formatted_datetime': django_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'timezone': target_timezone or settings.TIME_ZONE,
                'is_timezone_aware': settings.USE_TZ,
                'use_tz': settings.USE_TZ,
                'iso_format': django_datetime.isoformat() if settings.USE_TZ else django_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            }
        except Exception as e:
            return {
                'error': f'Django timezone conversion failed: {str(e)}',
                'original_date': date_string
            }

    @staticmethod
    def get_current_timezone_info():
        """
        Get current timezone configuration information.
        
        Returns:
            dict: Current timezone settings and information
        """
        return {
            'django_timezone': settings.TIME_ZONE,
            'use_tz': settings.USE_TZ,
            'current_datetime': django_timezone.now().isoformat(),
            'current_date': django_timezone.now().strftime('%Y-%m-%d'),
            'timezone_aware': settings.USE_TZ
        }

    @staticmethod
    def validate_date_format(date_string):
        """
        Validate if the date string is in supported format.
        
        Args:
            date_string (str): Date string to validate
            
        Returns:
            dict: Validation result
        """
        supported_formats = ['%Y/%m/%d', '%Y-%m-%d']
        
        for fmt in supported_formats:
            try:
                datetime.strptime(date_string, fmt)
                return {
                    'is_valid': True,
                    'format': fmt,
                    'date_string': date_string
                }
            except ValueError:
                continue
        
        return {
            'is_valid': False,
            'supported_formats': ['YYYY/MM/DD', 'YYYY-MM-DD'],
            'date_string': date_string
        }

    @staticmethod
    def create_date_range_for_query(date_string):
        """
        Create start and end datetime for database queries with proper timezone handling.
        
        Args:
            date_string (str): Date string in format 'YYYY/MM/DD' or 'YYYY-MM-DD'
            
        Returns:
            dict: {
                'start_datetime': timezone-aware datetime (start of day),
                'end_datetime': timezone-aware datetime (end of day),
                'original_date': str,
                'timezone': str
            }
        """
        try:
            # Parse the date string
            if '/' in date_string:
                date_obj = datetime.strptime(date_string, '%Y/%m/%d')
            else:
                date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            
            # Create start and end of day
            start_of_day = datetime.combine(date_obj.date(), time.min)
            end_of_day = datetime.combine(date_obj.date(), time.max)
            
            # Make timezone-aware using Django's timezone utilities
            if settings.USE_TZ:
                start_datetime = django_timezone.make_aware(start_of_day)
                end_datetime = django_timezone.make_aware(end_of_day)
            else:
                start_datetime = start_of_day
                end_datetime = end_of_day
            
            return {
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'original_date': date_string,
                'timezone': settings.TIME_ZONE,
                'use_tz': settings.USE_TZ
            }
        except Exception as e:
            return {
                'error': f'Date range creation failed: {str(e)}',
                'original_date': date_string
            }

    @staticmethod
    def create_date_range_for_period(start_date_str, end_date_str):
        """
        Create start and end datetime for a date period with proper timezone handling.
        
        Args:
            start_date_str (str): Start date in format 'YYYY/MM/DD' or 'YYYY-MM-DD'
            end_date_str (str): End date in format 'YYYY/MM/DD' or 'YYYY-MM-DD'
            
        Returns:
            dict: {
                'start_datetime': timezone-aware datetime (start of start date),
                'end_datetime': timezone-aware datetime (end of end date),
                'start_date': str,
                'end_date': str,
                'timezone': str
            }
        """
        try:
            # Parse the date strings
            if '/' in start_date_str:
                start_date_obj = datetime.strptime(start_date_str, '%Y/%m/%d')
            else:
                start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
                
            if '/' in end_date_str:
                end_date_obj = datetime.strptime(end_date_str, '%Y/%m/%d')
            else:
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # Create start and end of day
            start_datetime = datetime.combine(start_date_obj.date(), time.min)
            end_datetime = datetime.combine(end_date_obj.date(), time.max)
            
            # Make timezone-aware using Django's timezone utilities
            if settings.USE_TZ:
                start_datetime = django_timezone.make_aware(start_datetime)
                end_datetime = django_timezone.make_aware(end_datetime)
            
            return {
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'timezone': settings.TIME_ZONE,
                'use_tz': settings.USE_TZ
            }
        except Exception as e:
            return {
                'error': f'Date period range creation failed: {str(e)}',
                'start_date': start_date_str,
                'end_date': end_date_str
            }
    

