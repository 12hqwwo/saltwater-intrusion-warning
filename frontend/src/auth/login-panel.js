import { node } from '../shared/ui.js';
import { approveAccount, getCurrentUser, listPendingAccounts, loginWithPassword, logout, registerAccount } from './auth-service.js';

export function createLoginPanel(host) {
  const trigger = node('button', 'Đăng nhập', 'secondary');
  trigger.type = 'button';
  const panel = node('dialog');
  const form = node('form');
  const title = node('h2', 'Đăng nhập cán bộ');
  const username = node('input'); username.name = 'username'; username.required = true; username.autocomplete = 'username';
  const password = node('input'); password.name = 'password'; password.type = 'password'; password.required = true; password.autocomplete = 'current-password';
  const usernameLabel = node('label', 'Tên đăng nhập'); usernameLabel.append(username);
  const passwordLabel = node('label', 'Mật khẩu'); passwordLabel.append(password);
  const status = node('p', '', 'subtle'); status.setAttribute('role', 'status');
  const submit = node('button', 'Đăng nhập'); submit.type = 'submit';
  const cancel = node('button', 'Đóng', 'secondary'); cancel.type = 'button';
  cancel.addEventListener('click', () => panel.close());
  const openRegistration = node('button', 'Chưa có tài khoản? Đăng ký', 'text-button'); openRegistration.type = 'button';
  form.append(title, usernameLabel, passwordLabel, status, submit, openRegistration, cancel);
  panel.append(form);
  const registrationTrigger = node('button', 'Đăng ký', 'secondary'); registrationTrigger.type = 'button';
  const registrationPanel = node('dialog');
  const registrationForm = node('form');
  const registrationTitle = node('h2', 'Đăng ký tài khoản cán bộ');
  const registrationIntro = node('p', 'Tài khoản cần người kiểm tra duyệt trước khi đăng nhập.', 'subtle');
  const registrationName = node('input'); registrationName.name = 'display_name'; registrationName.required = true;
  registrationName.maxLength = 120; registrationName.autocomplete = 'name';
  const registrationNameLabel = node('label', 'Họ và tên'); registrationNameLabel.append(registrationName);
  const registrationUsername = node('input'); registrationUsername.name = 'username'; registrationUsername.required = true;
  registrationUsername.minLength = 3; registrationUsername.maxLength = 64;
  registrationUsername.pattern = '[A-Za-z0-9._-]+'; registrationUsername.autocomplete = 'username';
  const registrationUsernameLabel = node('label', 'Tên đăng nhập'); registrationUsernameLabel.append(registrationUsername);
  const registrationPassword = node('input'); registrationPassword.name = 'password'; registrationPassword.type = 'password';
  registrationPassword.required = true; registrationPassword.minLength = 12; registrationPassword.maxLength = 1024;
  registrationPassword.autocomplete = 'new-password';
  const registrationPasswordLabel = node('label', 'Mật khẩu (ít nhất 12 ký tự)'); registrationPasswordLabel.append(registrationPassword);
  const registrationConfirm = node('input'); registrationConfirm.name = 'password_confirm'; registrationConfirm.type = 'password';
  registrationConfirm.required = true; registrationConfirm.autocomplete = 'new-password';
  const registrationConfirmLabel = node('label', 'Nhập lại mật khẩu'); registrationConfirmLabel.append(registrationConfirm);
  const registrationStatus = node('p', '', 'subtle'); registrationStatus.setAttribute('role', 'status');
  const registrationSubmit = node('button', 'Gửi đăng ký'); registrationSubmit.type = 'submit';
  const registrationCancel = node('button', 'Đóng', 'secondary'); registrationCancel.type = 'button';
  registrationCancel.addEventListener('click', () => registrationPanel.close());
  registrationForm.append(registrationTitle, registrationIntro, registrationNameLabel, registrationUsernameLabel,
    registrationPasswordLabel, registrationConfirmLabel, registrationStatus, registrationSubmit, registrationCancel);
  registrationPanel.append(registrationForm);
  const pendingTrigger = node('button', 'Duyệt tài khoản', 'secondary'); pendingTrigger.type = 'button'; pendingTrigger.hidden = true;
  const pendingPanel = node('dialog');
  const pendingContent = node('div', undefined, 'auth-pending-content');
  const pendingTitle = node('h2', 'Tài khoản chờ duyệt');
  const pendingStatus = node('p', '', 'subtle'); pendingStatus.setAttribute('role', 'status');
  const pendingList = node('div');
  const pendingClose = node('button', 'Đóng', 'secondary'); pendingClose.type = 'button';
  pendingClose.addEventListener('click', () => pendingPanel.close());
  pendingContent.append(pendingTitle, pendingStatus, pendingList, pendingClose);
  pendingPanel.append(pendingContent);
  host.append(trigger, registrationTrigger, pendingTrigger, panel, registrationPanel, pendingPanel);
  function showRegistration() {
    panel.close(); registrationStatus.textContent = ''; registrationPanel.showModal(); registrationName.focus();
  }
  registrationTrigger.addEventListener('click', showRegistration);
  openRegistration.addEventListener('click', showRegistration);
  registrationForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (!registrationForm.reportValidity()) return;
    if (registrationPassword.value !== registrationConfirm.value) {
      registrationStatus.textContent = 'Hai lần nhập mật khẩu chưa khớp.'; return;
    }
    registrationSubmit.disabled = true; registrationStatus.textContent = 'Đang gửi đăng ký…';
    try {
      const result = await registerAccount(registrationUsername.value.trim(), registrationName.value.trim(), registrationPassword.value);
      registrationPassword.value = ''; registrationConfirm.value = '';
      registrationStatus.textContent = result.message;
    } catch (error) { registrationStatus.textContent = error.message; }
    finally { registrationSubmit.disabled = false; }
  });
  async function refreshPending() {
    pendingStatus.textContent = 'Đang tải đăng ký…'; pendingList.replaceChildren();
    try {
      const response = await listPendingAccounts();
      if (!pendingPanel.open) return;
      pendingStatus.textContent = response.items.length ? `${response.items.length} tài khoản chờ duyệt.` : 'Không có tài khoản chờ duyệt.';
      for (const candidate of response.items) {
        const row = node('div', undefined, 'auth-pending-row');
        const identity = node('span', `${candidate.display_name} · ${candidate.username}`);
        const approve = node('button', 'Duyệt'); approve.type = 'button';
        approve.addEventListener('click', async () => {
          approve.disabled = true; pendingStatus.textContent = `Đang duyệt ${candidate.username}…`;
          try { await approveAccount(candidate.user_id); await refreshPending(); }
          catch (error) { pendingStatus.textContent = error.message; approve.disabled = false; }
        });
        row.append(identity, approve); pendingList.append(row);
      }
    } catch (error) { pendingStatus.textContent = error.message; }
  }
  pendingTrigger.addEventListener('click', () => { pendingPanel.showModal(); refreshPending(); });
  trigger.addEventListener('click', () => {
    if (getCurrentUser()) { logout(); return; }
    panel.showModal(); username.focus();
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submit.disabled = true; status.textContent = 'Đang xác thực…';
    try {
      await loginWithPassword(username.value.trim(), password.value);
      password.value = ''; status.textContent = ''; panel.close();
    } catch (error) { status.textContent = error.message; }
    finally { submit.disabled = false; }
  });
  function refresh() {
    const user = getCurrentUser();
    trigger.textContent = user ? `${user.display_name} · Đăng xuất` : 'Đăng nhập';
    registrationTrigger.hidden = Boolean(user);
    pendingTrigger.hidden = user?.role !== 'INSPECTOR';
    if (user?.role !== 'INSPECTOR' && pendingPanel.open) pendingPanel.close();
  }
  window.addEventListener('workspace:auth-changed', refresh);
  refresh();
}
