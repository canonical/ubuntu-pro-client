// Replaces rtd-address with new-address in links

const rtd_address = 'canonical-ubuntu-pro-client-proxy.readthedocs-hosted.com';
const new_address = 'ubuntu.com/pro-client/docs';
const new_path = '/' + new_address.split('/').slice(1).join('/');

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function overwriteMatchingAnchorUrls(container) {
  if (!container) return;

  const rtd_addressRegex = new RegExp(escapeRegExp(rtd_address), 'g');
  container.querySelectorAll('a[href], link[href]').forEach((anchor) => {
    anchor.href = anchor.href.replace(rtd_addressRegex, new_address);
  });
}

function prependPathToAnchorUrls(container, path) {
  if (!container) return;

  container.querySelectorAll('a[href], link[href]').forEach((anchor) => {
    const href = anchor.getAttribute('href');
    // Only prepend to root-relative URLs (e.g. "/en/stable/page.html").
    // Skip absolute URLs ("https://..."), protocol-relative URLs ("//..."),
    // anchors ("#..."), and other schemes ("mailto:", "tel:", ...) so they
    // aren't broken by having the path prepended.
    if (
      href &&
      href.startsWith('/') &&
      !href.startsWith('//') &&
      !href.startsWith(path)
    ) {
      anchor.setAttribute('href', path + href);
    }
  });
}

function patchFlyout() {
  const rtdFlyout = document.querySelector('readthedocs-flyout');
  if (!rtdFlyout) return false;
  if (rtdFlyout.dataset.urlOverwritePatched) return true;
  rtdFlyout.dataset.urlOverwritePatched = 'true';

  overwriteMatchingAnchorUrls(rtdFlyout);
  overwriteMatchingAnchorUrls(rtdFlyout.shadowRoot);

  rtdFlyout.addEventListener('click', () => {
    overwriteMatchingAnchorUrls(rtdFlyout);
    overwriteMatchingAnchorUrls(rtdFlyout.shadowRoot);
  });

  return true;
}

function patchNotification() {
  const rtdNotification = document.querySelector('readthedocs-notification');
  if (!rtdNotification) return false;
  if (rtdNotification.dataset.urlOverwritePatched) return true;
  rtdNotification.dataset.urlOverwritePatched = 'true';

  const patchAll = () => {
    overwriteMatchingAnchorUrls(rtdNotification);
    if (rtdNotification.shadowRoot) {
      overwriteMatchingAnchorUrls(rtdNotification.shadowRoot);
    }
  };

  // Patch any content that already exists.
  patchAll();

  // Notification content is rendered dynamically into the element's shadow DOM
  // by Lit when the config is loaded (asynchronously), so the initial patch
  // above will usually find nothing. Wait for the shadow root to become
  // available (the custom element may not have been upgraded yet) and then
  // observe it so that links are patched as soon as they are rendered.
  const observeShadowRoot = () => {
    if (!rtdNotification.shadowRoot) {
      requestAnimationFrame(observeShadowRoot);
      return;
    }

    patchAll();

    const observer = new MutationObserver(patchAll);
    observer.observe(rtdNotification.shadowRoot, {
      childList: true,
      subtree: true,
    });
  };

  observeShadowRoot();

  return true;
}

function patchSearch() {
  const rtdSearch = document.querySelector('readthedocs-search');
  if (!rtdSearch) return false;
  if (rtdSearch.dataset.urlOverwritePatched) return true;
  rtdSearch.dataset.urlOverwritePatched = 'true';

  const patchAll = () => {
    overwriteMatchingAnchorUrls(rtdSearch);
    prependPathToAnchorUrls(rtdSearch, new_path);
    if (rtdSearch.shadowRoot) {
      overwriteMatchingAnchorUrls(rtdSearch.shadowRoot);
      prependPathToAnchorUrls(rtdSearch.shadowRoot, new_path);
    }
  };

  // Patch any content that already exists.
  patchAll();

  // Search results are rendered dynamically into the element's shadow DOM by
  // Lit when the user performs a search, so the initial patch above will
  // usually find nothing. Wait for the shadow root to become available (the
  // custom element may not have been upgraded yet) and then observe it so that
  // result links are patched as soon as they are rendered.
  const observeShadowRoot = () => {
    if (!rtdSearch.shadowRoot) {
      requestAnimationFrame(observeShadowRoot);
      return;
    }

    patchAll();

    const observer = new MutationObserver(patchAll);
    observer.observe(rtdSearch.shadowRoot, {
      childList: true,
      subtree: true,
    });
  };

  observeShadowRoot();

  // Patch on click as well, to cover keyboard navigation (the Enter key calls
  // .click() on the active result) and any case the observer might miss.
  rtdSearch.addEventListener('click', patchAll);

  return true;
}

function init() {
  overwriteMatchingAnchorUrls(document.querySelector('header'));

  // Patch each addon independently. Using `&&` short-circuit evaluation here
  // would prevent later addons (e.g. search) from being patched at all if an
  // earlier one (e.g. flyout or notification) is disabled or not yet loaded.
  let flyoutDone = patchFlyout();
  let notificationDone = patchNotification();
  let searchDone = patchSearch();

  if (flyoutDone && notificationDone && searchDone) return;

  const observer = new MutationObserver(() => {
    if (!flyoutDone) flyoutDone = patchFlyout();
    if (!notificationDone) notificationDone = patchNotification();
    if (!searchDone) searchDone = patchSearch();
    if (flyoutDone && notificationDone && searchDone) {
      observer.disconnect();
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
}

if (document.body) {
  init();
} else {
  document.addEventListener('DOMContentLoaded', init);
}
