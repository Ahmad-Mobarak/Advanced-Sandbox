import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://127.0.0.1:8443/api/public/get_images'
data = {
    'api_key': '3lYaJHUwuzpp',
    'api_key_secret': 'CL270rB6tsgVZ8pm5hgz94Pfbdn0Utcz'
}
req = urllib.request.Request(
    url, 
    data=json.dumps(data).encode('utf-8'), 
    headers={'Content-Type': 'application/json'}
)

try:
    res = urllib.request.urlopen(req, context=ctx)
    print(json.loads(res.read()))
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode())
