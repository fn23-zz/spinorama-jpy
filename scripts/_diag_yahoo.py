import json
import re
import sys
sys.path.insert(0, "/home/nari/scripts/spinorama_JPY/scripts")
from _market_probe import fetch  # noqa: E402

kw = sys.argv[1]
url = "https://shopping.yahoo.co.jp/search?p=" + __import__("urllib.parse", fromlist=["quote"]).quote(kw)
html = fetch(url, "diag_yahoo_" + re.sub(r"\W+", "_", kw))
print("len", len(html))
print("title", (re.search(r"<title>(.*?)</title>", html, re.S) or [None, None])[1])
for pat in [r'"price":\s*\{[^}]{0,60}', r'"price":\s*\d+', r'"name":"[^"]{0,60}"',
            r'見つかりませんでした', r'該当する商品はありません']:
    hits = re.findall(pat, html)[:5]
    print(pat, "->", hits)
