from django.core.management.base import BaseCommand, CommandError
from api.services.finance_summary_service import DailyFinanceSummaryService
from api.models import Branch
from datetime import datetime
import json

class Command(BaseCommand):
    help = 'Generate daily finance summary for all branches using current date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date for the summary in YYYY-MM-DD format (defaults to today)',
            default=None
        )

    def handle(self, *args, **options):
        date_str = options['date']

        try:
            # Parse date if provided
            date = None
            if date_str:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    self.stdout.write(
                        self.style.SUCCESS(f'Generating finance summary for all branches on date {date}')
                    )
                except ValueError:
                    raise CommandError("Invalid date format. Use YYYY-MM-DD.")
            else:
                date = datetime.now().date()
                self.stdout.write(
                    self.style.SUCCESS(f'Generating finance summary for all branches on current date {date}')
                )

            # Get all branches
            branches = Branch.objects.all()
            
            if not branches:
                self.stdout.write(
                    self.style.WARNING('No branches found in the database')
                )
                return

            self.stdout.write(f'Found {branches.count()} branches to process')

            # Process each branch
            for branch in branches:
                try:
                    self.stdout.write(
                        self.style.SUCCESS(f'\nProcessing branch: {branch.branch_name} (ID: {branch.id})')
                    )
                    
                    # Get the finance summary for this branch
                    summary = DailyFinanceSummaryService.get_summary(branch_id=branch.id, date=date)
                    
                    # Pretty print the summary
                    self.stdout.write(f'Finance Summary for {branch.branch_name}:')
                    self.stdout.write(json.dumps(summary, indent=2, default=str))
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing branch {branch.branch_name} (ID: {branch.id}): {str(e)}')
                    )
                    continue

            self.stdout.write(
                self.style.SUCCESS(f'\nCompleted processing all {branches.count()} branches')
            )

        except Exception as e:
            raise CommandError(f'Error generating finance summaries: {str(e)}')