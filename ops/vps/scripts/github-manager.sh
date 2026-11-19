#!/bin/bash
set -e

echo "🚀 เริ่มกระบวนการจัดการ GitHub แบบชุดเดียวจบ..."
echo "------------------------------------------------"

# 1. เคลียร์พื้นที่ดิสก์ (แก้ปัญหา Usage 88.6%)
echo "🧹 กำลังเคลียร์พื้นที่ดิสก์..."
apt-get clean -y >/dev/null 2>&1
apt-get autoremove -y >/dev/null 2>&1
echo "✅ เคลียร์พื้นที่เสร็จสิ้น"

# 2. ตรวจสอบการล็อกอิน GitHub
echo "🔐 กำลังตรวจสอบสถานะ GitHub..."
gh auth status
echo "------------------------------------------------"

# 3. รับข้อมูลจากผู้ใช้
read -p "📦 ใส่ชื่อ Owner/Repo (เช่น spinlnw10-art/my-project): " REPO_NAME
read -p "📝 ใส่ชื่อไฟล์ที่ต้องการแก้ไข (เช่น README.md): " FILE_NAME

# 4. โคลนหรืออัปเดต Repository
REPO_DIR=$(echo $REPO_NAME | cut -d'/' -f2)
if [ -d "$REPO_DIR" ]; then
    echo "📂 พบโฟลเดอร์ $REPO_DIR แล้ว กำลังดึงข้อมูลล่าสุด..."
    cd "$REPO_DIR"
    git pull origin main || git pull origin master
else
    echo "📥 กำลังดาวน์โหลด Repository..."
    gh repo clone "$REPO_NAME"
    cd "$REPO_DIR"
fi

# 5. แก้ไขไฟล์
echo "------------------------------------------------"
echo "✏️  กำลังเปิดไฟล์ $FILE_NAME ให้แก้ไข (ใช้โปรแกรม nano)"
echo "💡 วิธีใช้: แก้ไขข้อความเสร็จแล้ว กด [Ctrl+O] → [Enter] เพื่อบันทึก, แล้วกด [Ctrl+X] เพื่อออก"
echo "------------------------------------------------"
sleep 2

# สร้างไฟล์ถ้ายังไม่มี
touch "$FILE_NAME"
nano "$FILE_NAME"

# 6. Commit และ Push
echo "------------------------------------------------"
echo "💾 กำลังบันทึกการเปลี่ยนแปลงขึ้น GitHub..."
git add "$FILE_NAME"
git commit -m "chore: อัปเดต $FILE_NAME ผ่าน VPS Auto-Script"
git push origin main || git push origin master

echo "------------------------------------------------"
echo "🎉 เสร็จสมบูรณ์! ไฟล์ของคุณถูกอัปเดตขึ้น GitHub แล้ว"
echo "🔗 ตรวจสอบได้ที่: https://github.com/$REPO_NAME"
