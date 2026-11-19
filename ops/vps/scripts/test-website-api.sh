#!/usr/bin/env bash
set +x

printf 'กรุณาป้อน Website API Key / Token ใหม่: '
IFS= read -r -s WEBSITE_TOKEN
printf '\n'

if [[ -z "$WEBSITE_TOKEN" ]]; then
  echo "FAIL: ไม่ได้รับ API Key"
  exit 1
fi

echo "กำลังทดสอบ Vicoa ด้วย Key ที่ป้อน..."
vicoa --api-key "$WEBSITE_TOKEN" task ls
RESULT=$?

unset WEBSITE_TOKEN
echo "EXIT_CODE=$RESULT"

if [[ "$RESULT" -eq 0 ]]; then
  echo "CLI_COMMAND=PASS"
else
  echo "CLI_COMMAND=FAIL"
fi
