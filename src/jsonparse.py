import json

with open("src/test.json", "r") as file:
    data = json.load(file)
    print(data)
