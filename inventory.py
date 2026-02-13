import discord
import json
import os
import threading
from typing import Dict, Optional, List, Tuple

# File locking mechanism for concurrent access
_inventory_lock = threading.Lock()


class Inventory:
    """Manages Tribute inventories with persistent JSON storage."""

    def __init__(self, data_dir: str):
        """
        Initialize Inventory manager.
        
        Args:
            data_dir: Base directory for storing inventory data
        """
        self.data_dir = data_dir
        self.inv_dir = os.path.join(data_dir, "inventories")
        self.inv_file = os.path.join(self.inv_dir, "inventories.json")
        self.inv_data: Dict[str, Dict] = {}
        self.load()

    def load(self) -> None:
        """Load inventory data from JSON file."""
        with _inventory_lock:
            if not os.path.exists(self.inv_dir):
                os.makedirs(self.inv_dir)
            
            if os.path.exists(self.inv_file):
                try:
                    with open(self.inv_file, "r") as f:
                        self.inv_data = json.load(f)
                except (json.JSONDecodeError, IOError):
                    self.inv_data = {}
            else:
                self.inv_data = {}

    def save(self) -> None:
        """Save inventory data to JSON file with thread safety."""
        with _inventory_lock:
            if not os.path.exists(self.inv_dir):
                os.makedirs(self.inv_dir)
            
            with open(self.inv_file, "w") as f:
                json.dump(self.inv_data, f, indent=2)

    def _get_tribute(self, tribute_id: str) -> Optional[Dict]:
        """Get tribute inventory data or None if not found."""
        return self.inv_data.get(tribute_id.lower())

    def _ensure_tribute(self, tribute_id: str, capacity: int = 10) -> None:
        """Create tribute inventory if it doesn't exist."""
        tribute_id = tribute_id.lower()
        if tribute_id not in self.inv_data:
            self.inv_data[tribute_id] = {
                "capacity": capacity,
                "items": {}
            }

    def _rekey_items(self, items: Dict[str, str]) -> Dict[str, str]:
        """Re-key items dictionary to maintain sequential numbering."""
        rekeyed = {}
        for i, (_, value) in enumerate(items.items(), 1):
            rekeyed[str(i)] = value
        return rekeyed

    def _tribute_exists(self, tribute_id: str) -> bool:
        """Check if tribute exists in inventory system."""
        return tribute_id.lower() in self.inv_data

    def get_inventory(self, tribute_id: str) -> Tuple[bool, Dict]:
        """
        Retrieve inventory for a tribute.
        
        Returns:
            (success: bool, data: dict with 'error' or 'items' and 'capacity')
        """
        if not self._tribute_exists(tribute_id):
            return False, {"error": f"Error: Tribute ID not found in the system. No action taken."}
        
        tribute = self._get_tribute(tribute_id)
        items = tribute.get("items", {})
        capacity = tribute.get("capacity", 10)
        
        return True, {
            "items": items,
            "capacity": capacity,
            "item_count": len(items)
        }

    def set_inventory(self, tribute_id: str, items_dict: Dict[str, str], capacity: int = 10) -> Tuple[bool, Dict]:
        """
        Set (replace) entire inventory for a tribute.
        
        Args:
            tribute_id: Tribute identifier
            items_dict: Dictionary of items (will be re-keyed)
            capacity: Soft capacity limit for this tribute
            
        Returns:
            (success: bool, data: dict with 'error' or updated inventory)
        """
        if not self._tribute_exists(tribute_id):
            return False, {"error": f"Error: Tribute ID not found in the system. No action taken."}
        
        # Re-key items to maintain sequential numbering
        rekeyed_items = self._rekey_items(items_dict)
        
        tribute_id = tribute_id.lower()
        self.inv_data[tribute_id]["items"] = rekeyed_items
        self.inv_data[tribute_id]["capacity"] = capacity
        self.save()
        
        return True, {
            "items": rekeyed_items,
            "capacity": capacity,
            "item_count": len(rekeyed_items)
        }

    def add_to_inventory(self, tribute_id: str, item: str) -> Tuple[bool, Dict]:
        """
        Add an item to tribute's inventory.
        
        Args:
            tribute_id: Tribute identifier
            item: Item name/description
            
        Returns:
            (success: bool, data: dict with 'error' or updated inventory)
        """
        if not self._tribute_exists(tribute_id):
            return False, {"error": f"Error: Tribute ID not found in the system. No action taken."}
        
        tribute = self._get_tribute(tribute_id)
        items = tribute.get("items", {})
        
        # Get next sequential key
        next_key = str(len(items) + 1)
        items[next_key] = item
        
        self.save()
        
        return True, {
            "items": items,
            "capacity": tribute.get("capacity", 10),
            "item_count": len(items)
        }

    def remove_from_inventory(self, tribute_id: str, item: str) -> Tuple[bool, Dict]:
        """
        Remove first instance of item from tribute's inventory.
        
        Args:
            tribute_id: Tribute identifier
            item: Item name to remove (searches by value)
            
        Returns:
            (success: bool, data: dict with 'error' or updated inventory)
        """
        if not self._tribute_exists(tribute_id):
            return False, {"error": f"Error: Tribute ID not found in the system. No action taken."}
        
        tribute = self._get_tribute(tribute_id)
        items = tribute.get("items", {})
        
        # Find and remove first instance
        found_key = None
        for key, value in items.items():
            if value == item:
                found_key = key
                break
        
        if found_key is None:
            return False, {"error": f"Error: '{item}' not found in Tribute's inventory. No changes made."}
        
        del items[found_key]
        
        # Re-key to maintain sequential numbering
        items = self._rekey_items(items)
        tribute_id_lower = tribute_id.lower()
        self.inv_data[tribute_id_lower]["items"] = items
        self.save()
        
        return True, {
            "items": items,
            "capacity": tribute.get("capacity", 10),
            "item_count": len(items)
        }

    def search_inventories(self, item: str) -> Tuple[bool, Dict]:
        """
        Search all inventories for an item.
        
        Args:
            item: Item to search for
            
        Returns:
            (success: bool, data: dict with 'tributes' list or empty)
        """
        tributes_with_item = []
        
        for tribute_id, tribute_data in self.inv_data.items():
            items = tribute_data.get("items", {})
            if item in items.values():
                tributes_with_item.append(tribute_id)
        
        return True, {"tributes": tributes_with_item}

    def clear_inventory(self, tribute_id: str) -> Tuple[bool, Dict]:
        """
        Clear entire inventory for a tribute.
        
        Args:
            tribute_id: Tribute identifier
            
        Returns:
            (success: bool, data: dict with 'error' or confirmation)
        """
        if not self._tribute_exists(tribute_id):
            return False, {"error": f"Error: Tribute ID not found in the system. No action taken."}
        
        tribute_id_lower = tribute_id.lower()
        self.inv_data[tribute_id_lower]["items"] = {}
        self.save()
        
        return True, {"message": f"Inventory for {tribute_id} has been successfully cleared."}

    def create_tribute_inventory(self, tribute_id: str, capacity: int = 10) -> None:
        """Create a new tribute inventory."""
        self._ensure_tribute(tribute_id, capacity)
        self.save()
