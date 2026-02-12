# Specifications For Tribute-Centric Data Model and Storage Migration

# 1\. Introduction

## 1.1 Purpose

This document specifies the requirements and design for two critical changes to the THGBot architecture:

1. **Tribute-Centric Data Model:** Switching to a unified data model where all related variables are anchored to a central Tribute entity.  
2. **Storage Migration:** Transferring the bot's data management from flat JSON files to a more robust and scalable SQLite database.

This specification will serve as the guiding basis for implementing the new data model and storage solution, ensuring that all existing variables (inventory, prompts, IDs, files, etc.) are correctly associated with a specific 

## Tribute.1.2 Scope

The Tribute-Centric Data Model and Storage Migration will encompass the following core functionalities and changes:

* **Tribute Entity:** Establishment of a primary `Tribute` entity within the database.  
* **Variable Association:** All existing variables (including **Inventory**, **ID**, **Prompt Data**, and associated **Files**) must be restructured to be explicitly linked to a single `Tribute` entity.  
* **Data Persistence Layer:** The bot's data persistence mechanism will be fully migrated from the current JSON file storage to a single SQLite database instance.  
* **Data Integrity:** The migration must ensure lossless transfer of all existing data from JSON to SQLite and enforce relational integrity for Tribute-associated variables.

# 2\. Detailed Requirements

## 2.1 Tribute-Centric Data Model

| Requirement | Description | Associated Variables | Rationale |
| ----- | ----- | ----- | ----- |
| **Primary Entity** | A core `Tribute` entity must be created as the central object for the bot's data structure. | N/A | Simplifies data retrieval and ensures consistency across all bot functionalities. |
| **Relational Integrity** | All variable tables (Inventory, Prompts, Files) must contain a Foreign Key reference to the primary `Tribute ID`. | Inventory, Prompt Data, Files | Prevents orphaned records and enforces the rule that all data belongs to a Tribute. |

## 2.2 Storage Migration (JSON to SQLite)

| Attribute | Current Specification (JSON) | Revised Specification (SQLite) |
| ----- | ----- | ----- |
| **Storage Mechanism** | Flat JSON files stored on the server. | Indexed, embedded SQLite database file. |
| **Data Structure** | Disparate JSON dictionaries/arrays for different data types. | Relational tables (e.g., `Tributes`, `Inventories`, `Prompts`). |
| **Search Performance** | Slow for global searches (e.g., `Search Inventories`). | Significantly improved through database indexing. |
| **Transactionality** | Requires manual concurrency control (file locking). | Native database transaction support to ensure atomic operations. |

## 2.3 Migration Requirements

* **Data Conversion:** A one-time migration script must be developed to read all existing JSON data and correctly populate the new SQLite schema, associating all records with their respective Tribute ID.  
* **Backwards Compatibility:** For a short transition period, read operations should check both JSON and SQLite storage to minimize downtime, but all write operations must immediately target the SQLite database.