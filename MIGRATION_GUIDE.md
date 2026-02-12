# Tribute-Centric SQLite Migration Guide

## Overview
This guide explains the new Tribute-Centric Data Model and how to migrate existing JSON data to SQLite.

## What Changed

### Before (JSON-based)
- Flat JSON files for prompts and inventories
- No relational structure
- No transaction support
- Poor query performance
- Tribute IDs extracted from prompt/inventory keys

### After (SQLite-based)
- Centralized SQLite database with relational schema
- Tribute entity as primary anchor
- Atomic transactions for data consistency
- Indexed queries for fast searches
- Explicit tribute ID, name, and Discord user link

## New Tribute Entity

Each tribute now has **three identifiers**:

```
Tribute ID:      D1F              (immutable, used in commands)
Tribute Name:    John Doe         (human-readable, can be updated)
User Mention:    <@451541198889418772>  (Discord user link)
```

### Example: Creating a Tribute

```
/create-tribute
  tribute_id: D1F
  tribute_name: John Doe
  user: @John (Discord user picker)
```

This creates:
- A Tribute with ID=D1F
- Linked to Discord user @John
- Ready for inventory and prompt assignment

## Migration Process

### Step 1: Backup Existing Data
```bash
cp -r config/inventories config/inventories.backup
cp -r config/prompts config/prompts.backup
```

### Step 2: Run Migration (One-time)
```bash
# Preview changes (dry-run):
python migrate_json_to_sqlite.py --dry-run

# Execute migration:
python migrate_json_to_sqlite.py
```

This:
1. Creates SQLite database at `config/thgbot.db`
2. Extracts tribute IDs from JSON files
3. Creates Tribute records (with default names = IDs)
4. Migrates all inventory items
5. Migrates all prompts
6. Generates report with success/error counts

### Step 3: Update Tribute Information
After migration, tributes have default names (= their IDs). Update them:

```
/view-tributes                    # See all tributes
/view-tribute tribute_id: D1F     # View tribute details
/create-tribute
  tribute_id: D1F
  tribute_name: Alice Smith
  user: @alice                      # Link to Discord user
```

Wait - this will create a duplicate! Let me fix the documentation...

Actually, to update an existing tribute's name and user link, currently there's no command. You would need to:
1. Delete the tribute: `/delete-tribute tribute_id: D1F`
2. Recreate with correct info: `/create-tribute tribute_id: D1F tribute_name: Alice Smith user: @alice`

Or add an `/update-tribute` command.

### Step 4: Verify Migration
```
# Check SQLite database was created:
ls -lh config/thgbot.db

# Verify tributes in database:
/view-tributes

# Verify inventories:
/inventory-get tribute_id: D1F    # Should show migrated items

# Verify prompts:
/view-prompt-ids                  # Should show migrated prompts
```

### Step 5: Archive JSON Files
Once confident in migration, archive original JSON files:
```bash
mkdir config/json_backups_2026-02-12
mv config/inventories/inventories.json config/json_backups_2026-02-12/
mv config/prompts/prompt_info.json config/json_backups_2026-02-12/
```

## Data Structure

### New SQLite Schema

**tributes** table
```
id              INTEGER PRIMARY KEY
tribute_id      TEXT UNIQUE         (e.g., "D1F")
tribute_name    TEXT                (e.g., "John Doe")
user_id         INTEGER             (Discord user ID)
user_mention    TEXT                (e.g., "<@12345>")
guild_id        INTEGER             (server ID)
created_at      TIMESTAMP
```

**inventories** table
```
id              INTEGER PRIMARY KEY
tribute_id      TEXT UNIQUE FOREIGN KEY
capacity        INTEGER             (default 10)
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**inventory_items** table
```
id              INTEGER PRIMARY KEY
tribute_id      TEXT FOREIGN KEY
item_number     INTEGER
item_name       TEXT
UNIQUE(tribute_id, item_number)
```

**prompts** table
```
id              INTEGER PRIMARY KEY
tribute_id      TEXT FOREIGN KEY
prompt_id       TEXT
message         TEXT
channel_id      INTEGER
created_at      TIMESTAMP
UNIQUE(tribute_id, prompt_id)
```

(Similar tables for prompt_images and files)

## Fallback Mode (During Transition)

During migration, the bot operates in **dual-read mode**:

- **Read Operations**: Check SQLite first, fall back to JSON if needed
- **Write Operations**: All writes go to SQLite only
- **Benefits**: Minimize downtime, recover from mistakes

Once confident, disable fallback:
```python
bot.storage.disable_fallback()  # SQLite only
```

## Backup & Recovery

### Automated Backups
After migration, keep regular SQLite backups:
```bash
# Daily backup
cp config/thgbot.db config/backups/thgbot_$(date +%Y%m%d).db
```

### Restore from Backup
If needed:
```bash
cp config/backups/thgbot_20260212.db config/thgbot.db
```

## Commands Reference

### Tribute Management

**Create Tribute**
```
/create-tribute tribute_id: D1F tribute_name: John Doe user: @john
```

**View All Tributes**
```
/view-tributes
```

**View Specific Tribute**
```
/view-tribute tribute_id: D1F
```

**Delete Tribute** (cascades to inventory, prompts, files)
```
/delete-tribute tribute_id: D1F
```

### Inventory Management (Unchanged)

```
/inventory-create tribute_id: D1F capacity: 10
/inventory-get tribute_id: D1F
/inventory-add tribute_id: D1F item: Sword
/inventory-remove tribute_id: D1F item_number: 1
/inventory-search item: Sword
/inventory-clear tribute_id: D1F
```

### Prompt Management (Unchanged)

```
/save-prompt prompt_id: EVENT1 prompt: "Prompt text"
/view-prompts
/send-prompt prompt_id: EVENT1
/send-all-prompts
/clear-prompt prompt_id: EVENT1
/clear-all-prompts
```

## Troubleshooting

### Migration Failed
- Check JSON files exist: `ls config/inventories/inventories.json`
- Check permissions: `chmod 644 config/*.json`
- Check disk space: `df -h`
- Review error log in migration output

### Tribute Not Found After Migration
- Verify migration completed successfully
- Run `/view-tributes` to see all
- Check if tribute_id spelling is correct (case-insensitive)
- Try dry-run again: `python migrate_json_to_sqlite.py --dry-run`

### Data Looks Different
- Inventory items are now auto-keyed (1, 2, 3... instead of original numbers)
- Prompt IDs are normalized to uppercase (D1F not d1f)
- This is intentional for consistency

### Performance Issues
- SQLite database should be much faster than JSON
- If slow, check database isn't on slow storage
- Run VACUUM to optimize: `sqlite3 config/thgbot.db "VACUUM;"`

## Future Enhancements

The new data model enables:
- ✅ Fast item searches across all tributes
- ✅ Referential integrity (no orphaned data)
- ✅ Atomic transactions (all-or-nothing operations)
- ✅ Multi-server support (guild_id field)
- ✅ Audit logs (created_at, updated_at timestamps)
- 🔜 Item metadata and attributes
- 🔜 Inventory history/logs
- 🔜 Bulk operations
- 🔜 Complex queries (e.g., "find all tributes with more than 5 items")

## Questions?

For more information:
- View database schema: See `database.py` lines 35-115
- Review migration logic: See `migrate_json_to_sqlite.py`
- Check storage fallback: See `storage.py` lines 50-180
