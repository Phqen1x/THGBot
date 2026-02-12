# Software Specification: THG Discord Bot Inventory Management System

# 1\. Introduction

## 1.1 Purpose

This document specifies the requirements and design for the Inventory Management System within the THGBot, a Hunger Games Roleplay Discord bot. The system is designed to allow Gamemakers to manage, update, and track items associated with individual Tributes and send this inventory data alongside in-game prompts. This specification will serve as the basis for development and iteration.

## 1.2 Scope

The Inventory Management System will encompass the following core functionalities:

* Creation and persistent storage of a Tribute-specific inventory.  
* Functions for Gamemakers to get, set, add, and remove items from an inventory.  
* A search function to identify which Tributes possess a specific item.  
* Presentation of inventory updates to Gamemakers via ephemeral Discord embeds.

# 2\. Detailed Requirements

## 2.1 Inventory Data Structure (Class: `Inventory`)

| Attribute | Description | Data Type | Storage | Persistence | Capacity |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Storage Mechanism** | The inventory data will be stored as a JSON file on the bot's server (consider moving to an indexed database like SQLite for scalability, see Section 3.2). | JSON | Server File System | Indefinite (until cleared by a user) | N/A |
| **Data Structure** | **REVISED:** A dictionary where the keys are the item names and the values are the quantity of that item. This eliminates the need for re-keying on removal. | **Dictionary (string: int)** | N/A | N/A | N/A |
| **Soft Capacity** | A user-defined, non-enforced limit on the number of *unique* items. If this capacity is exceeded, the system must add a warning message to the returned embed. | Integer | N/A | N/A | User-Input |

# 2.2 Functional Specifications

## 2.2.1 Get Inventory

* **Function:** `get_inventory`  
* **Arguments:** Tribute ID (Unique identifier for the Tribute)  
* **Action:** Retrieves the complete, current inventory for the specified Tribute.  
* **Return:** An **ephemeral** Discord embed containing a numbered list of all items in the inventory.

## 2.2.2 Set Inventory (Full Replacement/Edit)

* **Function:** `set_inventory`  
* **Arguments:** Tribute ID  
* **Action:**  
  1. Opens a **modal dialogue** (pop-up) for the Gamemaker.  
  2. The modal will display the current inventory in a series of text boxes, pre-filled with the existing item values, with the incrementing slot numbers as labels.  
  3. The Gamemaker can edit, remove, or add new items in the text boxes. This action will completely replace the Tribute's old inventory with the new data.  
* **Return:** An **ephemeral** Discord embed showing the complete, updated inventory.

## 2.2.3 Add to Inventory

* **Function:** `add_to_inventory`  
* **Arguments:** Tribute ID, Item to Add (`string`)  
* **Action:** Appends the specified item to the end of the Tribute's current inventory dictionary (i.e., assigns the next available incrementing number as the key).  
* **Return:** An **ephemeral** Discord embed showing the complete, updated inventory.

## 2.2.4 Remove from Inventory

* **Function:** `remove_from_inventory`  
* **Arguments:** Tribute ID, Item to Remove (`string`)  
* **Action:** Searches for and removes the first instance of the specified item from the Tribute's inventory dictionary. If multiple instances exist, only one is removed per function call. The remaining items should be re-keyed to maintain sequential, incrementing numbers.  
* **Return:** An **ephemeral** Discord embed showing the complete, updated inventory.

## 2.2.5 Search Inventories

* **Function:** `search_inventories`  
* **Arguments:** Item to search for (`string`)  
* **Action:** Scans all stored Tribute inventories to find which ones contain the specified item.  
* **Return:** An **ephemeral** Discord embed with a list of all Tribute IDs whose inventory contains the searched item.

## 2.2.6 Clear Inventory(ies)

* **Function:** `clear_inventory`  
* **Arguments:** Tribute ID (Unique identifier for the Tribute)  
* **Action:** Deletes the specified Tribute's entire inventory from storage.  
* **Return**: An **ephemeral** Discord embed confirming: "Inventory for \[Tribute ID\] has been successfully cleared."

# 2.3 Error Handling and Robustness

This section defines expected failure modes and the system's response to ensure a consistent and safe user experience for Gamemakers.

| Function(s) | Condition | Required Action |
| ----- | ----- | ----- |
| **All Functions** | Tribute ID is not found in the storage system. | Return an **ephemeral** embed with: "Error: Tribute ID not found in the system. No action taken." |
| **2.2.4 Remove** | The specified item is not found in the inventory. | Return an **ephemeral** embed with: "Error: '\[Item Name\]' not found in Tribute's inventory. No changes made." |
| **2.1 Soft Capacity** | Soft capacity is exceeded. | **Warning Format:** Append the following warning to the standard return embed: "⚠️ **WARNING:** Inventory capacity (\[Limit\]) has been exceeded." |
| **General** | Concurrency Control | Implement a file-locking mechanism to prevent race conditions during simultaneous read/write operations to the JSON file. |

# 

# 2.4 Security and Access Control

| Requirement | Description |
| ----- | ----- |
| **RBAC** | All inventory-management commands must validate the executing Discord user's permissions and only proceed if the user holds the designated "Gamemaker" role or equivalent. |

# 3\. Future Considerations (For Iteration)

* **Quantity/Stacking:** Modify the data structure to allow for item quantities (e.g., `{'item_name': quantity}`) instead of a simple numbered list. This would simplify inventory management for stackable items.  
* **Item Metadata:** Integrate an item database to allow items to have attributes (e.g., weight, rarity, description) that could be included in the inventory embed.  
* **Storage Scalability:** Research and plan for a migration from flat JSON files to an indexed, embedded database (e.g., SQLite or a NoSQL solution) to improve the performance of **Search Inventories** as the number of Tributes and items grows.