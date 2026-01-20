from django.core.management.base import BaseCommand
from pharmacy.services import DrugService
from django.utils import timezone


class Command(BaseCommand):
    help = 'Check and zero out stock for expired drug items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        current_date = timezone.now().date()
        
        if options['dry_run']:
            self.stdout.write("DRY RUN - No changes will be made")
            self.stdout.write(f"Current date: {current_date}")
            self.stdout.write("")
            
            from pharmacy.models import LpacemakerDrugs, NcapDrugs, OncologyPharmacy
            
            total_expired = 0
            for model, name in [(LpacemakerDrugs, 'Lpacemaker'), 
                               (NcapDrugs, 'NCAP'), 
                               (OncologyPharmacy, 'Oncology')]:
                expired = model.objects.filter(
                    exp_date__isnull=False,
                    exp_date__lt=current_date,
                    stock__gt=0
                )
                count = expired.count()
                total_expired += count
                
                if count > 0:
                    self.stdout.write(f"{name} - {count} expired items:")
                    for drug in expired:
                        self.stdout.write(f"  - {drug.name} (ID: {drug.id}) - stock: {drug.stock} (would be set to 0)")
                else:
                    self.stdout.write(f"{name} - No expired items with stock")
            
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would update {total_expired} items"))
            return
        
        # Run the actual check
        count, items = DrugService.check_expired_items()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired items found.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} expired item(s):'))
        for item in items:
            self.stdout.write(f'  - {item["name"]} ({item["type"]}): stock reduced from {item["old_stock"]} to 0 (expired: {item["exp_date"]})')
