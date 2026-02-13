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
        return self.inv_data.get(tribute_id.upper())

    def _ensure_tribute(
        self, tribute_id: str, capacity: int = 10, equipped_capacity: int = 5
    ) -> None:
        """Create tribute inventory if it doesn't exist."""
        tribute_id = tribute_id.upper()
        if tribute_id not in self.inv_data:
            self.inv_data[tribute_id] = {
                "capacity": capacity,
                "items": {},
                "equipped_capacity": equipped_capacity,
                "equipped": {},
            }

    def _rekey_items(self, items: Dict[str, str]) -> Dict[str, str]:
        """Re-key items dictionary to maintain sequential numbering."""
        rekeyed = {}
        for i, (_, value) in enumerate(items.items(), 1):
            rekeyed[str(i)] = value
        return rekeyed

    def _tribute_exists(self, tribute_id: str) -> bool:
        """Check if tribute exists in inventory system."""
        return tribute_id.upper() in self.inv_data

    def get_inventory(self, tribute_id: str) -> Tuple[bool, Dict]:
        """
        Retrieve inventory for a tribute.

        Returns:
            (success: bool, data: dict with 'error' or 'items', 'equipped' and 'capacity')
        """
        if not self._tribute_exists(tribute_id):
            return False, {
                "error": f"Error: Tribute ID not found in the system. No action taken."
            }

        tribute = self._get_tribute(tribute_id)
        items = tribute.get("items", {})
        equipped = tribute.get("equipped", {})
        capacity = tribute.get("capacity", 10)
        equipped_capacity = tribute.get("equipped_capacity", 5)

        return True, {
            "items": items,
            "equipped": equipped,
            "capacity": capacity,
            "equipped_capacity": equipped_capacity,
            "item_count": len(items),
            "equipped_count": len(equipped),
        }

    def set_inventory(
        self,
        tribute_id: str,
        items_dict: Dict[str, str],
        capacity: int = 10,
        equipped_capacity: int = 5,
    ) -> Tuple[bool, Dict]:
        """
        Set (replace) entire inventory for a tribute.

        Args:
            tribute_id: Tribute identifier
            items_dict: Dictionary of items (will be re-keyed)
            capacity: Soft capacity limit for this tribute
            equipped_capacity: Capacity for equipped section

        Returns:
            (success: bool, data: dict with 'error' or updated inventory)
        """
        if not self._tribute_exists(tribute_id):
            return False, {
                "error": f"Error: Tribute ID not found in the system. No action taken."
            }

        # Re-key items to maintain sequential numbering
        rekeyed_items = self._rekey_items(items_dict)

        tribute_id = tribute_id.upper()
        self.inv_data[tribute_id]["items"] = rekeyed_items
        self.inv_data[tribute_id]["capacity"] = capacity
        self.inv_data[tribute_id]["equipped_capacity"] = equipped_capacity
        self.save()

        return True, {
            "items": rekeyed_items,
            "capacity": capacity,
            "equipped_capacity": equipped_capacity,
            "item_count": len(rekeyed_items),
            "equipped_count": len(self.inv_data[tribute_id].get("equipped", {})),
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
            return False, {
                "error": f"Error: Tribute ID not found in the system. No action taken."
            }

        tribute = self._get_tribute(tribute_id)
        items = tribute.get("items", {})

        # Get next sequential key
        next_key = str(len(items) + 1)
        items[next_key] = item

        self.save()

        return True, {
            "items": items,
            "capacity": tribute.get("capacity", 10),
            "equipped": tribute.get("equipped", {}),
            "equipped_capacity": tribute.get("equipped_capacity", 5),
            "item_count": len(items),
            "equipped_count": len(tribute.get("equipped", {})),
        }

    def add_to_equipped(self, tribute_id: str, item: str) -> Tuple[bool, Dict]:
        """
        Add an item directly to tribute's equipped section.

        Args:
            tribute_id: Tribute identifier
            item: Item name/description

        Returns:
            (success: bool, data: dict with 'error' or updated inventory)
        """
        if not self._tribute_exists(tribute_id):
            return False, {
                "error": f"Error: Tribute ID not found in the system. No action taken."
            }

        tribute = self._get_tribute(tribute_id)
        equipped = tribute.get("equipped", {})
        equipped_capacity = tribute.get("equipped_capacity", 5)

        if len(equipped) >= equipped_capacity:
            return False, {
                "error": f"Error: Equipped section is full ({len(equipped)}/{equipped_capacity})."
            }

        # Get next sequential key
        next_key = str(len(equipped) + 1)
        equipped[next_key] = item

        tribute_id_upper = tribute_id.upper()
        self.inv_data[tribute_id_upper]["equipped"] = equipped
        self.save()

        return True, {
            "items": tribute.get("items", {}),
            "capacity": tribute.get("capacity", 10),
            "equipped": equipped,
            "equipped_capacity": equipped_capacity,
            "item_count": len(tribute.get("items", {})),
            "equipped_count": len(equipped),
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
            return False, {
                "error": f"Error: Tribute ID not found in the system. No action taken."
            }

        tribute = self._get_tribute(tribute_id)
        items = tribute.get("items", {})

        # Find and remove first instance
        found_key = None
        for key, value in items.items():
            if value == item:
                found_key = key
                break

        if found_key is None:
            return False, {
                "error": f"Error: '{item}' not found in Tribute's inventory. No changes made."
            }

        del items[found_key]

        # Re-key to maintain sequential numbering
        items = self._rekey_items(items)
        tribute_id_upper = tribute_id.upper()
        self.inv_data[tribute_id_upper]["items"] = items
        self.save()

        return True, {
            "items": items,
            "capacity": tribute.get("capacity", 10),
            "item_count": len(items),
        }

    def search_inventories(self, item: str) -> Tuple[bool, Dict]:
        """
        Search all inventories for items containing the search phrase.

        Args:
            item: Search phrase (case-insensitive, partial match)

        Returns:
            (success: bool, data: dict with 'results' list of (tribute_id, item_name) tuples or empty)
        """
        results = []
        search_lower = item.lower()

        for tribute_id, tribute_data in self.inv_data.items():
            # Search in inventory items
            items = tribute_data.get("items", {})
            for item_name in items.values():
                if search_lower in item_name.lower():
                    results.append((tribute_id, item_name))
            
            # Search in equipped items
            equipped = tribute_data.get("equipped", {})
            for item_name in equipped.values():
                if search_lower in item_name.lower():
                    results.append((tribute_id, item_name))

        return True, {"results": results}

    def clear_inventory(self, tribute_id: str) -> Tuple[bool, Dict]:
        """
        Clear entire inventory and equipped sections for a tribute.

        Args:
            tribute_id: Tribute identifier

        Returns:
            (success: bool, data: dict with 'error' or confirmation)
        """
        if not self._tribute_exists(tribute_id):
            return False, {
                "error": f"Error: Tribute ID not found in the system. No action taken."
            }

        tribute_id_upper = tribute_id.upper()
        self.inv_data[tribute_id_upper]["items"] = {}
        self.inv_data[tribute_id_upper]["equipped"] = {}
        self.save()

        return True, {
            "message": f"Inventory and equipped items for {tribute_id} have been successfully cleared."
        }

    def create_tribute_inventory(
        self, tribute_id: str, capacity: int = 10, equipped_capacity: int = 5
    ) -> None:
        """Create a new tribute inventory, or update capacities if it exists."""
        tribute_id = tribute_id.upper()
        if tribute_id in self.inv_data:
            # Update capacities if inventory already exists
            self.inv_data[tribute_id]["capacity"] = capacity
            self.inv_data[tribute_id]["equipped_capacity"] = equipped_capacity
        else:
            # Create new inventory
            self._ensure_tribute(tribute_id, capacity, equipped_capacity)
        self.save()

    def delete_tribute_inventory(self, tribute_id: str) -> Tuple[bool, Dict]:
        """
        Completely delete a tribute's inventory entry.

        Args:
            tribute_id: Tribute identifier

        Returns:
            (success: bool, data: dict with result)
        """
        tribute_id_upper = tribute_id.upper()
        if tribute_id_upper in self.inv_data:
            del self.inv_data[tribute_id_upper]
            self.save()
            return True, {"message": f"Inventory for {tribute_id} has been deleted."}
        return False, {"error": f"Error: Tribute ID not found in the system."}

    def equip_item(self, tribute_id: str, item_key: str) -> Tuple[bool, Dict]:
        """
        Move item from inventory to equipped section.

        Args:
            tribute_id: Tribute identifier
            item_key: Item key/number to equip

        Returns:
            (success: bool, data: dict with 'error' or updated inventory)
        """
        if not self._tribute_exists(tribute_id):
            return False, {
                "error": f"Error: Tribute ID not found in the system. No action taken."
            }

        tribute = self._get_tribute(tribute_id)
        items = tribute.get("items", {})
        equipped = tribute.get("equipped", {})
        equipped_capacity = tribute.get("equipped_capacity", 5)

        if item_key not in items:
            return False, {"error": f"Error: Item #{item_key} not found in inventory."}

        if len(equipped) >= equipped_capacity:
            return False, {
                "error": f"Error: Equipped section is full ({len(equipped)}/{equipped_capacity})."
            }

        # Move item
        item_name = items[item_key]
        del items[item_key]

        # Re-key remaining inventory items
        items = self._rekey_items(items)

        # Add to equipped
        next_equipped_key = str(len(equipped) + 1)
        equipped[next_equipped_key] = item_name

        tribute_id_upper = tribute_id.upper()
        self.inv_data[tribute_id_upper]["items"] = items
        self.inv_data[tribute_id_upper]["equipped"] = equipped
        self.save()

        return True, {
            "items": items,
            "equipped": equipped,
            "capacity": tribute.get("capacity", 10),
            "equipped_capacity": equipped_capacity,
            "item_count": len(items),
            "equipped_count": len(equipped),
            "message": f"'{item_name}' has been equipped.",
        }

    def unequip_item(self, tribute_id: str, item_key: str) -> Tuple[bool, Dict]:
        """
        Move item from equipped section back to inventory.

        Args:
            tribute_id: Tribute identifier
            item_key: Item key/number to unequip

        Returns:
            (success: bool, data: dict with 'error' or updated inventory)
        """
        if not self._tribute_exists(tribute_id):
            return False, {
                "error": f"Error: Tribute ID not found in the system. No action taken."
            }

        tribute = self._get_tribute(tribute_id)
        items = tribute.get("items", {})
        equipped = tribute.get("equipped", {})
        capacity = tribute.get("capacity", 10)

        if item_key not in equipped:
            return False, {"error": f"Error: Equipped item #{item_key} not found."}

        if len(items) >= capacity:
            return False, {
                "error": f"Error: Inventory is full ({len(items)}/{capacity})."
            }

        # Move item
        item_name = equipped[item_key]
        del equipped[item_key]

        # Re-key remaining equipped items
        equipped = self._rekey_items(equipped)

        # Add to inventory
        next_inv_key = str(len(items) + 1)
        items[next_inv_key] = item_name

        tribute_id_upper = tribute_id.upper()
        self.inv_data[tribute_id_upper]["items"] = items
        self.inv_data[tribute_id_upper]["equipped"] = equipped
        self.save()

        return True, {
            "items": items,
            "equipped": equipped,
            "capacity": capacity,
            "equipped_capacity": tribute.get("equipped_capacity", 5),
            "item_count": len(items),
            "equipped_count": len(equipped),
            "message": f"'{item_name}' has been unequipped.",
        }
