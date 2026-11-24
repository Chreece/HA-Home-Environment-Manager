// Home Assistant loads this ES module once per document. A failed module import
// can be remembered for that document, so each retry needs a fresh module URL.
const cardTag = 'home-environment-manager-card';
const loaderURL = new URL(import.meta.url);
const cardURL = new URL('home-environment-manager-card.js', loaderURL);
cardURL.search = loaderURL.search;

if (!customElements.get(cardTag)) {
  const delays = [750, 2500, 6000];
  let attempt = 0;
  let delayIndex = 0;
  let pending = false;
  let timer;

  function clearRetry() {
    clearTimeout(timer);
    timer = undefined;
  }

  function stop() {
    clearRetry();
    window.removeEventListener('online', resume);
    window.removeEventListener('pageshow', resume);
    document.removeEventListener('visibilitychange', resume);
  }

  function resume(event) {
    // The initial pageshow is part of this load, not a return from the page cache.
    if (event.type === 'pageshow' && !event.persisted) return;
    if (document.visibilityState === 'hidden' || pending) return;
    clearRetry();
    delayIndex = 0;
    loadCard();
  }

  async function loadCard() {
    if (customElements.get(cardTag)) {
      stop();
      return;
    }
    // A local HA server or a cached module can be reachable while iOS reports offline.
    if (pending) return;
    pending = true;
    const url = new URL(cardURL);
    if (attempt) url.searchParams.set('hem_retry', String(attempt));
    attempt++;
    try {
      await import(url.href);
      stop();
    } catch (error) {
      if (delayIndex < delays.length) {
        timer = setTimeout(loadCard, delays[delayIndex++]);
      } else {
        console.warn('HEM could not load the dashboard card. Waiting for the app to resume or reconnect.', error);
      }
    } finally {
      pending = false;
    }
  }

  window.addEventListener('online', resume);
  window.addEventListener('pageshow', resume);
  document.addEventListener('visibilitychange', resume);
  loadCard();
}
