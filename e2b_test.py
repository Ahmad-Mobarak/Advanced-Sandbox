import urllib.request
import json

def test_e2b_sandbox():
    """Test the E2B AI Sandbox execution endpoint."""
    print("Testing E2B AI Sandbox Execution...")
    
    # 1. We authenticate using the static sandbox API key
    headers = {
        "Authorization": "Bearer sk_live_admin_replace_me",
        "Content-Type": "application/json"
    }
    
    # 2. Prepare the code snippet to execute inside the isolated E2B sandbox.
    # We will test installing a dependency (requests) and making an HTTP request.
    code_to_run = """
import requests
import sys
import platform

print(f"Python Version: {platform.python_version()}")
print(f"System: {platform.system()} {platform.release()}")

try:
    response = requests.get('https://api.github.com/zen')
    print(f"\\nNetwork Test (GitHub Zen): {response.text}")
except Exception as e:
    print(f"\\nNetwork Test Failed: {str(e)}")

print("\\n✅ Code execution completed successfully inside E2B Sandbox!")
"""

    payload = {
        "code": code_to_run,
        "language": "python",
        "dependencies": ["requests"],
        "timeout_seconds": 60,
        "network_access": "full",
        "allowed_domains": []
    }
    
    print("Sending code to E2B ephemeral sandbox...")
    
    # 3. Call the sandbox execution endpoint
    url = "http://127.0.0.1:8000/api/v1/ai-sandbox/execute"
    data = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            response_body = response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        status_code = e.code
        response_body = e.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to connect to the server: {e}")
        return
    
    print(f"Status Code: {status_code}")
    
    if status_code == 200:
        result = json.loads(response_body)
        print("\n" + "="*50)
        print("E2B EXECUTION RESULT")
        print("="*50)
        print(f"Status: {result.get('status')}")
        print(f"Execution Time: {result.get('execution_time_ms')} ms")
        print("-" * 50)
        print("STDOUT:")
        print(result.get('stdout'))
        
        if result.get('stderr'):
            print("-" * 50)
            print("STDERR:")
            print(result.get('stderr'))
        print("="*50)
    else:
        print(f"Error Response: {response_body}")

if __name__ == "__main__":
    test_e2b_sandbox()
