import requests, json
url = "https://object-store.os-api.cci2.ecmwf.int:443/cci2-prod-catalogue/resources/cems-glofas-historical/constraints_bef9c7bb6569dbb3cd25e0f769ab301d0c1adee87f41859807680029ac98f2c3.json"
r = requests.get(url)
with open('constraints.json', 'w') as f:
    f.write(r.text)
