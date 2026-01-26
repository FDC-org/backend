import pandas as pd
import requests

# ---------- CONFIG ----------
BRANCH_URL = "https://fdc-api.dharmatejan.in/api/onboard/branch/"
USER_URL = "https://fdc-api.dharmatejan.in/api/onboard/user/"
TOKEN = "Token 1199a52a-9763-45ce-ba58-fb86b0e8ec01"

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

# ---------- READ EXCEL ----------
df = pd.read_excel("fdc.xlsx")

for index, row in df.iterrows():
    try:
        # ---------- STEP 1: CREATE BRANCH ----------
        branch_payload = {
            "branchname": str(row["branchname"]).capitalize(),
            "location": str(row["location"]).capitalize(),
            "address": str(row["address"]).capitalize(),
            "phone_number": " ",
            "hub": str(row["hub"]),
            "incharge_name": " "
        }

        print(f"\n🔹 Creating branch for row {index + 1}...")

        branch_response = requests.post(
            BRANCH_URL,
            json=branch_payload,
            headers=HEADERS
        )

        if branch_response.status_code not in [200, 201]:
            print("❌ Branch creation failed:", branch_response.text)
            continue

        branch_data = branch_response.json()

        # ---------- EXTRACT BRANCH CODE (YOUR FORMAT) ----------
        try:
            branch_code = branch_data["hub_details"]["branch_code"]
        except:
            print("❌ Branch created but branch_code not found:", branch_data)
            continue

        print(f"✅ Branch created successfully. Branch Code = {branch_code}")

        # ---------- STEP 2: CREATE USER ----------
        user_payload = {
            "username": str(row["username"]),
            "password": str(row["password"]),
            "type": "branch",
            "code": str(branch_code),
            "firstname": " ",
            "lastname": " ",
            "phone_number": " ",
            "code_name": str(row["code_name"]).capitalize()
        }

        print(f"🔹 Creating user for branch {branch_code}...")

        user_response = requests.post(
            USER_URL,
            json=user_payload,
            headers=HEADERS
        )

        if user_response.status_code not in [200, 201]:
            print("❌ User creation failed:", user_response.text)
            continue

        print("✅ User created successfully.")

    except Exception as e:
        print("❌ Error in row", index + 1, ":", str(e))
