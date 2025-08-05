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


def create_workspace(name, token):
    # 1. Validate name
    if not name or len(name) > 60:
        raise ValueError("Invalid workspace name")

    # 2. Generate required values
    user_id = extract_user_id(token)
    instance_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    # 3. Prepare the metadata file path
    meta_path = os.path.join(STORAGE_DIR, META_FILE)

    # 4. Load or initialize the metadata
    if os.path.exists(meta_path):
        meta_df = pd.read_json(meta_path)
    else:
        meta_df = pd.DataFrame(columns=["user_id", "instance_id", "name", "created_at"])
    
    # 5. Append the new workspace to metadata
    new_row = {
        "user_id": user_id,
        "instance_id": instance_id,
        "name": name,
        "created_at": created_at
    }
    meta_df = pd.concat([meta_df, pd.DataFrame([new_row])], ignore_index=True)

    # 6. Save the updated metadata
    meta_df.to_json(meta_path, orient="records", indent=2)

    # 7. Create an empty CSV file for the new instance
    csv_path = os.path.join(STORAGE_DIR, f"instances/{instance_id}.csv")
    pd.DataFrame(columns=["date", "text", "amount", "category_id", "receipt_id"]).to_csv(csv_path, index=False)

    # 8. Return response
    return {
        "instance_id": instance_id,
        "created_at": created_at
    }


def list_workspaces(token):
    # 1. Extract user_id from the token (username in your case)
    user_id = extract_user_id(token)

    # 2. Load the metadata file
    meta_path = os.path.join(STORAGE_DIR, META_FILE)
    if not os.path.exists(meta_path):
        return {"instances": []}  # No workspaces exist

    meta_df = pd.read_json(meta_path)

    # 3. Filter rows for the user
    user_instances = meta_df[meta_df["user_id"] == user_id]

    # 🔧 4. Convert 'created_at' to datetime to avoid TypeError
    user_instances["created_at"] = pd.to_datetime(user_instances["created_at"], errors="coerce")

    # 5. Order by created_at descending
    user_instances = user_instances.sort_values(by="created_at", ascending=False)

    # 6. Build response list
    instances = user_instances[["instance_id", "name"]].rename(
        columns={"instance_id": "id"}
    ).to_dict(orient="records")

    return {"instances": instances}



def get_workspace(instance_id, token):
    user_id = extract_user_id(token)

    # Step 1: Load metadata
    meta_path = os.path.join(STORAGE_DIR, META_FILE)
    if not os.path.exists(meta_path):
        return {"error": "No workspace exists"}, 404

    meta_df = pd.read_json(meta_path)

    # Step 2: Filter to get workspace details
    workspace_details = meta_df[meta_df["instance_id"] == instance_id]

    if workspace_details.empty:
        return {"error": "Workspace not found"}, 404

    if workspace_details.iloc[0]["user_id"] != user_id:
        return {"error": f"Workspace does not belong to user {user_id}"}, 401

    name = workspace_details.iloc[0]["name"]

    # Step 3: Read instance CSV
    csv_path = os.path.join(STORAGE_DIR, f"instances/{instance_id}.csv")
    if not os.path.exists(csv_path):
        return {"error": "Workspace data file not found"}, 500

    df = pd.read_csv(csv_path)

    # Step 4: Calculate total spend
    total_spend = df["amount"].sum()
    total_spend = round(float(total_spend), 2)

    # Step 5: Extract categories
    if "category_id" in df.columns:
        category_ids = df["category_id"].dropna().unique()
        categories = [{"id": int(cid), "name": f"Category {int(cid)}"} for cid in category_ids]
    else:
        categories = []

    return {
        "instance_id": instance_id,
        "name": name,
        "total_spend": total_spend,
        "categories": categories
    }, 200


def update_workspace(instance_id, token, data):
    user_id = extract_user_id(token)

    # Step 1: Load metadata
    meta_path = os.path.join(STORAGE_DIR, META_FILE)
    if not os.path.exists(meta_path):
        return {"error": "Metadata not found"}, 500

    try:
        meta_df = pd.read_json(meta_path)
    except Exception as e:
        return {"error": "Failed to load metadata", "details": str(e)}, 500

    # Step 2: Find the workspace
    workspace_row = meta_df[meta_df["instance_id"] == instance_id]
    if workspace_row.empty:
        return {"error": "Workspace not found"}, 404

    idx = workspace_row.index[0]

    # Step 3: Authorization check
    if meta_df.at[idx, "user_id"] != user_id:
        return {"error": "Forbidden"}, 403

    # Step 4: Reject if already archived
    if meta_df.get("archived", pd.Series(False)).at[idx]:
        return {"error": "Workspace is already archived"}, 400

    # Step 5: Patch fields
    if "name" in data and data["name"]:
        meta_df.at[idx, "name"] = data["name"]

    if "archived" in data:
        if "archived" not in meta_df.columns:
            meta_df["archived"] = False
        meta_df.at[idx, "archived"] = data["archived"]

    # Step 6: Ensure created_at is in ISO format before saving
    if "created_at" in meta_df.columns:
        meta_df["created_at"] = pd.to_datetime(
            meta_df["created_at"], errors="coerce"
        ).dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    # Step 7: Save updated metadata
    try:
        meta_df.to_json(meta_path, orient="records", indent=2)
    except Exception as e:
        return {"error": "Failed to save metadata", "details": str(e)}, 500

    # Step 8: Return updated info
    return {
        "instance_id": instance_id,
        "name": meta_df.at[idx, "name"]
    }, 200



