import requests
headers = {"Authorization": "Bearer csk-mtycvf96c3twwcwxxhcvn6vwdh5pcj3x9mjwc26pdvyrfxmn"}
resp = requests.get("https://api.cerebras.ai/v1/models", headers=headers)
print(resp.json())