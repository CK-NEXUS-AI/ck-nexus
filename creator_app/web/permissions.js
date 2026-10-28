(() => {
  const $ = (id) => document.getElementById(id);
  const status = $('status');
  const tokenField = $('access-token');
  const setStatus = (message, kind = '') => { status.textContent = message; status.className = kind; };
  const profiles = {
    safe: ['system.inspect', 'code.analyze', 'repo.write', 'tests.run', 'infra.inspect', 'agents.parallel'],
    audit: ['system.inspect', 'code.analyze', 'infra.inspect'],
    git: ['system.inspect', 'code.analyze', 'repo.write', 'tests.run', 'git.local'],
    custom: null
  };
  const selected = (selector) => [...document.querySelectorAll(selector + ':checked')].map((node) => node.value);
  $('profile').addEventListener('change', () => {
    const preset = profiles[$('profile').value];
    if (preset) document.querySelectorAll('.permissions input').forEach((node) => { node.checked = preset.includes(node.value); });
  });
  document.querySelectorAll('.permissions input').forEach((node) => node.addEventListener('change', () => { $('profile').value = 'custom'; }));
  document.querySelectorAll('.high-impact-permission').forEach((node) => node.addEventListener('change', () => {
    const matchingPermission = [...document.querySelectorAll('.permissions input')].find((item) => item.value === node.value);
    if (node.checked && matchingPermission) matchingPermission.checked = true;
    $('profile').value = 'custom';
  }));
  const api = async (path, options = {}) => {
    const token = tokenField.value;
    if (!token) throw new Error('กรุณาใส่ CK-NEXUS Access Token');
    const response = await fetch(path, {
      ...options, mode: 'same-origin', credentials: 'same-origin', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token, ...(options.headers || {}) }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail?.message || body.detail || ('HTTP ' + response.status));
    return body;
  };
  const renderGrants = (grants) => {
    const host = $('grants');
    host.replaceChildren();
    if (!grants.length) { host.textContent = 'ยังไม่มี grant'; return; }
    grants.forEach((grant) => {
      const card = document.createElement('article');
      card.className = 'grant';
      const heading = document.createElement('strong');
      heading.textContent = grant.grant_id;
      const detail = document.createElement('p');
      detail.textContent = (grant.revoked_at ? 'REVOKED' : (grant.expires_at * 1000 <= Date.now() ? 'EXPIRED' : 'ACTIVE')) +
        ' · ' + grant.permissions.join(', ') + ' · ' + grant.targets.join(', ') +
        ' · หมดอายุ ' + new Date(grant.expires_at * 1000).toLocaleString();
      card.append(heading, detail);
      if (!grant.revoked_at && grant.expires_at * 1000 > Date.now()) {
        const button = document.createElement('button');
        button.className = 'secondary';
        button.textContent = 'เพิกถอน';
        button.addEventListener('click', async () => {
          if (!window.confirm('เพิกถอน grant ' + grant.grant_id + ' ใช่หรือไม่?')) return;
          try { await api('/api/permissions/grants/' + encodeURIComponent(grant.grant_id) + '/revoke', { method: 'POST', body: JSON.stringify({ revoked_by: $('approved-by').value.trim() || 'CK' }) }); await loadGrants(); setStatus('เพิกถอน grant แล้ว', 'success'); }
          catch (error) { setStatus('เพิกถอนไม่สำเร็จ: ' + error.message, 'error'); }
        });
        card.append(button);
      }
      host.append(card);
    });
  };
  const loadGrants = async () => { const result = await api('/api/permissions/grants'); renderGrants(result.grants || []); };
  $('refresh-button').addEventListener('click', async () => {
    try { await loadGrants(); setStatus('โหลดสถานะ grant แล้ว', 'success'); }
    catch (error) { setStatus('โหลดไม่สำเร็จ: ' + error.message, 'error'); }
  });
  $('grant-button').addEventListener('click', async () => {
    if (!window.isSecureContext && !['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)) {
      setStatus('หยุดเพื่อความปลอดภัย: เปิดหน้า Permission Center ผ่าน HTTPS', 'error'); return;
    }
    const permissions = selected('.permissions input');
    const targets = [...selected('.targets input'), ...$('custom-targets').value.split('\n').map((s) => s.trim()).filter(Boolean)];
    const approvedBy = $('approved-by').value.trim();
    const ttl = Number($('ttl').value);
    const budget = Number($('budget').value);
    const highImpactPermissions = selected('.high-impact-permission');
    if (!permissions.length || !targets.length || !approvedBy || !Number.isFinite(budget) || budget < 0 || budget > 10000) {
      setStatus('เลือกสิทธิ์ เป้าหมาย ผู้อนุมัติ และวงเงินที่ถูกต้องก่อน', 'error'); return;
    }
    if (!$('confirm').checked) { setStatus('กรุณายืนยันว่าตรวจสอบรายละเอียดแล้ว', 'error'); return; }
    const summary = 'อนุมัติชุดสิทธิ์นี้หรือไม่?\n\nสิทธิ์: ' + permissions.join(', ') +
      '\nเป้าหมาย: ' + targets.join(', ') + '\nอายุ: ' + ttl + ' วินาที\nวงเงิน API: $' + budget +
      '\nสิทธิ์ผลกระทบสูง: ' + (highImpactPermissions.length ? highImpactPermissions.join(', ') : 'ไม่มี');
    if (!window.confirm(summary)) { setStatus('ยกเลิกแล้ว ไม่มี grant ใหม่'); return; }
    $('grant-button').disabled = true;
    try {
      const grantId = 'batch-' + crypto.randomUUID();
      const result = await api('/api/permissions/grants', { method: 'POST', body: JSON.stringify({
        grant_id: grantId, permissions, targets, approved_by: approvedBy, ttl_seconds: ttl,
        max_cost_usd: budget, high_impact_permissions: highImpactPermissions
      }) });
      setStatus('บันทึก grant แล้ว: ' + result.grant.grant_id + '\nหมายเหตุ: การบันทึก grant ยังไม่ทำให้ controller ที่ไม่ได้เชื่อม Policy Gate ได้สิทธิ์เพิ่ม', 'success');
      $('confirm').checked = false;
      await loadGrants();
    } catch (error) { setStatus('บันทึกไม่สำเร็จ: ' + error.message, 'error'); }
    finally { tokenField.value = ''; $('grant-button').disabled = false; }
  });
})();