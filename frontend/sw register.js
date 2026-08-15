/**
 * sw-register.js
 *
 * Registers the service worker so Veridict becomes a properly
 * installable PWA. Safe to include on every page — if the browser
 * doesn't support service workers, this does nothing and causes
 * no errors.
 */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((reg) => {
        console.log('Veridict service worker registered:', reg.scope);
      })
      .catch((err) => {
        console.warn('Veridict service worker registration failed:', err);
      });
  });
}