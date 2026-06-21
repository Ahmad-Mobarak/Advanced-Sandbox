import requests
import time

base_url = "http://localhost:8000/api/v1"
headers = {
    "Authorization": "Bearer sk_live_admin_replace_me"
}

print("1. Submitting a test malware sample...")
files = {
    'file': ('test_malware.txt', b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')
}
response = requests.post(f"{base_url}/samples", headers=headers, files=files, params={"priority": 10})

if response.status_code == 200:
    data = response.json()
    sample_id = data["sample_id"]
    print(f"✅ Submission successful! Sample ID: {sample_id}")
    print(f"Status: {data['status']}")
    
    print("\n2. Checking analysis status (waiting a few seconds)...")
    for _ in range(3):
        time.sleep(2)
        status_resp = requests.get(f"{base_url}/samples/{sample_id}", headers=headers)
        if status_resp.status_code == 200:
            status_data = status_resp.json()
            print(f"Current Status: {status_data['status']}")
            if status_data['status'] == 'completed':
                break
        else:
            print(f"Failed to get status: {status_resp.text}")
            break
else:
    print(f"❌ Submission failed! Status Code: {response.status_code}")
    print(response.text)
