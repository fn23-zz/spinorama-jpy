import re
import sys

path = sys.argv[1]
pat = sys.argv[2]
t = open(path, encoding="utf-8", errors="replace").read()
for m in list(re.finditer(re.escape(pat), t))[:3]:
    s = max(0, m.start() - 700)
    print("-" * 50)
    print(t[s:m.end() + 200].replace("\\u002F", "/")[-900:])
