const API_BASE = (
  process.env.INTERNAL_API_BASE ??
  process.env.NEXT_PUBLIC_API_BASE ??
  "http://localhost:8000/api"
).replace(/\/+$/, "");

type CatalogStaticData = {
  banners: unknown[];
  promoCards: unknown[];
  about: { sections: unknown[] };
  hero: { description: string; image: string | null };
  siteSettings: unknown | null;
};

const fetchStaticJson = async <T>(path: string, fallback: T): Promise<T> => {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: 60 },
      cache: "force-cache",
    });
    if (!response.ok) {
      return fallback;
    }
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
};

export const getCatalogStaticData = async (): Promise<CatalogStaticData> => {
  const [banners, promoCards, about, hero, siteSettings] = await Promise.all([
    fetchStaticJson<unknown[]>("/banners/", []),
    fetchStaticJson<unknown[]>("/promo-cards/", []),
    fetchStaticJson<{ sections: unknown[] }>("/about-section/", { sections: [] }),
    fetchStaticJson<{ description: string; image: string | null }>("/hero/", {
      description: "",
      image: null,
    }),
    fetchStaticJson<unknown | null>("/site-settings/", null),
  ]);

  return {
    banners,
    promoCards,
    about,
    hero,
    siteSettings,
  };
};

export type { CatalogStaticData };
