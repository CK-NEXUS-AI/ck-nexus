(() => {
  const form = document.getElementById('approval-form');
  const button = document.getElementById('approve-button');
  const status = document.getElementById('status');
  const tokenField = document.getElementById('access-token');
  const clearButton = document.getElementById('clear-button');
  const setStatus = (message, kind = '') => {
    status.textContent = message;
    status.className = kind;
  };
  const clearSensitive = () => {
    tokenField.value = '';
  };
  clearButton.addEventListener('click', () => {
    form.reset();
    clearSensitive();
    setStatus('ล้างข้อมูลในฟอร์มแล้ว');
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (!window.isSecureContext && !['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)) {
      setStatus('หยุดเพื่อความปลอดภัย: กรุณาเปิดหน้าอนุมัติผ่าน HTTPS', 'error');
      return;
    }
    const approvalId = document.getElementById('approval-id').value.trim();
    const fingerprint = document.getElementById('fingerprint').value.trim().toLowerCase();
    const approvedBy = document.getElementById('approved-by').value.trim();
    const ttlSeconds = Number(document.getElementById('ttl').value);
    const token = tokenField.value;
    if (!/^[a-f0-9]{64}$/.test(fingerprint)) {
      setStatus('Fingerprint ต้องเป็นเลขฐานสิบหก 64 ตัวอักษร', 'error');
      return;
    }
    if (!document.getElementById('confirm-check').checked) {
      setStatus('ต้องติ๊กยืนยันหลังตรวจสอบรายละเอียดก่อน', 'error');
      return;
    }
    const accepted = window.confirm(
      'ยืนยันอนุมัติคำขอนี้หรือไม่?\n\nApproval ID: ' + approvalId +
      '\nFingerprint: ' + fingerprint +
      '\nผู้อนุมัติ: ' + approvedBy +
      '\nระยะเวลา: ' + Math.round(ttlSeconds / 60) + ' นาที'
    );
    if (!accepted) {
      clearSensitive();
      setStatus('ยกเลิกแล้ว ไม่มีการส่งคำขออนุมัติ');
      return;
    }
    button.disabled = true;
    setStatus('กำลังส่งคำขออนุมัติ…');
    try {
      const response = await fetch('/api/agnes/approvals', {
        method: 'POST',
        mode: 'same-origin',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({
          approval_id: approvalId,
          fingerprint,
          approved_by: approvedBy,
          ttl_seconds: ttlSeconds
        })
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = response.status === 401
          ? 'ยืนยันไม่สำเร็จ: Access Token ไม่ถูกต้องหรือไม่ได้รับอนุญาต'
          : response.status === 422
            ? 'ข้อมูลไม่ผ่านการตรวจสอบ กรุณาตรวจ Approval ID, fingerprint และระยะเวลา'
            : 'ระบบปฏิเสธคำขอ (HTTP ' + response.status + ')';
        setStatus(message, 'error');
        return;
      }
      setStatus(
        'อนุมัติสำเร็จ\nApproval ID: ' + String(result.approval_id || approvalId) +
        '\nผู้อนุมัติ: ' + String(result.approved_by || approvedBy) +
        '\nหมดอายุ: ' + String(result.expires_at || 'ระบบยืนยันแล้ว'),
        'success'
      );
      document.getElementById('confirm-check').checked = false;
    } catch (_) {
      setStatus('เชื่อมต่อ API ไม่สำเร็จ ตรวจสอบเครือข่ายแล้วลองใหม่ โดยระบบไม่ได้เก็บ token', 'error');
    } finally {
      clearSensitive();
      button.disabled = false;
    }
  });
})();
