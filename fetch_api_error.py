import urllib.request
import urllib.error
import json

try:
    urllib.request.urlopen("http://localhost:7071/api/const/book/1")
except urllib.error.HTTPError as e:
    print("Error code:", e.code)
    try:
        err_msg = e.read().decode('utf-8')
        print("Response body:", err_msg)
    except Exception as ex:
        print("Could not read body:", ex)
except Exception as e:
    print("Other error:", e)
