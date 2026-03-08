from django.core.management.base import BaseCommand
from api.models import BranchDetails, DRS, ManifestDetails


class Command(BaseCommand):
    help = (
        "Sync branch manifest_counter and drs_counter based on existing "
        "DRS and ManifestDetails records. Sets each counter to (max existing + 1) "
        "so the next number issued continues the real series."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be changed without saving.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        branches = BranchDetails.objects.all()

        if not branches.exists():
            self.stdout.write(self.style.WARNING("No branches found."))
            return

        updated = 0

        for branch in branches:
            code = branch.branch_code

            # ── DRS counter ──────────────────────────────────────────────────
            # drsno format: "{branch_code}{counter:04d}"
            # We extract the last 4 chars as the counter portion
            drs_records = DRS.objects.filter(code=code)
            max_drs = 0
            for drs in drs_records:
                drsno = drs.drsno or ""
                # Try to strip the branch_code prefix and parse counter
                if drsno.startswith(code):
                    suffix = drsno[len(code):]
                    try:
                        val = int(suffix)
                        if val > max_drs:
                            max_drs = val
                    except ValueError:
                        pass

            new_drs_counter = str(max_drs + 1).zfill(4)

            # ── Manifest counter ─────────────────────────────────────────────
            # manifestnumber format: "{branch_code}{counter:04d}"
            manifest_records = ManifestDetails.objects.filter(inscaned_branch_code=code)
            max_manifest = 0
            for m in manifest_records:
                mnum = m.manifestnumber or ""
                if mnum.startswith(code):
                    suffix = mnum[len(code):]
                    try:
                        val = int(suffix)
                        if val > max_manifest:
                            max_manifest = val
                    except ValueError:
                        pass

            new_manifest_counter = str(max_manifest + 1).zfill(4)

            # ── Report & save ────────────────────────────────────────────────
            drs_changed = new_drs_counter != branch.drs_counter
            manifest_changed = new_manifest_counter != branch.manifest_counter

            if drs_changed or manifest_changed:
                self.stdout.write(
                    f"Branch [{code}] {branch.branchname}:\n"
                    f"  drs_counter:      {branch.drs_counter!r:>6} → {new_drs_counter!r}\n"
                    f"  manifest_counter: {branch.manifest_counter!r:>6} → {new_manifest_counter!r}"
                )
                if not dry_run:
                    branch.drs_counter = new_drs_counter
                    branch.manifest_counter = new_manifest_counter
                    branch.save()
                    updated += 1
            else:
                self.stdout.write(
                    f"Branch [{code}] {branch.branchname}: already up-to-date "
                    f"(drs={branch.drs_counter}, manifest={branch.manifest_counter})"
                )

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry-run mode — no changes were saved."))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nDone. {updated} branch(es) updated.")
            )
