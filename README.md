# THG Discord Bot - Hunger Games Roleplay Bot

A comprehensive Discord bot for managing Hunger Games roleplay events, including prompt management and tribute inventory tracking.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Command Reference](#command-reference)
  - [Admin Commands](#admin-commands)
  - [Prompt Commands](#prompt-commands)
  - [Inventory Commands](#inventory-commands)
- [Data Management](#data-management)
- [File Storage](#file-storage)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## Overview

THGBot is a specialized Discord bot designed for Hunger Games roleplay communities. It provides Gamemakers (administrators) with tools to:

1. **Manage Prompts** - Create, edit, view, and send roleplay prompts to tributes
2. **Track Inventory** - Manage items associated with individual tributes
3. **Organize Events** - Coordinate prompt delivery and recipient management

The bot uses Discord's slash commands (application commands) for a modern, accessible interface and stores all data persistently in JSON format.

---

## Features

### Prompt Management
- Create and store unique prompts with IDs
- Edit prompts using interactive modal dialogs
- View all available prompts
- Send prompts to specific channels or all tributes
- Attach files (images, documents) to prompts
- Clear individual or all prompts
- Automatic logging of bot actions

### Inventory Management
- Create and manage tribute inventories
- Add/remove items with automatic re-keying
- Search for items across all tributes
- View complete inventory lists
- Soft capacity warnings
- Persistent data storage

### Admin Features
- Configure log channels for audit trails
- Organize prompts into categories
- Role-based access control (Gamemaker role required)
- Automatic data persistence
- Error handling and user feedback

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- Discord.py 2.5.2+
- Discord bot token with required intents enabled
- Bot must be invited to your Discord server with permissions

### Step 1: Clone/Install

```bash
git clone <repository-url>
cd THGBot
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Environment Setup

Set the following environment variables:

```bash
export SNAP_DATA=/path/to/bot/data  # Base data directory
export SNAP_REVISION=current
export TOKEN=your_discord_bot_token
```

**Note:** If not using snap, set `SNAP_DATA` to any writable directory where the bot should store data.

### Step 3: Start the Bot

```bash
python thgbot.py
```

The bot will:
1. Connect to Discord
2. Create necessary directories in `SNAP_DATA`
3. Load all stored prompts and inventories
4. Sync slash commands with your server
5. Display "Logged in as [Bot Name]"

---

## Configuration

### Initial Setup (First Time)

When the bot joins a new server, it creates default configuration:

```json
{
  "guild_id": {
    "log_channel_id": null,
    "category_id": null
  }
}
```

Use the admin commands below to configure your server.

### Admin Commands

#### `/set-log-channel`
Configure where bot actions are logged.

**Parameters:**
- `channel_id` (optional): Channel ID number
- `channel_name` (optional): Channel name (e.g., "bot-logs")

**Usage:**
```
/set-log-channel channel_id: 1234567890
```
or
```
/set-log-channel channel_name: bot-logs
```

**What Gets Logged:**
- Prompts sent to tributes
- Files added to prompts
- Prompt creation/deletion

**Result:** ✓ Confirmation message with setup details

---

#### `/set-category`
Configure the Discord category where prompt channels are created.

**Parameters:**
- `category_id` (optional): Category ID
- `category_name` (optional): Category name

**Usage:**
```
/set-category category_name: Prompts
```

**Purpose:** Keeps all tribute channels organized in one category when prompts are sent.

**Result:** ✓ Confirmation message with category details

---

## Command Reference

### Admin Commands

All admin commands require appropriate Discord permissions.

---

### Prompt Commands

Prompts are the core feature of THGBot. Each prompt is identified by a unique ID and can contain text, files, and metadata.

#### `/save-prompt`
Create or update a prompt using an interactive modal dialog.

**Description:** Opens a pop-up form where you can enter:
- **Prompt ID**: Unique identifier (e.g., "bloodbath_1", "final_scenario")
- **Content**: The prompt text to send to tributes

**Usage:**
```
/save-prompt
```

**Result:** Modal dialog appears. Fill in fields and submit. The bot confirms with an ephemeral message.

**Example Prompt IDs:**
- `bloodbath_1` - First bloodbath event
- `arena_update` - Arena condition update
- `final_four` - Final four tributes scenario
- `custom_event` - Any custom roleplay event

---

#### `/view-prompt-ids`
List all stored prompt IDs.

**Usage:**
```
/view-prompt-ids
```

**Result:** Numbered list of all available prompts. Useful for:
- Checking what prompts exist
- Verifying prompt names before sending
- Audit trail of stored content

---

#### `/view-prompt`
View the complete content of a specific prompt.

**Parameters:**
- `prompt_id` (required): The prompt ID to view

**Usage:**
```
/view-prompt prompt_id: bloodbath_1
```

**Result:** Ephemeral embed showing:
- Prompt ID
- Full prompt text
- Associated files (if any)
- Last modified date

---

#### `/add-to-prompt`
Add additional content to an existing prompt using a modal dialog.

**Description:** Opens a form to append text to an existing prompt without losing current content.

**Usage:**
```
/add-to-prompt prompt_id: bloodbath_1
```

**Result:** Modal appears with current prompt content. Add more text and submit. Content is appended.

---

#### `/send-prompt`
Send a prompt to a specific channel or user.

**Parameters:**
- `prompt_id` (required): The prompt to send
- `destination` (optional): Channel/user to send to

**Usage:**
```
/send-prompt prompt_id: bloodbath_1
```

**Result:** Sends the prompt to the specified channel with all associated files. Logs the action.

**Behavior:**
- Splits long messages (>2000 chars) automatically
- Sends attached files alongside text
- Logs to configured log channel
- Returns confirmation with delivery status

---

#### `/send-all-prompts`
Broadcast all stored prompts to designated channels.

**Usage:**
```
/send-all-prompts
```

**Behavior:**
- Sends every stored prompt sequentially
- Creates separate channels per tribute if configured
- Logs each send action
- Handles concurrent sends efficiently

**Result:** Confirmation showing how many prompts were sent.

---

#### `/clear-prompt`
Delete a specific prompt from storage.

**Parameters:**
- `prompt_id` (required): Prompt to delete

**Usage:**
```
/clear-prompt prompt_id: bloodbath_1
```

**Result:** ✓ Confirmation that prompt was deleted. Cannot be undone.

**Warning:** This permanently removes the prompt. Use with caution.

---

#### `/clear-all-prompts`
Delete all stored prompts at once.

**Usage:**
```
/clear-all-prompts
```

**Result:** ⚠️ Confirmation dialog appears. Confirm deletion to proceed.

**Warning:** This permanently removes ALL prompts. Use with extreme caution.

---

#### `/add-file`
Attach a file (image, document, etc.) to a prompt.

**Parameters:**
- `prompt_id` (required): Prompt to attach file to
- `file` (required): File to upload (image, PDF, etc.)

**Usage:**
```
/add-file prompt_id: arena_map
<attach an image>
```

**Supported Files:**
- Images: PNG, JPG, GIF, WebP
- Documents: PDF, TXT
- Other files: Any format Discord allows

**Result:** ✓ Confirmation showing filename and attachment details.

**Details:**
- Files are stored alongside prompts
- Automatically sent when prompt is shared
- Multiple files per prompt supported
- Logged when sent to channels

---

### Inventory Commands

Inventory commands let Gamemakers track what items each tribute possesses. All inventory commands require the **Gamemaker** Discord role.

#### `/inventory-create`
Create a new inventory for a tribute.

**Parameters:**
- `tribute_id` (required): Unique identifier for the tribute
- `capacity` (optional): Soft item limit (default: 10)

**Usage:**
```
/inventory-create tribute_id: Katniss capacity: 15
```

**Result:** ✓ Green confirmation embed showing:
- Tribute ID
- Starting capacity
- Empty item list

**Notes:**
- Capacity is a soft limit (doesn't prevent adding items)
- Shows warning when exceeded
- Each tribute can have their own capacity

---

#### `/inventory-get`
View a tribute's current inventory.

**Parameters:**
- `tribute_id` (required): Tribute to view

**Usage:**
```
/inventory-get tribute_id: Katniss
```

**Result:** Blue embed showing:
```
Title: Inventory: Katniss
Items:
  1. Bread from Peeta
  2. Water bottle
  3. Rope
Item Count: 3/15
```

**Display:**
- Numbered list (1, 2, 3...)
- Current count vs. capacity
- ⚠️ Warning if capacity exceeded
- Empty message if no items

---

#### `/inventory-add`
Add an item to a tribute's inventory.

**Parameters:**
- `tribute_id` (required): Tribute to add to
- `item` (required): Item name/description

**Usage:**
```
/inventory-add tribute_id: Katniss item: Emergency backpack
```

**Result:** Blue embed showing updated inventory with the new item added.

**Behavior:**
- Items are numbered sequentially
- Next available number assigned automatically
- Appends to end of inventory
- Can add unlimited items (soft capacity only)

---

#### `/inventory-remove`
Remove an item from a tribute's inventory.

**Parameters:**
- `tribute_id` (required): Tribute to remove from
- `item` (required): Exact item name to remove (case-sensitive)

**Usage:**
```
/inventory-remove tribute_id: Katniss item: Rope
```

**Result:** Blue embed showing updated inventory with item removed and items re-numbered.

**Important:**
- Only removes first occurrence if duplicates exist
- Remaining items are automatically re-keyed (1, 2, 3...)
- Use exact item name (case-sensitive)
- Error if item not found

**Example:**
```
Before removal:
1. Bread from Peeta
2. Water bottle
3. Rope

Remove "Rope"

After removal:
1. Bread from Peeta      (was #1)
2. Water bottle          (was #2)
```

---

#### `/inventory-search`
Search all tributes for a specific item.

**Parameters:**
- `item` (required): Item to search for

**Usage:**
```
/inventory-search item: sword
```

**Result:** Blue embed listing all tributes with the item:
```
Title: Search Results: 'sword'
Tributes with this item:
  • Cato
  • Thresh
  • Clove
```

**Use Cases:**
- Verify item distribution
- Find who has a specific weapon
- Track supply locations
- Audit inventory integrity

---

#### `/inventory-clear`
Delete an entire tribute's inventory.

**Parameters:**
- `tribute_id` (required): Tribute to clear

**Usage:**
```
/inventory-clear tribute_id: Katniss
```

**Result:** ✓ Green confirmation:
```
Title: Inventory Cleared
Description: Inventory for Katniss has been successfully cleared.
```

**Warning:** This removes all items for that tribute. Cannot be undone without re-adding items manually.

---

## Data Management

### Data Structure

The bot stores all data in JSON format for easy management and backup.

#### Prompt Storage
```
{datadir}/prompts/prompt_info.json
```

**Format:**
```json
{
  "prompt_id_1": {
    "content": "The prompt text here...",
    "image": "filename.png",
    "timestamp": "2024-01-15 10:30:00"
  },
  "prompt_id_2": {
    "content": "Another prompt...",
    "timestamp": "2024-01-15 11:00:00"
  }
}
```

#### Inventory Storage
```
{datadir}/inventories/inventories.json
```

**Format:**
```json
{
  "tribute_1": {
    "capacity": 10,
    "items": {
      "1": "sword",
      "2": "shield",
      "3": "water"
    }
  },
  "tribute_2": {
    "capacity": 15,
    "items": {
      "1": "bow",
      "2": "arrow"
    }
  }
}
```

#### Configuration Storage
```
{datadir}/config/config.json
```

**Format:**
```json
{
  "guild_id_1": {
    "log_channel_id": 1234567890,
    "category_id": 0987654321
  }
}
```

### Backup & Recovery

#### Manual Backup

```bash
# Backup all data
cp -r $SNAP_DATA/prompts backup/prompts
cp -r $SNAP_DATA/inventories backup/inventories
cp -r $SNAP_DATA/config backup/config
```

#### Manual Restore

```bash
# Restore from backup
cp backup/prompts/* $SNAP_DATA/prompts/
cp backup/inventories/* $SNAP_DATA/inventories/
cp backup/config/* $SNAP_DATA/config/
```

The bot will automatically reload data on restart.

---

## File Storage

### Directory Structure

```
{SNAP_DATA}/
├── prompts/
│   ├── prompt_info.json          # All prompt definitions
│   └── prompt_images/            # Attached files
│       ├── bloodbath_1.png
│       ├── arena_map.jpg
│       └── ...
├── inventories/
│   └── inventories.json          # All tribute inventories
├── config/
│   └── config.json               # Guild configuration
└── prompt/                        # Guild-specific folders
    └── {guild_id}/
        └── {tribute_channels}
```

### File Size Considerations

- **prompt_info.json**: Grows ~100 bytes per prompt
- **inventories.json**: Grows ~200 bytes per item
- **Attached files**: Unlimited (Discord file size limits apply)

For 100 prompts + 50 tributes with 10 items each:
- Data footprint: ~200 KB (excluding images)
- Images can be 1-10 MB each

### Permissions

The bot requires write access to `SNAP_DATA`. Ensure:

```bash
chmod 755 $SNAP_DATA
chmod 644 $SNAP_DATA/*/config.json
```

---

## Troubleshooting

### Bot Won't Start

**Error: "SNAP_DATA must be set"**
- Solution: Set the environment variable
  ```bash
  export SNAP_DATA=/path/to/data
  export TOKEN=your_token
  export SNAP_REVISION=current
  ```

**Error: "TOKEN must be set"**
- Solution: Set your Discord bot token
  ```bash
  export TOKEN=your_discord_bot_token
  ```

**Error: "discord.py not installed"**
- Solution: Install dependencies
  ```bash
  pip install -r requirements.txt
  ```

### Bot Connects But Commands Don't Appear

**Commands Not Showing in Discord:**
1. Ensure bot has "applications.commands" scope
2. The bot must have permission to create slash commands
3. Commands sync on bot startup - check console for "Logged in as"
4. Try right-clicking → "Apps" to refresh command list

### Permission Errors

**Error: "You do not have permission"**
- Check that you have the required Discord role:
  - Inventory commands need: **Gamemaker** role
  - Admin commands need: Server admin or moderator status

**To add a role:**
```
1. Server Settings → Roles
2. Create "Gamemaker" role if it doesn't exist
3. Assign to users who should manage inventories
4. Restart bot to apply
```

### Data Not Saving

**Prompts/Inventories Lost After Restart:**
1. Check that `SNAP_DATA` directory exists and is writable
2. Verify file permissions: `ls -la $SNAP_DATA/`
3. Look for error messages in bot console
4. Ensure sufficient disk space

### Files Not Uploading

**Error When Adding File to Prompt:**
- Check file size (Discord limit: 25 MB for most servers)
- Verify file format is supported
- Ensure bot has message attachment permissions
- Try again - might be temporary rate limit

### Inventory Items Not Re-keying

**Items Don't Renumber After Removal:**
- This is automatic and shouldn't require action
- Check bot console for errors
- Verify inventories.json is not corrupted
- Try restarting the bot

### Slow Performance with Many Prompts

**Bot Takes Long Time to Start:**
- Normal if you have 100+ prompts
- First sync takes longer - subsequent starts are faster
- Try splitting prompts into multiple bot instances
- Consider database migration (future feature)

---

## Development

### Project Structure

```
THGBot/
├── thgbot.py                 # Main bot and prompt commands
├── inventory.py              # Inventory system core
├── inventory_commands.py      # Inventory Discord commands
├── promptview.py             # Prompt UI components
├── promptmodal.py            # Prompt input modals
├── editpromptview.py         # Edit view components
├── addtopromptmodal.py       # Add-to-prompt modal
├── addfile.py                # File attachment logic
├── confirmationview.py       # Confirmation dialogs
├── tributechannelselector.py # Channel selection UI
├── promptsender.py           # Prompt delivery logic
├── utils.py                  # Helper functions
├── requirements.txt          # Python dependencies
├── InventorySystem.md        # Inventory feature spec
└── README.md                 # This file
```

### Key Components

#### `inventory.py` - Core Inventory Class
- Manages all inventory operations
- Handles JSON persistence with thread safety
- Implements all 6 core functions

#### `inventory_commands.py` - Discord Integration
- Slash commands for end users
- Role-based access control
- Ephemeral embed formatting

#### `thgbot.py` - Main Bot
- Discord bot initialization
- Prompt management commands
- Configuration and logging
- Event handlers

### Adding New Features

1. **Create Feature File**: Add `newfeature.py` for core logic
2. **Create Commands File**: Add `newfeature_commands.py` for Discord integration
3. **Integrate in thgbot.py**: Import and load the cog
4. **Test Thoroughly**: Use concurrency tests for thread safety
5. **Update README**: Document the new feature

### Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run inventory tests
python -c "from inventory import Inventory; import tempfile; ..."

# Test all imports
python -c "from inventory import Inventory; from inventory_commands import InventoryCog; print('✓ All imports OK')"
```

### Contributing

When contributing:
1. Follow existing code style
2. Add docstrings to functions
3. Test new features with concurrent access
4. Update documentation
5. Verify no breaking changes

---

## Support & Resources

### Common Workflows

#### Scenario: Run a Multi-Part Event

1. **Create Prompts:**
   ```
   /save-prompt    # Create "event_part_1"
   /save-prompt    # Create "event_part_2"
   ```

2. **Assign Starting Gear:**
   ```
   /inventory-create tribute_id: Katniss
   /inventory-add tribute_id: Katniss item: Backpack
   /inventory-add tribute_id: Katniss item: Water Bottle
   ```

3. **Send Event:**
   ```
   /send-prompt prompt_id: event_part_1
   ```

4. **Update Inventories During Event:**
   ```
   /inventory-remove tribute_id: Katniss item: Water Bottle
   /inventory-add tribute_id: Katniss item: Found Supplies
   ```

#### Scenario: Search for Contraband

1. Search for items:
   ```
   /inventory-search item: knife
   /inventory-search item: poison
   ```

2. See which tributes have dangerous items

3. Adjust via removal/addition as needed

#### Scenario: Archive Old Event

1. Backup data before clearing:
   ```bash
   cp -r $SNAP_DATA backup-event-1
   ```

2. Clear old prompts:
   ```
   /clear-all-prompts
   ```

3. Data is safely backed up for history

---

## FAQ

**Q: Can I edit a prompt after saving?**
A: Yes! Use `/add-to-prompt` to append content, or `/save-prompt` with the same ID to replace.

**Q: Can multiple Gamemakers use the bot simultaneously?**
A: Yes! The bot uses thread-safe file locking to prevent data corruption.

**Q: How many tributes/items can the bot handle?**
A: Thousands! The bot is designed to scale. Future versions may migrate to SQLite for even better performance.

**Q: Can I recover deleted prompts?**
A: Not automatically. Always backup before mass-deleting. Use manual JSON file backups for recovery.

**Q: Are inventories sent with prompts?**
A: Not yet. This is a future enhancement. Currently inventories are managed separately.

**Q: Can I run multiple bot instances?**
A: Yes, with separate `SNAP_DATA` directories. Coordinating across instances requires external state management.

---

## License & Credits

THGBot was built for the Hunger Games Roleplay community. 

- **Framework**: discord.py 2.5.2+
- **Language**: Python 3.10+
- **Storage**: JSON-based persistence

---

## Version History

- **v1.0** (Current) - Full prompt management + inventory system
  - 10 prompt commands
  - 6 inventory commands
  - Thread-safe file persistence
  - Role-based access control

---

**Last Updated:** February 12, 2026

For issues or questions, reach out to the server administration team.
