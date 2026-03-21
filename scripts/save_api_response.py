import requests
import json

# Fetch Article 8 from the API
response = requests.get('http://localhost:7071/api/rpc/article/8')
data = response.json()

with open('article_8_response.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Article 8 paragraph_links:")
print(json.dumps(data.get('paragraph_links', {}), indent=2))

# Fetch Article 217 from the API
response = requests.get('http://localhost:7071/api/rpc/article/217')
data = response.json()

with open('article_217_response.json', 'w') as f:
    json.dump(data, f, indent=2)

print("\nArticle 217 paragraph_links:")
print(json.dumps(data.get('paragraph_links', {}), indent=2))
