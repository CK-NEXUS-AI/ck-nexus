import re
p = '/root/ckctl'
s = open(p).read()

# chrome-open
s = s.replace(
'''chrome-open)
  URL="${2:-https://chat.qwen.ai}"''',
'''chrome-open)
  URL="${2:-https://chat.qwen.ai}"
  if [ "$URL" = "URL" ] || [ -z "$URL" ]; then echo "❌ ใส่ URL จริง: ~/ckctl chrome-open https://example.com"; exit 1; fi
  if ! echo "$URL" | grep -qE "^https?://"; then echo "❌ URL ต้องเริ่มด้วย http:// หรือ https://"; exit 1; fi''')

# chrome-tab
s = s.replace(
'''chrome-tab)
  N="${2:-1}"''',
'''chrome-tab)
  N="${2:-1}"
  if ! echo "$N" | grep -qE "^[1-9]$"; then echo "❌ ใส่ตัวเลข 1-9: ~/ckctl chrome-tab 1"; exit 1; fi''')

open(p, 'w').write(s)
print("✅ patched")
