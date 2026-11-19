const form = document.querySelector('#feedback-form');
const result = document.querySelector('#result');
const submit = document.querySelector('#submit');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const values = new FormData(form);
  const payload = {
    kind: values.get('kind'), title: values.get('title'), message: values.get('message'),
    rating: values.get('rating') ? Number(values.get('rating')) : null,
    steps: values.get('steps') || '', expected: values.get('expected') || '',
    consent: values.get('consent') === 'on', website: values.get('website') || '',
  };
  submit.disabled = true;
  result.textContent = 'กำลังส่งรายงาน...';
  try {
    const response = await fetch('/api/public-feedback', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail?.message || body.detail || 'ส่งรายงานไม่สำเร็จ');
    result.textContent = body.feedback_id ? `รับรายงานแล้ว หมายเลข: ${body.feedback_id}` : 'ขอบคุณสำหรับความคิดเห็น';
    form.reset();
  } catch (error) {
    result.textContent = String(error.message || 'เกิดข้อผิดพลาด');
  } finally {
    submit.disabled = false;
  }
});
