import { node } from '../shared/ui.js';
import { getCurrentUser, loginWithPassword, logout } from './auth-service.js';

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
  form.append(title, usernameLabel, passwordLabel, status, submit, cancel);
  panel.append(form);
  host.append(trigger, panel);
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
  }
  window.addEventListener('workspace:auth-changed', refresh);
  refresh();
}
