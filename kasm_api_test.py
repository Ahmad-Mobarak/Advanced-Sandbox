import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://127.0.0.1:8443/api/public/request_kasm"
data = {
    "api_key": "3lYaJHUwuzpp",
    "api_key_secret": "CL270rB6tsgVZ8pm5hgz94Pfbdn0Utcz",
    "user_id": "6f3fda65-66e8-49fa-a169-3490bbf9cfd6",
    "image_id": "54ffa417-dc10-485b-9929-0c047908ac8b",
    "kasm_url": "https://gemini.google.com/"
}

print("Testing Kasm API request...")
try:
    resp = requests.post(url, json=data, verify=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Exception: {e}")
