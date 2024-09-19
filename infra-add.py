import requests

url = "http://localhost:8000/v1/models"
params = {
    "model_name": "google/gemma-2-9b-it",
}

response = requests.post(url, params=params)
print(response.json())