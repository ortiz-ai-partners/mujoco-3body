import json
import sys
c = json.load(open(sys.argv[1], encoding="utf-8"))
n = len(c)
k = max(1, n // 5)
print("episodes", n)
for i in range(5):
    part = c[i * k:(i + 1) * k] if i < 4 else c[i * k:]
    if part:
        print(f"ep {i * k:3d}-{i * k + len(part) - 1:3d}: success {sum(r['success'] for r in part)}/{len(part)}  "
              f"landed {sum(r['landed'] for r in part)}")
