#!/bin/bash
set +e
SANDBOX="c7d9vw"
PORT="8080"
echo "=== Cloud Sandbox: $SANDBOX (port $PORT) ==="
echo ""
echo "==> [1/5] รายการ cloud sandbox"
sbx --cloud ls
echo ""
echo "==> [2/5] รอ $SANDBOX ให้ขึ้น Running..."
for i in $(seq 1 30); do
    LINE=$(sbx --cloud ls 2>/dev/null | grep "$SANDBOX")
    if echo "$LINE" | grep -q "●"; then
        echo "  [$i/30] Running แล้ว"; break
    fi
    echo "  [$i/30] $(echo "$LINE" | awk '{print $4}')"; sleep 10
done
echo ""
echo "==> [3/5] attach (Ctrl+C เพื่อออก)"
sbx --cloud attach "$SANDBOX"
echo ""
echo "==> [4/5] เปิดพอร์ต $PORT"
sbx --cloud ports "$SANDBOX" --publish "$PORT" || echo "!! publish ไม่ได้"
echo ""
echo "==> [5/5] รายการพอร์ต + URL"
sbx --cloud ports "$SANDBOX"
echo ""
echo "=== เสร็จแล้ว ==="