def delete_workspace(token, instance_id):
    user_id = extract_user_id(token)

    # Step 1: Load metadata
    meta_path = os.path.join(STORAGE_DIR, META_FILE)
    if not os.path.exists(meta_path):
        return {"error": "Metadata not found"}, 500

    meta_df = pd.read_json(meta_path)

    # Step 2: Find the workspace
    workspace_row = meta_df[meta_df["instance_id"] == instance_id]
    if workspace_row.empty:
        return {"error": "Workspace not found"}, 404

    idx = workspace_row.index[0]

    # Step 3: Authorization check
    if meta_df.at[idx, "user_id"] != user_id:
        return {"error": "Forbidden"}, 403

    # Step 4: Delete the row from metadata
    meta_df = meta_df.drop(index=idx)
    meta_df.to_json(meta_path, orient="records", indent=2)

    # Step 5: Delete the CSV file
    csv_path = os.path.join(STORAGE_DIR, f"instances/{instance_id}.csv")
    if os.path.exists(csv_path):
        os.remove(csv_path)

    # step 6 delete associated reciept files
    # PENDING

    return {"deleted": True}, 200



def initialize_categories(token, instance_id, data):
    user_id = extract_user_id(token)

    # Step 1: Load metadata
    meta_path = os.path.join(STORAGE_DIR, META_FILE)
    CATEGORIES_PATH = os.path.join(STORAGE_DIR, "categories.csv")

    if not os.path.exists(meta_path):
        return {"error": "Metadata not found"}, 500

    meta_df = pd.read_json(meta_path)
    workspace_row = meta_df[meta_df["instance_id"] == instance_id]

    if workspace_row.empty:
        return {"error": "Workspace not found"}, 404

    if workspace_row.iloc[0]["user_id"] != user_id:
        return {"error": "Forbidden"}, 403

    # Step 2: Parse input
    raw_string = data.get("categories", "")
    input_names = [name.strip() for name in raw_string.split(",") if name.strip()]
    if not input_names:
        return {"error": "No valid category names"}, 400

    # Step 3: Load or initialize categories.csv
    if os.path.exists(CATEGORIES_PATH):
        cat_df = pd.read_csv(CATEGORIES_PATH)
    else:
        cat_df = pd.DataFrame(columns=["instance_id", "id", "name"])

    # Step 4: Filter existing categories for this instance
    existing = cat_df[cat_df["instance_id"] == instance_id]["name"].str.lower()
    new_names = [name for name in input_names if name.lower() not in existing.values]

    if not new_names:
        return {"message": "No new categories to add"}, 200

    # Step 5: Calculate next ID
    current_ids = cat_df[cat_df["instance_id"] == instance_id]["id"]
    start_id = current_ids.max() + 1 if not current_ids.empty else 1

    # Step 6: Create new rows
    new_rows = pd.DataFrame([
        {"instance_id": instance_id, "id": start_id + i, "name": name}
        for i, name in enumerate(new_names)
    ])

    # Step 7: Append and save
    cat_df = pd.concat([cat_df, new_rows], ignore_index=True)
    cat_df.to_csv(CATEGORIES_PATH, index=False)

    # Step 8: Build response
    response = new_rows[["id", "name"]].to_dict(orient="records")
    return {"categories": response}, 200


def add_category(token, instance_id, data):
    user_id = extract_user_id(token)

    # Step 1: Load metadata
    meta_path = os.path.join(STORAGE_DIR, META_FILE)
    CATEGORIES_PATH = os.path.join(STORAGE_DIR, "categories.csv")

    if not os.path.exists(meta_path):
        return {"error": "Metadata not found"}, 500

    meta_df = pd.read_json(meta_path)
    workspace_row = meta_df[meta_df["instance_id"] == instance_id]

    if workspace_row.empty:
        return {"error": "Workspace not found"}, 404

    if workspace_row.iloc[0]["user_id"] != user_id:
        return {"error": "Forbidden"}, 403

    # Step 2: Validate input
    name = data.get("name", "").strip()
    if not name:
        return {"error": "Missing category name"}, 400

    # Step 3: Load or initialize categories.csv
    if os.path.exists(CATEGORIES_PATH):
        cat_df = pd.read_csv(CATEGORIES_PATH)
    else:
        cat_df = pd.DataFrame(columns=["instance_id", "id", "name"])

    # Step 4: Check for duplicates
    existing = cat_df[
        (cat_df["instance_id"] == instance_id) &
        (cat_df["name"].str.lower() == name.lower())
    ]
    if not existing.empty:
        return {"error": "Category already exists"}, 400

    # Step 5: Generate ID
    current_ids = cat_df[cat_df["instance_id"] == instance_id]["id"]
    new_id = current_ids.max() + 1 if not current_ids.empty else 1

    # Step 6: Add new category
    new_row = pd.DataFrame([{
        "instance_id": instance_id,
        "id": new_id,
        "name": name
    }])
    cat_df = pd.concat([cat_df, new_row], ignore_index=True)
    cat_df.to_csv(CATEGORIES_PATH, index=False)

    # Step 7: Return response
    return {"id": int(new_id), "name": name}, 200
