import os
import pandas as pd
import uuid
import datetime
from app.utils.reciept_parser import reciept_parser
from app.utils.save_reciept_image import save_receipt_image
from app.services.workspace import add_category
import json


RECIEPTS_PATH = "storage/receipts"
RECIEPT_FILE = 'receipts.json'

def upload_and_parse_reciept(token,instance_id, file):
    # Step 1: Save uploaded image and generate receipt_id
    receipt_id, path = save_receipt_image(file)
    img_url = path.split('\\')[1]

    # Step 2: Parse the receipt
    extracted_json = reciept_parser(img_url, instance_id)

    # Ensure receipt_id and instance_id are added
    extracted_json["receipt_id"] = receipt_id
    extracted_json["instance_id"] = instance_id

    # Step 2.5: Handle missing category_ids (i.e., new categories)
    category_map = {}

    # Collect all unique category names to be added
    for item in extracted_json["items"]:
        if "category_name" in item and not item.get("category_id"):
            category_name = item["category_name"].strip()
            category_map[category_name] = None  # Placeholder for returned ID

    # Add categories via service and store their IDs
    for category_name in category_map.keys():
        category_resp, status = add_category(token,instance_id, {"name": category_name})
        if status == 200:
            category_map[category_name] = category_resp["id"]
        else:
            raise Exception(f"Failed to add category '{category_name}': {category_resp.get('error')}")

    # Replace category_name with category_id using the map
    for item in extracted_json["items"]:
        if "category_name" in item and not item.get("category_id"):
            category_name = item["category_name"].strip()
            item["category_id"] = category_map[category_name]
            item.pop("category_name", None)

    # Step 3: Append to receipts.json
    receipts_json_path = os.path.join(RECIEPTS_PATH, RECIEPT_FILE)

    if os.path.exists(receipts_json_path):
        with open(receipts_json_path, 'r') as f:
            try:
                receipt_data = json.load(f)
            except json.JSONDecodeError:
                receipt_data = []
    else:
        receipt_data = []

    receipt_data.append(extracted_json)

    with open(receipts_json_path, 'w') as f:
        json.dump(receipt_data, f, indent=2)

    # Step 4: Append items to instance CSV
    instance_csv_path = f"storage/instances/{instance_id}.csv"
    os.makedirs(os.path.dirname(instance_csv_path), exist_ok=True)

    csv_rows = []
    for item in extracted_json["items"]:
        csv_rows.append({
            "date": extracted_json.get("date", ""),
            "text": item["text"],
            "amount": item["price"],
            "category_id": item["category_id"],
            "receipt_id": receipt_id
        })

    file_exists = os.path.exists(instance_csv_path)
    df = pd.DataFrame(csv_rows)
    df.to_csv(instance_csv_path, mode='a', header=not file_exists, index=False)

    return {"receipt_id": receipt_id, "items": extracted_json['items']}



def get_parsed_reciept(reciept_id):
    path = os.path.join(RECIEPTS_PATH, RECIEPT_FILE)

    with open(path, 'r') as file:
        data = json.load(file)
    
    for reciept in data:
        if reciept.get('receipt_id') == reciept_id:
            return {"JSON":reciept,"url":f'storage/receipts/uploads/{reciept_id}.jpg'}

    return None  # If no match found



def correct_parse_reciept(token, reciept_id, fix_data):
    instance_id = fix_data.get("instance_id")
    if not instance_id:
        return {"error": "instance_id missing"}, 400

    receipt_path = os.path.join(RECIEPTS_PATH, RECIEPT_FILE)

    # Load the existing JSON data
    with open(receipt_path, 'r') as file:
        all_receipts = json.load(file)

    updated = False
    receipt_found = None

    # Apply fixes to JSON receipt
    for receipt in all_receipts:
        if receipt.get('receipt_id') == reciept_id:
            for fix in fix_data.get("fixes", []):
                line = fix.get("line")
                if isinstance(line, int) and 0 <= line < len(receipt.get("items", [])):
                    for key, value in fix.items():
                        if key != "line":
                            receipt["items"][line][key] = value
            # Recalculate total
            receipt["total"] = round(sum(item.get("price", 0) for item in receipt.get("items", [])), 2)
            updated = True
            receipt_found = receipt
            break

    if not updated:
        return {"error": f"No receipt found with ID: {reciept_id}"}, 404

    # Save updated JSON back
    with open(receipt_path, 'w') as file:
        json.dump(all_receipts, file, indent=2)

    # Update instance CSV
    csv_path = os.path.join("storage", "instances", f"{instance_id}.csv")
    if not os.path.exists(csv_path):
        return {"error": f"CSV not found for instance_id: {instance_id}"}, 404

    try:
        df = pd.read_csv(csv_path)

        # Locate rows that belong to the current receipt_id
        mask = df["receipt_id"] == reciept_id
        receipt_rows = df[mask].copy()

        for fix in fix_data.get("fixes", []):
            line = fix.get("line")
            if isinstance(line, int) and 0 <= line < len(receipt_rows):
                index = receipt_rows.index[line]
                for key, value in fix.items():
                    if key == "text":
                        df.at[index, "text"] = value
                    elif key == "price":
                        df.at[index, "amount"] = value
                    elif key == "category_id":
                        df.at[index, "category_id"] = value

        # Save updated CSV
        df.to_csv(csv_path, index=False)

    except Exception as e:
        return {"error": f"Error processing CSV: {str(e)}"}, 500

    return {"message": "Receipt and CSV updated successfully."}, 200
