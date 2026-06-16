import requests
from bs4 import BeautifulSoup

url = 'https://www.orsr.sk/hladaj_ico.asp'
params = {'ICO': '12345678', 'SID': '0'}
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, params=params, headers=headers, timeout=20)
resp.encoding = 'iso-8859-2'
print('Status:', resp.status_code)
print('Len:', len(resp.text))

soup = BeautifulSoup(resp.text, 'html.parser')
tables = soup.find_all('table', {'class': 'tab1'})
print('tab1 tables:', len(tables))

# Print first table rows
if tables:
    for i, row in enumerate(tables[0].find_all('tr')[:5]):
        cells = row.find_all(['td', 'th'])
        texts = [c.get_text(strip=True) for c in cells]
        print(f'Row {i}:', texts)
