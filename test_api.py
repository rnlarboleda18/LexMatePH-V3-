import requests
res = requests.get("http://localhost:7071/api/codex/versions?short_name=fc")
arts = res.json().get("articles", [])

print("API returned", len(arts), "articles")

art7 = next((a for a in arts if a.get("key_id", a.get("article_number")) == "7"), None)
if art7:
    print("Article 7:")
    print(repr(art7["content"]))
    
art8 = next((a for a in arts if a.get("key_id", a.get("article_number")) == "8"), None)
if art8:
    print("Article 8:")
    print(repr(art8["content"]))
else:
    print("Article 8 not found in API response!")
    print("Available keys around 8:")
    keys = [a.get("key_id") for a in arts]
    if "7" in keys: print(keys[keys.index("7"):keys.index("7")+5])
