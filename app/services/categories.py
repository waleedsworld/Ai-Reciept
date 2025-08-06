import os
import uuid
from datetime import datetime, timezone
import pandas as pd

# Constants
STORAGE_DIR = "storage"
META_FILE = "meta.json"

# Ensure the storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)

# Dummy function to simulate extracting user ID from token
def extract_user_id(token):
    return token  

def rename_category(token, cat_id, data):
    user_id = extract_user_id(token)

    # File paths
    meta_path = os.path.join(STORAGE_DIR, META_FILE)
    categories_path = os.path.join(STORAGE_DIR, "categories.csv")

    # Load metadata and categories
    if not os.path.exists(meta_path) or not os.path.exists(categories_path):
        return {"error": "Metadata or category data missing"}, 500

    try:
        meta_df = pd.read_json(meta_path)
        cat_df = pd.read_csv(categories_path)
    except Exception as e:
        return {"error": "Failed to load data", "details": str(e)}, 500

    # Step 1: Get instance_id for this user (assuming one instance per user)
    user_instances = meta_df[meta_df["user_id"] == user_id]
    if user_instances.empty:
        return {"error": "No workspace found for user"}, 404

    # ⚠️ If multiple instances exist for the user, you can refine this part as needed.
    instance_id = user_instances.iloc[0]["instance_id"]

    # Step 2: Find category with matching cat_id AND instance_id
    cat_row = cat_df[(cat_df["id"] == int(cat_id)) & (cat_df["instance_id"] == instance_id)]
    if cat_row.empty:
        return {"error": "Category not found in this workspace"}, 404

    # Step 3: Validate input
    new_name = data.get("name", "").strip()
    if not new_name:
        return {"error": "Missing category name"}, 400

    # Step 4: Update name
    idx = cat_row.index[0]
    cat_df.at[idx, "name"] = new_name

    # Step 5: Save back to file
    try:
        cat_df.to_csv(categories_path, index=False)
    except Exception as e:
        return {"error": "Failed to save category", "details": str(e)}, 500

    # Step 6: Return updated category
    return {"id": int(cat_id), "name": new_name}, 200



def delete_category(token, cat_id):
    user_id = extract_user_id(token)

    # File paths
    meta_path = os.path.join(STORAGE_DIR, META_FILE)
    categories_path = os.path.join(STORAGE_DIR, "categories.csv")

    # Step 1: Load metadata and categories
    if not os.path.exists(meta_path) or not os.path.exists(categories_path):
        return {"error": "Metadata or categories not found"}, 500

    meta_df = pd.read_json(meta_path)
    cat_df = pd.read_csv(categories_path)

    # Step 2: Get instance_id from user_id
    user_instances = meta_df[meta_df["user_id"] == user_id]
    if user_instances.empty:
        return {"error": "No workspace found for user"}, 404

    # If user has multiple instances, you may need to modify this logic
    instance_id = user_instances.iloc[0]["instance_id"]

    # Step 3: Find the category with matching id & instance
    cat_row = cat_df[(cat_df["id"] == int(cat_id)) & (cat_df["instance_id"] == instance_id)]
    if cat_row.empty:
        return {"error": "Category not found in this workspace"}, 404

    # Step 4: Ensure at least one category remains after deletion
    instance_categories = cat_df[cat_df["instance_id"] == instance_id]
    if len(instance_categories) <= 1:
        return {"error": "At least one category must remain"}, 400

    # Step 5: Update rows in instance CSV with category_id == cat_id → 0
    instance_csv_path = os.path.join(STORAGE_DIR, f"instances/{instance_id}.csv")
    if not os.path.exists(instance_csv_path):
        return {"error": "Instance data file not found"}, 500

    try:
        instance_df = pd.read_csv(instance_csv_path)
        instance_df.loc[instance_df["category_id"] == int(cat_id), "category_id"] = 0
        instance_df.to_csv(instance_csv_path, index=False)
    except Exception as e:
        return {"error": "Failed to update instance data", "details": str(e)}, 500

    # Step 6: Remove category from categories.csv
    cat_df = cat_df.drop(cat_row.index)
    try:
        cat_df.to_csv(categories_path, index=False)
    except Exception as e:
        return {"error": "Failed to save updated categories", "details": str(e)}, 500

    return {"deleted": True}, 200
