const defaultApiBase =
  process.env.NODE_ENV === "production" ? "/api" : "http://localhost:8000/api";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? defaultApiBase).replace(/\/+$/, "");

const baseOrigin = API_BASE.replace(/\/api\/?$/, "");

export const resolveMediaUrl = (url: string | null | undefined) => {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  if (url.startsWith("/")) {
    return `${baseOrigin}${url}`;
  }
  return `${baseOrigin}/${url}`;
};

export const formatPrice = (value: string | number) => {
  const raw = typeof value === "number" ? value.toFixed(2) : String(value);
  const normalized = raw.replace(",", ".");
  const [whole, frac] = normalized.split(".");
  if (!frac || Number(frac) === 0) {
    return `${whole} ₽`;
  }
  return `${whole}.${frac} ₽`;
};
