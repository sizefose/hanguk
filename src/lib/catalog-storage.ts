export const SCROLL_KEY = "hanguk:catalog:scroll";
export const PENDING_FILTERS_KEY = "hanguk:catalog:pending-filters";
export const CATALOG_RETURN_URL_KEY = "hanguk:catalog:return-url";
export const MODAL_BACK_KEY = "hanguk:catalog:modal-back";

export const makePreviewKey = (slug: string) => `hanguk:product:preview:${slug}`;

const canUseStorage = () => typeof window !== "undefined";

export const getSessionItem = (key: string): string | null => {
  if (!canUseStorage()) return null;
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
};

export const setSessionItem = (key: string, value: string): boolean => {
  if (!canUseStorage()) return false;
  try {
    sessionStorage.setItem(key, value);
    return true;
  } catch {
    // ignore storage errors
    return false;
  }
};

export const removeSessionItem = (key: string): void => {
  if (!canUseStorage()) return;
  try {
    sessionStorage.removeItem(key);
  } catch {
    // ignore storage errors
  }
};

export const setSessionJson = (key: string, value: unknown): boolean =>
  setSessionItem(key, JSON.stringify(value));

export const parseSessionJson = <T>(key: string): T | null => {
  const raw = getSessionItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
};

export const resolveCatalogReturnUrl = (value: string | null): string | null => {
  if (!value) return null;
  if (!value.startsWith("/")) return null;
  if (value.startsWith("/p/")) return null;
  return value;
};

export const getCatalogReturnUrl = (): string | null =>
  resolveCatalogReturnUrl(getSessionItem(CATALOG_RETURN_URL_KEY));
