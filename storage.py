"""
Storage migration layer providing dual-read capability during transition.
Reads from SQLite first, falls back to JSON if needed.
All writes go directly to SQLite.
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
from database import SQLDatabase

logger = logging.getLogger(__name__)

try:
    datadir = os.environ["SNAP_DATA"]
except KeyError:
    logger.warning("SNAP_DATA not set, using current directory")
    datadir = "."

# JSON file paths
INVENTORIES_JSON = os.path.join(datadir, "inventories", "inventories.json")
PROMPTS_JSON = os.path.join(datadir, "prompts", "prompt_info.json")


class StorageManager:
    """Manages dual-read storage (SQLite primary, JSON fallback) during migration."""
    
    def __init__(self, db: SQLDatabase):
        self.db = db
        self.fallback_mode = True  # Enable JSON fallback reads
    
    def load_json_file(self, filepath: str) -> Dict[str, Any]:
        """Load JSON file, return empty dict if not found."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load {filepath}: {e}")
        return {}
    
    def save_json_file(self, filepath: str, data: Dict[str, Any]):
        """Save data to JSON file."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")
    
    # INVENTORY OPERATIONS
    
    def get_inventory(self, tribute_id: str) -> Optional[Dict[str, Any]]:
        """Get inventory from JSON storage."""
        try:
            inventories = self.load_json_file(INVENTORIES_JSON)
            if tribute_id.lower() in inventories:
                return inventories[tribute_id.lower()]
            return None
        except Exception as e:
            logger.error(f"Failed to get inventory for {tribute_id}: {e}")
            return None
    
    def create_inventory(self, tribute_id: str, capacity: int = 10) -> bool:
        """Create inventory in JSON storage (or update capacity if exists)."""
        try:
            inventories = self.load_json_file(INVENTORIES_JSON)
            tribute_id_lower = tribute_id.lower()
            
            if tribute_id_lower in inventories:
                # Update capacity if inventory already exists
                inventories[tribute_id_lower]["capacity"] = capacity
                logger.info(f"Updated inventory capacity for {tribute_id} to {capacity}")
            else:
                inventories[tribute_id_lower] = {"capacity": capacity, "items": {}}
                logger.info(f"Created inventory for {tribute_id} with capacity {capacity}")
            
            self.save_json_file(INVENTORIES_JSON, inventories)
            return True
        except Exception as e:
            logger.error(f"Failed to create inventory for {tribute_id}: {e}")
            return False
    
    def add_inventory_item(self, tribute_id: str, item_name: str) -> bool:
        """Add item to inventory in JSON storage."""
        try:
            inventories = self.load_json_file(INVENTORIES_JSON)
            if tribute_id.lower() not in inventories:
                logger.warning(f"Inventory not found for {tribute_id}")
                return False
            
            items = inventories[tribute_id.lower()].get("items", {})
            next_num = max([int(k) for k in items.keys()] or [0]) + 1
            items[str(next_num)] = item_name
            inventories[tribute_id.lower()]["items"] = items
            
            self.save_json_file(INVENTORIES_JSON, inventories)
            return True
        except Exception as e:
            logger.error(f"Failed to add item to {tribute_id}: {e}")
            return False
    
    def remove_inventory_item(self, tribute_id: str, item_number: int) -> bool:
        """Remove item from inventory in JSON storage."""
        try:
            inventories = self.load_json_file(INVENTORIES_JSON)
            if tribute_id.lower() not in inventories:
                return False
            
            items = inventories[tribute_id.lower()].get("items", {})
            if str(item_number) not in items:
                return False
            
            del items[str(item_number)]
            
            # Rekey remaining items
            rekeyed = {}
            for idx, (_, item_name) in enumerate(sorted(items.items()), 1):
                rekeyed[str(idx)] = item_name
            
            inventories[tribute_id.lower()]["items"] = rekeyed
            self.save_json_file(INVENTORIES_JSON, inventories)
            return True
        except Exception as e:
            logger.error(f"Failed to remove item from {tribute_id}: {e}")
            return False
    
    def clear_inventory(self, tribute_id: str) -> bool:
        """Clear all items from inventory in JSON storage."""
        try:
            inventories = self.load_json_file(INVENTORIES_JSON)
            if tribute_id.lower() not in inventories:
                return False
            
            inventories[tribute_id.lower()]["items"] = {}
            self.save_json_file(INVENTORIES_JSON, inventories)
            return True
        except Exception as e:
            logger.error(f"Failed to clear inventory for {tribute_id}: {e}")
            return False
    
    def search_inventory_items(self, item_name: str) -> List[Dict[str, Any]]:
        """Search for tributes with a specific item in JSON storage."""
        try:
            results = []
            inventories = self.load_json_file(INVENTORIES_JSON)
            for tribute_id, inv_data in inventories.items():
                items = inv_data.get("items", {})
                for item_num, item in items.items():
                    if item_name.lower() in item.lower():
                        results.append({
                            "tribute_id": tribute_id,
                            "item_number": int(item_num),
                            "item_name": item
                        })
            return results
        except Exception as e:
            logger.error(f"Failed to search for '{item_name}': {e}")
            return []

    
    # PROMPT OPERATIONS
    
    def get_prompt(self, tribute_id: str) -> Optional[Dict[str, Any]]:
        """Get prompt from SQLite, fallback to JSON."""
        # Try SQLite first
        prompt = self.db.get_prompt(tribute_id)
        if prompt:
            return {
                "message": prompt['message'],
                "channel": prompt['channel_id'],
                "image": None  # Handle separately if needed
            }
        
        # Fallback to JSON - match tribute_id as key
        if self.fallback_mode:
            prompts = self.load_json_file(PROMPTS_JSON)
            if tribute_id.upper() in prompts:
                logger.info(f"Prompt fallback: {tribute_id} from JSON")
                return prompts[tribute_id.upper()]
        
        return None
    
    def get_all_prompts(self, guild_id: Optional[int] = None) -> Dict[str, Any]:
        """Get all prompts from SQLite, fallback to JSON for missing ones."""
        result = {}
        
        # Get from SQLite
        prompts = self.db.get_all_prompts(guild_id)
        for prompt in prompts:
            result[prompt['tribute_id']] = {
                "message": prompt['message'],
                "channel": prompt['channel_id']
            }
        
        # Fallback to JSON for any missing
        if self.fallback_mode:
            json_prompts = self.load_json_file(PROMPTS_JSON)
            for prompt_id, prompt_data in json_prompts.items():
                if prompt_id not in result:
                    logger.info(f"Prompt fallback: {prompt_id} from JSON")
                    result[prompt_id] = prompt_data
        
        return result
    
    def create_prompt(
        self,
        tribute_id: str,
        message: str,
        channel_id: int
    ) -> bool:
        """Create prompt in SQLite (1:1 with tribute)."""
        try:
            self.db.create_prompt(tribute_id, message, channel_id)
            return True
        except Exception as e:
            logger.error(f"Failed to create prompt for {tribute_id}: {e}")
            return False
    
    def update_prompt(
        self,
        tribute_id: str,
        **kwargs
    ) -> bool:
        """Update prompt in SQLite."""
        try:
            self.db.update_prompt(tribute_id, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to update prompt for {tribute_id}: {e}")
            return False
    
    def delete_prompt(self, tribute_id: str) -> bool:
        """Delete prompt from SQLite."""
        try:
            return self.db.delete_prompt(tribute_id)
        except Exception as e:
            logger.error(f"Failed to delete prompt for {tribute_id}: {e}")
            return False
    
    def delete_all_prompts(self) -> bool:
        """Delete all prompts in SQLite."""
        try:
            self.db.delete_all_prompts()
            return True
        except Exception as e:
            logger.error(f"Failed to delete prompts: {e}")
            return False
    
    # MIGRATION ANALYSIS
    
    def analyze_json_data(self) -> Dict[str, Any]:
        """Analyze existing JSON data to prepare for migration."""
        inventories = self.load_json_file(INVENTORIES_JSON)
        prompts = self.load_json_file(PROMPTS_JSON)
        
        # Extract tribute IDs from both sources
        tribute_ids = set()
        tribute_ids.update(tid.upper() for tid in inventories.keys())
        tribute_ids.update(pid.upper() for pid in prompts.keys())
        
        analysis = {
            "total_tributes": len(tribute_ids),
            "tribute_ids": sorted(list(tribute_ids)),
            "total_inventories": len(inventories),
            "total_prompts": len(prompts),
            "inventory_items_total": sum(
                len(data.get("items", {})) for data in inventories.values()
            ),
            "needs_migration": len(tribute_ids) > 0
        }
        
        return analysis
    
    def disable_fallback(self):
        """Disable JSON fallback - use SQLite only."""
        self.fallback_mode = False
        logger.info("JSON fallback disabled - SQLite mode only")
    
    def enable_fallback(self):
        """Enable JSON fallback for reading."""
        self.fallback_mode = True
        logger.info("JSON fallback enabled")
