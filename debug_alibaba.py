import requests
from bs4 import BeautifulSoup

q = 'rtx 5080'
url = f'https://www.alibaba.com/trade/search?SearchText={q}&page=1'
resp = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
print('status', resp.status_code)
print('final_url', resp.url)
print('snippet', resp.text[:1200])
soup = BeautifulSoup(resp.text, 'html.parser')
print('anchor_count', len(soup.find_all('a', href=True)))
print('h3_count', len(soup.find_all('h3')))
print('div_count', len(soup.find_all('div')))
print('sample_classes', sorted({c for cls in soup.find_all(class_=True) for c in cls.get('class', [])})[:50])
print('sample_hrefs', [a.get('href') for a in soup.find_all('a', href=True)[:20]])
