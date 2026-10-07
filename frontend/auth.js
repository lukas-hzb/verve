import { createAuthClient } from '@neondatabase/auth';

const root = document.querySelector('[data-neon-auth]');
const csrf = root.dataset.csrf;
const client = createAuthClient(new URL('/auth/neon', location.origin).href, {
  fetchOptions: { headers: { 'X-CSRFToken': csrf } },
});
const form = document.querySelector('#auth-form');
const message = document.querySelector('#auth-message');
const verificationForm = document.querySelector('#verification-form');
let verificationEmail;
const buttons = root.querySelectorAll('button');
const destination = new URL(root.dataset.next || '/', location.origin);
const next = destination.origin === location.origin ? destination.href : location.origin + '/';
function showError(error) {
  message.textContent = error?.message || 'Authentication failed. Please try again.';
  message.hidden = false;
}
async function perform(action) {
  buttons.forEach(button => button.disabled = true);
  message.hidden = true;
  try {
    const result = await action();
    if (result?.error) throw result.error;
    return result;
  } catch (error) {
    showError(error);
    return null;
  } finally {
    buttons.forEach(button => button.disabled = false);
  }
}
form?.addEventListener('submit', async event => {
  event.preventDefault();
  const fields = Object.fromEntries(new FormData(form));
  const mode = root.dataset.mode;
  const result = await perform(() => {
    if (mode === 'register') return client.signUp.email({
      name: fields.username, email: fields.email, password: fields.password,
    });
    if (mode === 'change-password') return client.changePassword({
      currentPassword: fields.current_password, newPassword: fields.password,
      revokeOtherSessions: true,
    });
    if (mode === 'reset-password') return client.emailOtp.resetPassword({
      password: fields.password, email: fields.email, otp: fields.otp,
    });
    return client.signIn.email({ email: fields.email, password: fields.password });
  });
  if (result && mode !== 'register' && mode !== 'login') location.assign(next);
  else if (result) await finishSignIn(result.data?.user, fields.email);
});
document.querySelector('#google-login')?.addEventListener('click', () => perform(() =>
  client.signIn.social({ provider: 'google', callbackURL: new URL('/auth/callback?next=' + encodeURIComponent(next), location.origin).href,
    errorCallbackURL: new URL('/auth/login', location.origin).href })
));
document.querySelector('#forgot-password')?.addEventListener('click', async () => {
  const email = form.elements.email.value;
  if (!email) { showError({ message: 'Enter your email address first.' }); return; }
  const result = await perform(() => client.emailOtp.requestPasswordReset({ email }));
  if (result) location.assign('/auth/reset-password?email=' + encodeURIComponent(email));
});
// The official SDK exchanges Neon's OAuth verifier and restores its managed session.
if (root.dataset.mode === 'login' || root.dataset.mode === 'register') {
  const result = await perform(() => client.getSession());
  if (result?.data?.session) await finishSignIn(result.data.user, result.data.user.email);
}

async function finishSignIn(user, email) {
  if (user && user.emailVerified !== true) {
    verificationEmail = email;
    const sent = await perform(() => client.emailOtp.sendVerificationOtp({
      email, type: 'email-verification',
    }));
    if (sent) { form.hidden = true; verificationForm.hidden = false; }
    return;
  }
  location.assign(next);
}
verificationForm.addEventListener('submit', async event => {
  event.preventDefault();
  const result = await perform(() => client.emailOtp.verifyEmail({
    email: verificationEmail, otp: new FormData(verificationForm).get('otp'),
  }));
  if (result) location.assign(next);
});
