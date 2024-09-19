import requests

url = "http://localhost:8000/v1/supported_models"
response = requests.get(url)
print("-- Supported\n")
print(response.json())

url = "http://localhost:8000/v1/models"
response = requests.get(url)
print("\n\n-- Models\n")
print(response.json())