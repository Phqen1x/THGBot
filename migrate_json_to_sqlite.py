"""
Migration script: Converts existing JSON data to SQLite database.
Creates tributes from JSON keys and migrates all data with referential integrity.
Run BEFORE deploying the new system.
"""

import os
import json
import sys
import logging
from typing import Dict, List, Tuple
from database import SQLDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    datadir = os.environ["SNAP_DATA"]
except KeyError:
    logger.warning("SNAP_DATA not set, using current directory")
    datadir = "."

INVENTORIES_JSON = os.path.join(datadir, "inventories", "inventories.json")
PROMPTS_JSON = os.path.join(datadir, "prompts", "prompt_info.json")


class MigrationReport:
    """Track migration statistics and errors."""
    
    def __init__(self):
        self.tributes_created = 0
        self.inventories_migrated = 0
        self.inventory_items_migrated = 0
        self.prompts_migrated = 0
        self.errors = []
        self.warnings = []
    
    def add_error(self, msg: str):
        self.errors.append(msg)
        logger.error(f"ERROR: {msg}")
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)
        logger.warning(f"WARNING: {msg}")
    
    def print_summary(self):
        print("\n" + "=" * 70)
        print("MIGRATION REPORT")
        print("=" * 70)
        print(f"\nSuccessful Operations:")
        print(f"  Tributes created:        {self.tributes_created}")
        print(f"  Inventories migrated:    {self.inventories_migrated}")
        print(f"  Inventory items:         {self.inventory_items_migrated}")
        print(f"  Prompts migrated:        {self.prompts_migrated}")
        
        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  ⚠️  {w}")
        
        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for e in self.errors:
                print(f"  ❌ {e}")
        else:
            print(f"\n✅ Migration completed successfully with no errors")
        
        print("=" * 70 + "\n")


def load_json(filepath: str) -> Dict:
    """Load JSON file, return empty dict if not found."""
    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}")
        return {}
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {filepath}: {e}")
        return {}


def extract_tributes(inventories: Dict, prompts: Dict) -> set:
    """Extract unique tribute IDs from JSON data."""
    tribute_ids = set()
    
    # From inventories
    for inv_id in inventories.keys():
        tribute_ids.add(inv_id.upper())
    
    # From prompts
    for prompt_id in prompts.keys():
        tribute_ids.add(prompt_id.upper())
    
    return tribute_ids


def migrate(db: SQLDatabase, dry_run: bool = False) -> MigrationReport:
    """Execute migration from JSON to SQLite."""
    
    report = MigrationReport()
    
    logger.info("=" * 70)
    logger.info("STARTING MIGRATION FROM JSON TO SQLITE")
    logger.info("=" * 70)
    
    # Load JSON files
    logger.info("Loading JSON files...")
    inventories_data = load_json(INVENTORIES_JSON)
    prompts_data = load_json(PROMPTS_JSON)
    
    logger.info(f"  Inventories.json: {len(inventories_data)} entries")
    logger.info(f"  Prompts.json: {len(prompts_data)} entries")
    
    # Extract tribute IDs
    tribute_ids = extract_tributes(inventories_data, prompts_data)
    
    if not tribute_ids:
        logger.warning("No tributes found in JSON files - nothing to migrate")
        return report
    
    logger.info(f"Found {len(tribute_ids)} unique tributes to migrate")
    
    # Create tributes
    logger.info("\n--- Creating Tributes ---")
    for tribute_id in sorted(tribute_ids):
        try:
            if not dry_run:
                # Create tribute with default values (name = ID, user_id = 0)
                # These should be updated manually after migration
                db.create_tribute(
                    tribute_id=tribute_id,
                    tribute_name=tribute_id,  # Default name = ID
                    user_id=0,  # Placeholder
                    user_mention="<@unknown>",  # Placeholder
                    guild_id=None
                )
            report.tributes_created += 1
            logger.info(f"  ✓ Created tribute: {tribute_id}")
        except Exception as e:
            report.add_error(f"Failed to create tribute {tribute_id}: {e}")
    
    # Migrate inventories
    logger.info("\n--- Migrating Inventories ---")
    for tribute_id_lower, inv_data in inventories_data.items():
        tribute_id = tribute_id_lower.upper()
        
        try:
            capacity = inv_data.get("capacity", 10)
            if not dry_run:
                # Create inventory
                db.create_inventory(tribute_id, capacity)
            
            report.inventories_migrated += 1
            logger.info(f"  ✓ Migrated inventory for {tribute_id} (capacity: {capacity})")
            
            # Migrate items
            items = inv_data.get("items", {})
            for item_number, item_name in items.items():
                try:
                    if not dry_run:
                        db.add_inventory_item(tribute_id, item_name)
                    report.inventory_items_migrated += 1
                except Exception as e:
                    report.add_error(
                        f"Failed to add item to {tribute_id}: {item_name} - {e}"
                    )
        
        except Exception as e:
            report.add_error(f"Failed to migrate inventory for {tribute_id}: {e}")
    
    # Migrate prompts (now 1:1 with tribute, no separate prompt_id)
    logger.info("\n--- Migrating Prompts ---")
    for prompt_id, prompt_data in prompts_data.items():
        try:
            prompt_id_upper = prompt_id.upper()
            message = prompt_data.get("message", "")
            channel_id = prompt_data.get("channel", 0)
            
            # Extract tribute ID from prompt ID (e.g., "D1F" from "D1F" or find in tributes)
            tribute_id = None
            for tid in tribute_ids:
                if prompt_id_upper.startswith(tid[:3]):
                    tribute_id = tid
                    break
            
            if not tribute_id:
                # Try exact match
                if prompt_id_upper in tribute_ids:
                    tribute_id = prompt_id_upper
            
            if not tribute_id:
                report.add_warning(
                    f"Could not map prompt {prompt_id} to a tribute"
                )
                continue
            
            if not dry_run:
                # Create prompt (now 1:1 with tribute, no prompt_id parameter)
                db.create_prompt(tribute_id, message, channel_id)
            
            report.prompts_migrated += 1
            logger.info(f"  ✓ Migrated prompt for: {tribute_id}")
        
        except Exception as e:
            report.add_error(f"Failed to migrate prompt {prompt_id}: {e}")
    
    return report


def main():
    """Main migration entry point."""
    
    # Parse arguments
    dry_run = "--dry-run" in sys.argv or "--preview" in sys.argv
    force = "--force" in sys.argv
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    
    # Check if JSON files exist
    if not os.path.exists(INVENTORIES_JSON) and not os.path.exists(PROMPTS_JSON):
        logger.warning("No JSON files found to migrate. Exiting.")
        return
    
    # Initialize database
    try:
        db = SQLDatabase()
        logger.info(f"Database initialized at: {db.db_path}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)
    
    # Run migration
    try:
        report = migrate(db, dry_run=dry_run)
        report.print_summary()
        
        if dry_run:
            print("To execute this migration for real, run:")
            print("  python migrate_json_to_sqlite.py --force")
        elif report.errors:
            print("\n⚠️  Migration completed with errors. Please review above.")
        else:
            print("✅ Migration successful!")
            print("\nNext steps:")
            print("  1. Update tribute names and Discord user links via /create-tribute")
            print("  2. Verify all data is correct in the new database")
            print("  3. Keep JSON backups until you're confident in the migration")
    
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
