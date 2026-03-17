"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { formatPrice, resolveMediaUrl } from "@/lib/api";
import { apiFetchOr } from "@/lib/api-client";
import { getSiteSettingsRaw } from "@/lib/catalog-api";
import {
  CATALOG_RETURN_URL_KEY,
  MODAL_BACK_KEY,
  PENDING_FILTERS_KEY,
  SCROLL_KEY,
  makePreviewKey,
  parseSessionJson,
  removeSessionItem,
  setSessionItem,
  setSessionJson,
  getSessionItem,
} from "@/lib/catalog-storage";
import BottomSheet from "@/components/BottomSheet";

type Banner = {
  id: number;
  title: string;
  description: string;
  image: string;
  image_thumb?: string;
  background_image?: string | null;
  background_color?: string;
  background_opacity?: string | number;
  link_url: string;
};

type Product = {
  id: number;
  title: string;
  slug: string;
  photo: string | null;
  photo_thumb?: string | null;
  price: string;
  original_price: string;
  discounted_price: string | null;
  has_discount: boolean;
  discount_label: string | null;
  spicy: number;
  is_new: boolean;
  category_title: string;
  category_slug: string;
  country_title: string;
  country_slug: string;
};

type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

type PromoCardScenario = "link" | "list" | "new";
type PromoCard = {
  id: number;
  image: string;
  scenario: PromoCardScenario;
  link_url: string;
  sort_order: number;
  products: Product[];
};

type FilterOption = {
  id: number;
  title: string;
  slug: string;
  image: string | null;
  enabled: boolean;
  selected: boolean;
  discount_badge: string | null;
};

type FilterOptionsResponse = {
  categories: FilterOption[];
  countries: FilterOption[];
  all_categories_image: string | null;
  all_countries_image: string | null;
};

type AboutSection = {
  id: number;
  title: string;
  slug: string;
  description: string;
  image: string | null;
  section_type: "generic" | "location";
  map_script_url: string;
  is_active?: boolean;
};

type AboutSectionResponse = {
  sections: AboutSection[];
};

type HeroSection = {
  description: string;
  image: string | null;
};

type SiteAddress = {
  text: string;
  url: string;
};

type SiteContact = {
  text: string;
  href: string;
};

type SiteSocial = {
  platform: "vk" | "whatsapp" | "telegram";
  url: string;
};

type SiteSettings = {
  header_action_label: string;
  header_action_url: string;
  telegram_button_label: string;
  telegram_button_url: string;
  order_phone_display: string;
  order_phone_link: string;
  addresses: SiteAddress[];
  contacts: SiteContact[];
  social_links: SiteSocial[];
  stores: SiteStore[];
  maker_label: string;
  maker_url: string;
  legal_text: string;
  new_badge_days: number;
  hide_prices: boolean;
  default_category_slugs: string[];
};

type DeliveryServiceKey = "chibbis" | "yandex_food" | "pickup";
type SiteStoreDelivery = {
  id: number;
  service_type: DeliveryServiceKey;
  service_url: string;
  map_script_url: string;
};
type SiteStore = {
  id: number;
  name: string;
  address: string;
  phone: string;
  deliveries: SiteStoreDelivery[];
};

type FilterModalKind = "category" | "country" | null;

type SortKey = "" | "price_asc" | "price_desc" | "new";

type PendingFilters = {
  category: string[];
  country: string[];
};

type CatalogPageInitialData = {
  banners?: unknown[];
  promoCards?: unknown[];
  about?: unknown;
  hero?: unknown;
  siteSettings?: unknown | null;
};

const BANNER_AUTOPLAY_INTERVAL_MS = 3000;
const BANNER_INTERACTION_COOLDOWN_MS = 8000;
const CATALOG_ROWS_PER_PAGE = 10;
const SOCIAL_ICONS: Record<SiteSocial["platform"], string> = {
  vk: "/static/icons/vk.svg",
  whatsapp: "/static/icons/wa.png",
  telegram: "/static/icons/tg.svg",
};
const SOCIAL_LABELS: Record<SiteSocial["platform"], string> = {
  vk: "VK",
  whatsapp: "WhatsApp",
  telegram: "Telegram",
};
const SOCIAL_ORDER: SiteSocial["platform"][] = ["vk", "whatsapp", "telegram"];
const DELIVERY_SERVICE_META: Record<DeliveryServiceKey, { label: string; icon: string }> = {
  chibbis: {
    label: "Чиббис",
    icon: "/static/icons/chibbis.svg",
  },
  yandex_food: {
    label: "Яндекс.Еда",
    icon: "/static/icons/yandex_food.svg",
  },
  pickup: {
    label: "Самовывоз",
    icon: "/static/icons/call.svg",
  },
};
const STATIC_FOOTER_MAKER = {
  label: "sizeworks",
  url: "https://t.me/+OODKdq0iQFsyMDky",
};

const SORT_OPTIONS: Array<{ key: SortKey; label: string }> = [
  { key: "price_asc", label: "дешевле" },
  { key: "price_desc", label: "дороже" },
  { key: "new", label: "новинки" },
];

const detectColumns = (width: number): number => {
  if (width >= 1200) return 4;
  if (width >= 1024) return 3;
  return 2;
};

const readInitialPageSize = (): number => {
  if (typeof window === "undefined") {
    return 20;
  }
  return detectColumns(window.innerWidth) * CATALOG_ROWS_PER_PAGE;
};

const normalizeFilterOptions = (value: unknown): FilterOption[] => {
  if (!Array.isArray(value)) return [];

  return value
    .map((option) => {
      const raw = option as Partial<FilterOption> & Record<string, unknown>;
      return {
        id: Number.isFinite(raw.id as number) ? Number(raw.id) : 0,
        title: typeof raw.title === "string" ? raw.title : "",
        slug: typeof raw.slug === "string" ? raw.slug : "",
        image: typeof raw.image === "string" ? raw.image : null,
        enabled: Boolean(raw.enabled),
        selected: Boolean(raw.selected),
        discount_badge:
          typeof raw.discount_badge === "string" && raw.discount_badge.trim()
            ? raw.discount_badge
            : null,
      } as FilterOption;
    })
    .filter((option) => option.id > 0 && option.slug);
};

const normalizePromoCards = (value: unknown): PromoCard[] => {
  const source = Array.isArray(value)
    ? value
    : Array.isArray((value as { results?: unknown[] })?.results)
      ? (value as { results: unknown[] }).results
      : Array.isArray((value as { data?: unknown[] })?.data)
        ? (value as { data: unknown[] }).data
        : [];

  if (!source.length) return [];

  return source
    .map((item) => item as Record<string, unknown>)
    .map((item) => {
      const scenario = item.scenario;
      const normalizedScenario: PromoCardScenario =
        scenario === "link" || scenario === "list" || scenario === "new"
          ? scenario
          : "link";
      const rawProducts = Array.isArray(item.products) ? item.products : [];
      const products = rawProducts as Product[];

      return {
        id: Number.isFinite(Number(item.id)) ? Number(item.id) : 0,
        image: typeof item.image === "string" ? item.image : "",
        scenario: normalizedScenario,
        link_url: typeof item.link_url === "string" ? item.link_url : "",
        sort_order: Number.isFinite(Number(item.sort_order)) ? Number(item.sort_order) : 0,
        products: Array.isArray(products) ? products : [],
      } as PromoCard;
    })
    .filter((card) => card.id > 0);
};

const normalizeAboutSections = (value: unknown): AboutSection[] => {
  const sections = Array.isArray((value as AboutSectionResponse | null)?.sections)
    ? ((value as AboutSectionResponse).sections as AboutSection[])
    : [];
  return sections.filter((section) => section.is_active !== false);
};

const normalizeSiteSettings = (value: unknown): SiteSettings => {
  const data = (value ?? {}) as Record<string, unknown>;

  const addresses = Array.isArray(data.addresses)
    ? data.addresses
        .map((item) => item as Record<string, unknown>)
        .map((item) => ({
          text: typeof item.text === "string" ? item.text : "",
          url: typeof item.url === "string" ? item.url : "",
        }))
        .filter((item) => item.text)
    : [];

  const contacts = Array.isArray(data.contacts)
    ? data.contacts
        .map((item) => item as Record<string, unknown>)
        .map((item) => ({
          text: typeof item.text === "string" ? item.text : "",
          href: typeof item.href === "string" ? item.href : "",
        }))
        .filter((item) => item.text)
    : [];

  const socialLinks = Array.isArray(data.social_links)
    ? data.social_links
        .map((item) => item as Record<string, unknown>)
        .map((item) => {
          const platform = item.platform;
          return {
            platform:
              platform === "vk" || platform === "whatsapp" || platform === "telegram"
                ? platform
                : "telegram",
            url: typeof item.url === "string" ? item.url : "",
          } as SiteSocial;
        })
        .filter((item) => item.url)
    : [];
  const stores = Array.isArray(data.stores)
    ? data.stores
        .map((item) => item as Record<string, unknown>)
        .map((item) => {
          const rawDeliveries = Array.isArray(item.deliveries) ? item.deliveries : [];
          const deliveries = rawDeliveries
            .map((delivery) => delivery as Record<string, unknown>)
            .map((delivery) => {
              const serviceType = delivery.service_type;
              return {
                id: Number.isFinite(delivery.id as number) ? Number(delivery.id) : 0,
                service_type:
                  serviceType === "chibbis" ||
                  serviceType === "yandex_food" ||
                  serviceType === "pickup"
                    ? serviceType
                    : "pickup",
                service_url:
                  typeof delivery.service_url === "string" ? delivery.service_url : "",
                map_script_url:
                  typeof delivery.map_script_url === "string"
                    ? delivery.map_script_url
                    : "",
              } as SiteStoreDelivery;
            })
            .filter((delivery) => delivery.id > 0);

          return {
            id: Number.isFinite(item.id as number) ? Number(item.id) : 0,
            name: typeof item.name === "string" ? item.name : "",
            address: typeof item.address === "string" ? item.address : "",
            phone: typeof item.phone === "string" ? item.phone : "",
            deliveries,
          } as SiteStore;
        })
        .filter((store) => store.id !== 0 && store.address)
    : [];

  return {
    header_action_label:
      typeof data.header_action_label === "string" ? data.header_action_label : "",
    header_action_url:
      typeof data.header_action_url === "string" ? data.header_action_url : "",
    telegram_button_label:
      typeof data.telegram_button_label === "string" ? data.telegram_button_label : "",
    telegram_button_url:
      typeof data.telegram_button_url === "string" ? data.telegram_button_url : "",
    order_phone_display:
      typeof data.order_phone_display === "string" ? data.order_phone_display : "",
    order_phone_link:
      typeof data.order_phone_link === "string" ? data.order_phone_link : "",
    addresses,
    contacts,
    social_links: socialLinks,
    stores,
    maker_label: typeof data.maker_label === "string" ? data.maker_label : "",
    maker_url: typeof data.maker_url === "string" ? data.maker_url : "",
    legal_text: typeof data.legal_text === "string" ? data.legal_text : "",
    new_badge_days: Number.isFinite(data.new_badge_days as number)
      ? Number(data.new_badge_days)
      : 0,
    hide_prices: Boolean(data.hide_prices),
    default_category_slugs: Array.isArray(data.default_category_slugs)
      ? data.default_category_slugs
          .map((item) => (typeof item === "string" ? item : ""))
          .filter(Boolean)
      : [],
  };
};

const reconcileSelection = (prev: string[], validSlugs: Set<string>): string[] => {
  const next = prev.filter((slug) => validSlugs.has(slug));
  if (next.length === prev.length && next.every((slug, index) => slug === prev[index])) {
    return prev;
  }
  return next;
};

const buildCatalogReturnUrl = () => {
  const params = new URLSearchParams(window.location.search);
  params.delete("product");
  const query = params.toString();
  return query ? `${window.location.pathname}?${query}` : window.location.pathname;
};

const hexToRgba = (hex: string | undefined, alpha: number): string | null => {
  if (!hex) return null;
  const normalized = hex.trim();
  const match = normalized.match(/^#?([0-9a-fA-F]{6})$/);
  if (!match) return null;
  const value = match[1];
  const r = Number.parseInt(value.slice(0, 2), 16);
  const g = Number.parseInt(value.slice(2, 4), 16);
  const b = Number.parseInt(value.slice(4, 6), 16);
  const clamped = Number.isFinite(alpha) ? Math.min(1, Math.max(0, alpha)) : 1;
  return `rgba(${r}, ${g}, ${b}, ${clamped})`;
};

const toTelHref = (raw: string): string => {
  const normalized = raw.replace(/[^\d+]/g, "");
  if (!normalized) return "";
  return normalized.startsWith("tel:") ? normalized : `tel:${normalized}`;
};

export default function CatalogPage({ initialData }: { initialData?: CatalogPageInitialData }) {
  const pathname = usePathname();
  const router = useRouter();
  const [activeBanner, setActiveBanner] = useState(0);
  const initialBanners = useMemo(
    () => (Array.isArray(initialData?.banners) ? (initialData.banners as Banner[]) : []),
    [initialData?.banners]
  );
  const initialPromoCards = useMemo(
    () => normalizePromoCards(initialData?.promoCards),
    [initialData?.promoCards]
  );
  const initialAboutSections = useMemo(
    () => normalizeAboutSections(initialData?.about),
    [initialData?.about]
  );
  const initialHeroSection = useMemo<HeroSection>(() => {
    const rawHero = (initialData?.hero ?? null) as Record<string, unknown> | null;
    return {
      description: typeof rawHero?.description === "string" ? rawHero.description : "",
      image: typeof rawHero?.image === "string" ? rawHero.image : null,
    };
  }, [initialData?.hero]);
  const initialSiteSettings = useMemo(
    () => (initialData?.siteSettings !== undefined ? normalizeSiteSettings(initialData.siteSettings) : null),
    [initialData?.siteSettings]
  );
  const hasInitialStaticData = Boolean(initialData);

  const [banners, setBanners] = useState<Banner[]>(initialBanners);
  const [promoCards, setPromoCards] = useState<PromoCard[]>(initialPromoCards);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortKey>("");
  const [isSortOpen, setIsSortOpen] = useState(false);
  const [sortPopupPosition, setSortPopupPosition] = useState<{
    top: number;
    left: number;
    width: number;
  } | null>(null);
  const [isStorePickerOpen, setIsStorePickerOpen] = useState(false);
  const [filterModal, setFilterModal] = useState<FilterModalKind>(null);
  const [filterOptions, setFilterOptions] = useState<FilterOptionsResponse>({
    categories: [],
    countries: [],
    all_categories_image: null,
    all_countries_image: null,
  });
  const [filtersRefreshToken, setFiltersRefreshToken] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalProducts, setTotalProducts] = useState(0);
  const [isProductsLoading, setIsProductsLoading] = useState(true);
  const [hasLoadedProductsOnce, setHasLoadedProductsOnce] = useState(false);
  const [pageSize, setPageSize] = useState(20);
  const [isPageSizeReady, setIsPageSizeReady] = useState(false);
  const [isBootstrapped, setIsBootstrapped] = useState(false);
  const [heroSection, setHeroSection] = useState<HeroSection>(initialHeroSection);
  const [isHeroLoading, setIsHeroLoading] = useState(!hasInitialStaticData);
  const [siteSettings, setSiteSettings] = useState<SiteSettings | null>(initialSiteSettings);
  const [aboutSections, setAboutSections] = useState<AboutSection[]>(initialAboutSections);
  const [activeAboutTab, setActiveAboutTab] = useState<string>(initialAboutSections[0]?.slug ?? "");
  const [selectedStoreId, setSelectedStoreId] = useState<number | "">("");
  const [deliveryModalState, setDeliveryModalState] = useState<{
    store: SiteStore;
    delivery: SiteStoreDelivery;
  } | null>(null);
  const [promoProductsModal, setPromoProductsModal] = useState<{
    products: Product[];
  } | null>(null);
  const [infoBannerHeight, setInfoBannerHeight] = useState(0);
  const [pageScrollbar, setPageScrollbar] = useState({
    top: 0,
    thumbTop: 0,
    thumbHeight: 32,
  });
  const [isDesktopScrollbar, setIsDesktopScrollbar] = useState(false);

  const touchStartX = useRef<number | null>(null);
  const touchCurrentX = useRef<number | null>(null);
  const aboutTouchStart = useRef<{ x: number; y: number } | null>(null);
  const aboutTouchCurrent = useRef<{ x: number; y: number } | null>(null);
  const lastBannerInteractionAt = useRef<number>(0);
  const mainSectionRef = useRef<HTMLElement | null>(null);
  const aboutSectionRef = useRef<HTMLElement | null>(null);
  const footerSectionRef = useRef<HTMLElement | null>(null);
  const infoBannerRef = useRef<HTMLDivElement | null>(null);
  const heroRef = useRef<HTMLElement | null>(null);
  const isFirstPageRender = useRef(true);
  const sortButtonRef = useRef<HTMLButtonElement | null>(null);
  const storePickerRootRef = useRef<HTMLDivElement | null>(null);
  const filterRequestSeq = useRef(0);
  const openingProductSlugRef = useRef<string | null>(null);
  const openingProductTimerRef = useRef<number | null>(null);
  const shouldApplyDefaultCategoriesOnBootRef = useRef<boolean>(false);
  const safeActiveAboutSlug =
    aboutSections.some((section) => section.slug === activeAboutTab)
      ? activeAboutTab
      : aboutSections[0]?.slug ?? "";

  const activeSection = useMemo(
    () =>
      aboutSections.find((section) => section.slug === safeActiveAboutSlug) ??
      aboutSections[0] ??
      null,
    [aboutSections, safeActiveAboutSlug]
  );

  useEffect(() => {
    const navigationEntry = performance
      .getEntriesByType("navigation")
      .at(0) as PerformanceNavigationTiming | undefined;
    const isReload = navigationEntry?.type === "reload";

    if (isReload) {
      removeSessionItem(SCROLL_KEY);
      window.scrollTo(0, 0);
    } else {
      const saved = getSessionItem(SCROLL_KEY);
      if (saved) {
        window.scrollTo(0, Number(saved));
      }
    }

    const params = new URLSearchParams(window.location.search);
    const categoriesFromUrl = params.getAll("category");
    const countriesFromUrl = params.getAll("country");
    const queryFromUrl = (params.get("q") || "").trim();
    const sortFromUrlRaw = (params.get("sort") || "").trim();
    const sortFromUrl: SortKey =
      sortFromUrlRaw === "price_asc" ||
      sortFromUrlRaw === "price_desc" ||
      sortFromUrlRaw === "new"
        ? sortFromUrlRaw
        : "";
    const productFromUrl = (params.get("product") || "").trim();
    const pageFromUrlRaw = Number.parseInt(params.get("page") || "1", 10);
    const pageFromUrl = Number.isFinite(pageFromUrlRaw) && pageFromUrlRaw > 0
      ? pageFromUrlRaw
      : 1;
    const pendingRaw = getSessionItem(PENDING_FILTERS_KEY);
    shouldApplyDefaultCategoriesOnBootRef.current =
      !pendingRaw &&
      countriesFromUrl.length === 0 &&
      !queryFromUrl &&
      !sortFromUrl &&
      pageFromUrl === 1;

    requestAnimationFrame(() => {
      setSelectedCategories(categoriesFromUrl);
      setSelectedCountries(countriesFromUrl);
      setSearchInput(queryFromUrl);
      setSearchQuery(queryFromUrl);
      setSortBy(sortFromUrl);
      setCurrentPage(pageFromUrl);

      setPageSize(readInitialPageSize());
      setIsPageSizeReady(true);
    });
    // Read pending filters only after hydration to avoid SSR/client mismatch.
    try {
      if (pendingRaw) {
        const pending = parseSessionJson<PendingFilters>(PENDING_FILTERS_KEY);
        if (!pending) {
          throw new Error("invalid pending filters payload");
        }
        requestAnimationFrame(() => {
          setSelectedCategories(Array.isArray(pending.category) ? pending.category : []);
          setSelectedCountries(Array.isArray(pending.country) ? pending.country : []);
          setCurrentPage(1);
        });
      }
      removeSessionItem(PENDING_FILTERS_KEY);
    } catch {
      // ignore storage errors
    }

    requestAnimationFrame(() => {
      if (productFromUrl) {
        setSessionItem(CATALOG_RETURN_URL_KEY, "/");
        removeSessionItem(MODAL_BACK_KEY);
        router.replace(`/p/${encodeURIComponent(productFromUrl)}`, {
          scroll: false,
        });
      }

      setIsBootstrapped(true);
    });

    return () => {
      setSessionItem(SCROLL_KEY, String(window.scrollY));
    };
  }, [router]);

  useEffect(() => {
    const applyFiltersFromEvent = (event: Event) => {
      const customEvent = event as CustomEvent<PendingFilters>;
      const payload = customEvent.detail;
      if (!payload) return;
      setIsProductsLoading(true);
      setSelectedCategories(Array.isArray(payload.category) ? payload.category : []);
      setSelectedCountries(Array.isArray(payload.country) ? payload.country : []);
      setCurrentPage(1);
      setFilterModal(null);
    };

    window.addEventListener("hanguk:apply-filters", applyFiltersFromEvent);
    return () => {
      window.removeEventListener("hanguk:apply-filters", applyFiltersFromEvent);
    };
  }, []);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 1024px)");
    const updateMode = () => setIsDesktopScrollbar(mediaQuery.matches);
    updateMode();
    mediaQuery.addEventListener("change", updateMode);
    return () => mediaQuery.removeEventListener("change", updateMode);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!isDesktopScrollbar) {
      setPageScrollbar({ top: 0, thumbTop: 0, thumbHeight: 0 });
      return;
    }

    const updateScrollbar = () => {
      const doc = document.documentElement;
      const scrollY = window.scrollY;
      const viewportHeight = window.innerHeight;
      const docHeight = Math.max(doc.scrollHeight, document.body.scrollHeight);

      const heroHeight = Math.max(0, Math.ceil(heroRef.current?.getBoundingClientRect().height ?? 0));
      const top = heroHeight;
      const trackHeight = Math.max(0, viewportHeight - top);
      if (trackHeight <= 0 || docHeight <= viewportHeight) {
        setPageScrollbar({ top, thumbTop: 0, thumbHeight: 0 });
        return;
      }

      const thumbHeight = Math.max(24, Math.round(trackHeight * (viewportHeight / docHeight)));
      const maxThumbTop = Math.max(trackHeight - thumbHeight, 0);
      const maxScrollY = Math.max(docHeight - viewportHeight, 1);
      const thumbTop = Math.round((scrollY / maxScrollY) * maxThumbTop);

      setPageScrollbar({ top, thumbTop, thumbHeight });
    };

    updateScrollbar();
    window.addEventListener("scroll", updateScrollbar, { passive: true });
    window.addEventListener("resize", updateScrollbar);

    return () => {
      window.removeEventListener("scroll", updateScrollbar);
      window.removeEventListener("resize", updateScrollbar);
    };
  }, [isDesktopScrollbar, isHeroLoading, banners.length, heroSection.image]);

  useEffect(() => {
    return () => {
      if (openingProductTimerRef.current !== null) {
        window.clearTimeout(openingProductTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (pathname.startsWith("/p/")) {
      return;
    }

    openingProductSlugRef.current = null;
    if (openingProductTimerRef.current !== null) {
      window.clearTimeout(openingProductTimerRef.current);
      openingProductTimerRef.current = null;
    }
  }, [pathname]);

  useEffect(() => {
    if (banners.length <= 1) {
      return;
    }

    const intervalId = window.setInterval(() => {
      if (Date.now() - lastBannerInteractionAt.current < BANNER_INTERACTION_COOLDOWN_MS) {
        return;
      }
      setActiveBanner((prev) => (prev + 1) % banners.length);
    }, BANNER_AUTOPLAY_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [banners.length]);

  useEffect(() => {
    if (hasInitialStaticData) {
      return;
    }

    const controller = new AbortController();
    let cancelled = false;

    const fetchContentBlocks = async () => {
      try {
        const [bannerResult, promoCardsResult, aboutResult, heroResult, siteResult] =
          await Promise.allSettled([
            apiFetchOr<Banner[]>("/banners/", [], {
              signal: controller.signal,
              cache: "no-store",
            }),
            apiFetchOr<unknown[]>("/promo-cards/", [], {
              signal: controller.signal,
              cache: "no-store",
            }),
            apiFetchOr<AboutSectionResponse>("/about-section/", { sections: [] }, {
              signal: controller.signal,
              cache: "no-store",
            }),
            apiFetchOr<HeroSection>("/hero/", { description: "", image: null }, {
              signal: controller.signal,
              cache: "no-store",
            }),
            getSiteSettingsRaw({
              signal: controller.signal,
            }),
          ]);

        if (cancelled) {
          return;
        }

        if (bannerResult.status === "fulfilled") {
          setBanners(Array.isArray(bannerResult.value) ? bannerResult.value : []);
        }
        if (promoCardsResult.status === "fulfilled") {
          setPromoCards(normalizePromoCards(promoCardsResult.value));
        }

        if (aboutResult.status === "fulfilled") {
          const normalized = normalizeAboutSections(aboutResult.value);
          setAboutSections(normalized);
          setActiveAboutTab((prev) => {
            if (prev && normalized.some((section) => section.slug === prev)) {
              return prev;
            }
            return normalized[0]?.slug ?? "";
          });
        }

        if (heroResult.status === "fulfilled") {
          setHeroSection({
            description:
              typeof heroResult.value?.description === "string"
                ? heroResult.value.description
                : "",
            image: typeof heroResult.value?.image === "string" ? heroResult.value.image : null,
          });
        }

        if (siteResult.status === "fulfilled") {
          setSiteSettings(normalizeSiteSettings(siteResult.value));
        }
      } finally {
        if (!cancelled) {
          setIsHeroLoading(false);
        }
      }
    };

    void fetchContentBlocks();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [hasInitialStaticData]);

  useEffect(() => {
    const activeSection = aboutSections.find((section) => section.slug === safeActiveAboutSlug);
    if (!activeSection || activeSection.section_type !== "location") return;
    if (!activeSection.map_script_url) return;

    const container = document.getElementById("yandex-about-map-frame");
    if (!container) return;

    container.innerHTML = "";

    const script = document.createElement("script");
    script.type = "text/javascript";
    script.charset = "utf-8";
    script.async = true;
    script.src = activeSection.map_script_url;
    container.appendChild(script);

    return () => {
      container.innerHTML = "";
    };
  }, [safeActiveAboutSlug, aboutSections]);

  useEffect(() => {
    setSelectedStoreId("");
    setDeliveryModalState(null);
  }, [siteSettings]);

  const shouldHidePrices = Boolean(siteSettings?.hide_prices);

  useEffect(() => {
    if (!shouldHidePrices) {
      return;
    }
    if (!sortBy) {
      return;
    }
    setSortBy("");
    setIsSortOpen(false);
  }, [shouldHidePrices, sortBy]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!isDesktopScrollbar) {
      document.documentElement.classList.remove("is-scrolling");
      return;
    }

    const root = document.documentElement;
    let timerId: number | null = null;

    const markScrolling = () => {
      root.classList.add("is-scrolling");
      if (timerId !== null) {
        window.clearTimeout(timerId);
      }
      timerId = window.setTimeout(() => {
        root.classList.remove("is-scrolling");
      }, 260);
    };

    window.addEventListener("scroll", markScrolling, { passive: true });
    window.addEventListener("wheel", markScrolling, { passive: true });
    window.addEventListener("touchmove", markScrolling, { passive: true });

    return () => {
      window.removeEventListener("scroll", markScrolling);
      window.removeEventListener("wheel", markScrolling);
      window.removeEventListener("touchmove", markScrolling);
      if (timerId !== null) {
        window.clearTimeout(timerId);
      }
      root.classList.remove("is-scrolling");
    };
  }, [isDesktopScrollbar]);

  useEffect(() => {
    if (!isBootstrapped || !siteSettings) {
      return;
    }
    if (!shouldApplyDefaultCategoriesOnBootRef.current) {
      return;
    }

    const defaults = siteSettings.default_category_slugs;
    setSelectedCategories(defaults);
    setSelectedCountries([]);
    setCurrentPage(1);
    shouldApplyDefaultCategoriesOnBootRef.current = false;
  }, [
    isBootstrapped,
    siteSettings,
  ]);

  useEffect(() => {
    const banner = infoBannerRef.current;
    if (!banner) return;

    const updateHeight = () => {
      const next = Math.ceil(banner.getBoundingClientRect().height);
      setInfoBannerHeight((prev) => (prev === next ? prev : next));
    };

    updateHeight();
    const observer = new ResizeObserver(updateHeight);
    observer.observe(banner);
    window.addEventListener("resize", updateHeight);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateHeight);
    };
  }, [banners.length]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 768px) and (orientation: landscape)");
    if (mediaQuery.matches) {
      setFilterModal(null);
    }

    const onChange = (event: MediaQueryListEvent) => {
      if (event.matches) {
        setFilterModal(null);
      }
    };

    mediaQuery.addEventListener("change", onChange);
    return () => mediaQuery.removeEventListener("change", onChange);
  }, []);

  const totalPages = Math.max(1, Math.ceil(totalProducts / Math.max(pageSize, 1)));
  const normalizedCurrentPage = Math.max(1, currentPage);
  const safeCurrentPage = hasLoadedProductsOnce
    ? Math.min(normalizedCurrentPage, totalPages)
    : normalizedCurrentPage;

  useEffect(() => {
    if (!isBootstrapped) {
      return;
    }
    if (!isPageSizeReady) {
      return;
    }

    const controller = new AbortController();
    const requestId = ++filterRequestSeq.current;
    const requestPage = Math.max(1, safeCurrentPage);
    const filterQuery = new URLSearchParams();

    selectedCategories.forEach((slug) => filterQuery.append("category", slug));
    selectedCountries.forEach((slug) => filterQuery.append("country", slug));
    if (searchQuery) {
      filterQuery.set("q", searchQuery);
    }

    const productsQuery = new URLSearchParams(filterQuery);
    if (sortBy && !shouldHidePrices) {
      productsQuery.set("sort", sortBy);
    }
    productsQuery.set("page", String(requestPage));
    productsQuery.set("page_size", String(pageSize));

    const productsSuffix = productsQuery.toString() ? `?${productsQuery.toString()}` : "";
    const filterSuffix = filterQuery.toString() ? `?${filterQuery.toString()}` : "";

    const fetchCatalogData = async () => {
      const [productsResult, filtersResult] = await Promise.allSettled([
        apiFetchOr<PaginatedResponse<Product>>(
          `/products/${productsSuffix}`,
          {
            count: 0,
            next: null,
            previous: null,
            results: [],
          },
          {
            signal: controller.signal,
            cache: "no-store",
          }
        ),
        apiFetchOr<FilterOptionsResponse>(
          `/filter-options/${filterSuffix}`,
          {
            categories: [],
            countries: [],
            all_categories_image: null,
            all_countries_image: null,
          },
          {
            signal: controller.signal,
            cache: "no-store",
          }
        ),
      ]);

      if (requestId !== filterRequestSeq.current) {
        return;
      }

      if (productsResult.status === "fulfilled") {
        const productData = productsResult.value;
        const count = Number.isFinite(productData?.count) ? productData.count : 0;
        const nextTotalPages = Math.max(1, Math.ceil(count / Math.max(pageSize, 1)));
        if (count > 0 && requestPage > nextTotalPages) {
          setCurrentPage(nextTotalPages);
          return;
        }

        setTotalProducts(count);
        setHasLoadedProductsOnce(true);

        if (Array.isArray(productData?.results)) {
          setProducts(productData.results);
        } else if (Array.isArray(productData)) {
          setProducts(productData);
          setTotalProducts(productData.length);
        } else {
          setProducts([]);
        }
      }

      if (filtersResult.status === "fulfilled") {
        const filterData = filtersResult.value;
        const normalizedCategories = normalizeFilterOptions(filterData?.categories);
        const normalizedCountries = normalizeFilterOptions(filterData?.countries);

        setFilterOptions({
          categories: normalizedCategories,
          countries: normalizedCountries,
          all_categories_image: filterData?.all_categories_image ?? null,
          all_countries_image: filterData?.all_countries_image ?? null,
        });

        const categorySlugs = new Set(normalizedCategories.map((item) => item.slug));
        const countrySlugs = new Set(normalizedCountries.map((item) => item.slug));

        setSelectedCategories((prev) => reconcileSelection(prev, categorySlugs));
        setSelectedCountries((prev) => reconcileSelection(prev, countrySlugs));
      }

      setIsProductsLoading(false);
    };

    void fetchCatalogData().catch((error: unknown) => {
      if ((error as { name?: string })?.name === "AbortError") {
        return;
      }
      if (requestId === filterRequestSeq.current) {
        setIsProductsLoading(false);
      }
    });

    return () => controller.abort();
  }, [selectedCategories, selectedCountries, searchQuery, sortBy, safeCurrentPage, pageSize, isPageSizeReady, filtersRefreshToken, isBootstrapped, shouldHidePrices]);

  const handleTouchStart = (event: React.TouchEvent<HTMLDivElement>) => {
    touchStartX.current = event.touches[0]?.clientX ?? null;
    touchCurrentX.current = touchStartX.current;
  };

  const handleTouchMove = (event: React.TouchEvent<HTMLDivElement>) => {
    touchCurrentX.current = event.touches[0]?.clientX ?? touchCurrentX.current;
  };

  const handleTouchEnd = () => {
    if (touchStartX.current === null || touchCurrentX.current === null) return;
    const delta = touchStartX.current - touchCurrentX.current;
    const threshold = 40;

    if (Math.abs(delta) > threshold && banners.length > 1) {
      setActiveBanner((prev) =>
        delta > 0
          ? (prev + 1) % banners.length
          : (prev - 1 + banners.length) % banners.length
      );
      lastBannerInteractionAt.current = Date.now();
    }
    touchStartX.current = null;
    touchCurrentX.current = null;
  };

  const handleAboutTouchStart = (event: React.TouchEvent<HTMLElement>) => {
    if (aboutSections.length < 2) return;
    const touch = event.touches[0];
    if (!touch) return;
    const point = { x: touch.clientX, y: touch.clientY };
    aboutTouchStart.current = point;
    aboutTouchCurrent.current = point;
  };

  const handleAboutTouchMove = (event: React.TouchEvent<HTMLElement>) => {
    const touch = event.touches[0];
    if (!touch || !aboutTouchStart.current) return;
    aboutTouchCurrent.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleAboutTouchEnd = () => {
    if (!aboutTouchStart.current || !aboutTouchCurrent.current) return;

    const deltaX = aboutTouchStart.current.x - aboutTouchCurrent.current.x;
    const deltaY = Math.abs(aboutTouchStart.current.y - aboutTouchCurrent.current.y);
    const swipeThreshold = 42;

    if (Math.abs(deltaX) > swipeThreshold && Math.abs(deltaX) > deltaY) {
      const currentIndex = aboutSections.findIndex(
        (section) => section.slug === safeActiveAboutSlug
      );

      if (currentIndex >= 0) {
        const targetIndex =
          deltaX > 0
            ? Math.min(currentIndex + 1, aboutSections.length - 1)
            : Math.max(currentIndex - 1, 0);
        const target = aboutSections[targetIndex];
        if (target && target.slug !== safeActiveAboutSlug) {
          setActiveAboutTab(target.slug);
        }
      }
    }

    aboutTouchStart.current = null;
    aboutTouchCurrent.current = null;
  };

  const handleProductClick = (
    event: React.MouseEvent<HTMLAnchorElement>,
    slug: string,
    product?: Product
  ) => {
    event.preventDefault();

    if (openingProductSlugRef.current === slug) {
      return;
    }
    openingProductSlugRef.current = slug;

    if (openingProductTimerRef.current !== null) {
      window.clearTimeout(openingProductTimerRef.current);
    }
    openingProductTimerRef.current = window.setTimeout(() => {
      openingProductSlugRef.current = null;
      openingProductTimerRef.current = null;
    }, 300);

    setSessionItem(SCROLL_KEY, String(window.scrollY));
    setSessionItem(
      CATALOG_RETURN_URL_KEY,
      buildCatalogReturnUrl()
    );
    setSessionItem(MODAL_BACK_KEY, "1");

    if (product) {
      setSessionJson(makePreviewKey(product.slug), product);
    }

    router.push(`/p/${encodeURIComponent(slug)}`, { scroll: false });
  };

  const toggleCategory = (option: FilterOption) => {
    if (!option.enabled && !option.selected) {
      return;
    }

    setIsProductsLoading(true);
    setSelectedCategories((prev) =>
      prev.includes(option.slug)
        ? prev.filter((item) => item !== option.slug)
        : [...prev, option.slug]
    );
    setCurrentPage(1);
  };

  const toggleCountry = (option: FilterOption) => {
    if (!option.enabled && !option.selected) {
      return;
    }

    setIsProductsLoading(true);
    setSelectedCountries((prev) =>
      prev.includes(option.slug)
        ? prev.filter((item) => item !== option.slug)
        : [...prev, option.slug]
    );
    setCurrentPage(1);
  };

  const resetCategories = () => {
    setIsProductsLoading(true);
    setSelectedCategories([]);
    setCurrentPage(1);
  };
  const resetCountries = () => {
    setIsProductsLoading(true);
    setSelectedCountries([]);
    setCurrentPage(1);
  };

  const closeFilterModal = useCallback(() => {
    setFilterModal(null);
  }, []);

  const refreshFilterOptions = () => {
    setFiltersRefreshToken((prev) => prev + 1);
  };

  const openCategoryModal = () => {
    setIsSortOpen(false);
    refreshFilterOptions();
    setFilterModal("category");
  };

  const openCountryModal = () => {
    setIsSortOpen(false);
    refreshFilterOptions();
    setFilterModal("country");
  };

  const syncSortPopupPosition = () => {
    const button = sortButtonRef.current;
    if (!button) return;
    const rect = button.getBoundingClientRect();
    setSortPopupPosition({
      top: rect.bottom + 8,
      left: rect.left,
      width: rect.width,
    });
  };

  const openSortPopup = () => {
    if (isSortOpen) {
      setIsSortOpen(false);
      return;
    }
    syncSortPopupPosition();
    setIsSortOpen(true);
  };

  const closeSortPopup = () => {
    setIsSortOpen(false);
  };

  const closeStorePicker = useCallback(() => {
    setIsStorePickerOpen(false);
  }, []);

  const openStorePicker = useCallback(() => {
    setIsStorePickerOpen((prev) => !prev);
  }, []);

  const scrollToSection = (section: "menu" | "about" | "contacts") => {
    if (section === "menu") {
      mainSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    if (section === "about") {
      aboutSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    footerSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const applySort = (value: SortKey) => {
    setIsProductsLoading(true);
    setSortBy(value);
    setCurrentPage(1);
    setIsSortOpen(false);
  };

  const applySearch = () => {
    setIsProductsLoading(true);
    setSearchQuery(searchInput.trim());
    setCurrentPage(1);
    setIsSortOpen(false);
  };

  const resetSearch = () => {
    setIsProductsLoading(true);
    setSearchInput("");
    setSearchQuery("");
    setCurrentPage(1);
    setIsSortOpen(false);
  };

  const handleSearchKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    applySearch();
  };

  useEffect(() => {
    if (!isSortOpen) return;

    const handleViewportChange = () => syncSortPopupPosition();
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsSortOpen(false);
      }
    };

    window.addEventListener("resize", handleViewportChange);
    window.addEventListener("scroll", handleViewportChange, true);
    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("resize", handleViewportChange);
      window.removeEventListener("scroll", handleViewportChange, true);
      window.removeEventListener("keydown", handleEscape);
    };
  }, [isSortOpen]);

  useEffect(() => {
    if (!isStorePickerOpen) return;

    const handleOutsidePointer = (event: PointerEvent) => {
      const target = event.target as Node | null;
      if (target && storePickerRootRef.current?.contains(target)) {
        return;
      }
      setIsStorePickerOpen(false);
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsStorePickerOpen(false);
      }
    };

    window.addEventListener("pointerdown", handleOutsidePointer, true);
    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("pointerdown", handleOutsidePointer, true);
      window.removeEventListener("keydown", handleEscape);
    };
  }, [isStorePickerOpen]);

  useEffect(() => {
    if (!deliveryModalState?.delivery.map_script_url) {
      return;
    }

    const container = document.getElementById("yandex-delivery-map-frame");
    if (!container) return;

    container.innerHTML = "";
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.charset = "utf-8";
    script.async = true;
    script.src = deliveryModalState.delivery.map_script_url;
    container.appendChild(script);

    return () => {
      container.innerHTML = "";
    };
  }, [deliveryModalState]);
  const bannerCount = banners.length;
  const isCategoryModal = filterModal === "category";
  const modalTitle = isCategoryModal ? "Выберите категории:" : "Выберите страны:";
  const modalOptions = isCategoryModal
    ? filterOptions.categories
    : filterOptions.countries;
  const isAllSelected = isCategoryModal
    ? selectedCategories.length === 0
    : selectedCountries.length === 0;
  const allFilterImage = isCategoryModal
    ? filterOptions.all_categories_image
    : filterOptions.all_countries_image;
  useEffect(() => {
    if (!isBootstrapped) {
      return;
    }
    if (pathname.startsWith("/p/")) {
      return;
    }
    if (!isPageSizeReady) return;

    const params = new URLSearchParams();
    selectedCategories.forEach((slug) => params.append("category", slug));
    selectedCountries.forEach((slug) => params.append("country", slug));
    if (searchQuery) {
      params.set("q", searchQuery);
    }
    if (sortBy && !shouldHidePrices) {
      params.set("sort", sortBy);
    }
    params.set("page", String(safeCurrentPage));

    const query = params.toString();
    const nextUrl = query
      ? `${window.location.pathname}?${query}`
      : window.location.pathname;
    const currentUrl = `${window.location.pathname}${window.location.search}`;

    if (currentUrl === nextUrl) {
      return;
    }

    router.replace(nextUrl, { scroll: false });
  }, [selectedCategories, selectedCountries, searchQuery, sortBy, safeCurrentPage, isPageSizeReady, pathname, isBootstrapped, router, shouldHidePrices]);

  useEffect(() => {
    if (pathname.startsWith("/p/")) {
      return;
    }

    // Safety net: fully reset body lock styles after closing intercepted modal route.
    const lockedTop = document.body.style.top;
    const shouldRestoreScroll = document.body.style.position === "fixed" && lockedTop;
    document.body.style.overflow = "";
    document.body.style.touchAction = "";
    document.body.style.position = "";
    document.body.style.top = "";
    document.body.style.left = "";
    document.body.style.right = "";
    document.body.style.width = "";

    if (shouldRestoreScroll) {
      const offset = Number.parseInt(lockedTop.replace("-", ""), 10);
      if (Number.isFinite(offset)) {
        window.scrollTo(0, offset);
      }
    }
  }, [pathname]);

  useEffect(() => {
    if (!pathname.startsWith("/p/")) {
      return;
    }

    requestAnimationFrame(() => {
      setIsSortOpen(false);
      setFilterModal(null);
    });
  }, [pathname]);

  useEffect(() => {
    if (isFirstPageRender.current) {
      isFirstPageRender.current = false;
      return;
    }

    mainSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [safeCurrentPage]);

  const paginationItems: Array<number | string> = useMemo(() => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, index) => index + 1);
    }

    if (safeCurrentPage <= 4) {
      return [1, 2, 3, 4, 5, "ellipsis-right", totalPages];
    }

    if (safeCurrentPage >= totalPages - 3) {
      return [
        1,
        "ellipsis-left",
        totalPages - 4,
        totalPages - 3,
        totalPages - 2,
        totalPages - 1,
        totalPages,
      ];
    }

    return [
      1,
      "ellipsis-left",
      safeCurrentPage - 1,
      safeCurrentPage,
      safeCurrentPage + 1,
      "ellipsis-right",
      totalPages,
    ];
  }, [safeCurrentPage, totalPages]);

  const skeletonItems = useMemo(
    () => Array.from({ length: pageSize }, (_, index) => index),
    [pageSize]
  );

  const heroImage = resolveMediaUrl(heroSection.image);
  const heroDescription = heroSection.description.trim();
  const shouldShowHero = Boolean(heroImage);
  const socialLinkMap: Partial<Record<SiteSocial["platform"], string>> = {};
  for (const item of siteSettings?.social_links ?? []) {
    if (item.url) {
      socialLinkMap[item.platform] = item.url;
    }
  }
  const footerSocialLinks = SOCIAL_ORDER
    .map((platform) => ({
      platform,
      url: socialLinkMap[platform] || "",
    }))
    .filter((item) => item.url) as SiteSocial[];
  const stores = siteSettings?.stores ?? [];
  const footerAddresses = siteSettings?.addresses ?? [];
  const footerContacts = siteSettings?.contacts ?? [];
  const footerRows = stores.length
    ? stores
        .map((store) => ({ address: store.address.trim(), phone: store.phone.trim() }))
        .filter((row) => row.address || row.phone)
    : Array.from({ length: Math.max(footerAddresses.length, footerContacts.length) }, (_, index) => ({
        address: (footerAddresses[index]?.text || "").trim(),
        phone: (footerContacts[index]?.text || "").trim(),
      })).filter((row) => row.address || row.phone);
  const selectedStore =
    selectedStoreId === ""
      ? null
      : stores.find((store) => store.id === selectedStoreId) ?? null;
  const selectedDeliveryServices = selectedStore?.deliveries ?? [];
  const handleOpenDeliveryModal = useCallback(
    (delivery: SiteStoreDelivery) => {
      if (!selectedStore) {
        return;
      }
      setDeliveryModalState({ store: selectedStore, delivery });
    },
    [selectedStore]
  );
  const selectedDeliveryMeta = deliveryModalState
    ? DELIVERY_SERVICE_META[deliveryModalState.delivery.service_type]
    : null;
  const modalStorePhoneHref = deliveryModalState?.store.phone
    ? toTelHref(deliveryModalState.store.phone)
    : "";

  const aboutCover = useMemo(() => {
    if (!activeSection) {
      return "/static/images/placeholder.png";
    }
    const source = resolveMediaUrl(activeSection.image);
    return source || "/static/images/placeholder.png";
  }, [activeSection]);

  return (
    <>
      <main className="page">
        {isHeroLoading ? (
          <section className="hero hero-skeleton" aria-label="Hero loading" ref={heroRef}>
          </section>
        ) : shouldShowHero ? (
          <section
            className="hero"
            ref={heroRef}
            aria-label="Hero"
            style={{
              backgroundImage: `linear-gradient(180deg, rgba(34, 34, 34, 0) 0%, rgba(34, 34, 34, 1) 100%), url(${heroImage})`,
            }}
          >
            {heroDescription ? <p className="hero-text">{heroDescription}</p> : null}
          </section>
        ) : null}

        <section className="info" aria-label="Info">
          <div className="info-container">
            <header className="info-header">
              <div className="info-actions">
                <button
                  className="btn info-nav-btn"
                  type="button"
                  onClick={() => scrollToSection("menu")}
                >
                  меню
                </button>
                <button
                  className="btn info-nav-btn"
                  type="button"
                  onClick={() => scrollToSection("about")}
                >
                  о нас
                </button>
                <button
                  className="btn info-nav-btn"
                  type="button"
                  onClick={() => scrollToSection("contacts")}
                >
                  контакты
                </button>
              </div>
            </header>

            <div
              className="info-content-grid"
              style={
                {
                  "--info-banner-height": `${Math.max(infoBannerHeight, 0)}px`,
                } as React.CSSProperties
              }
            >
              {isHeroLoading ? (
                <div className="info-content-col info-content-col-banner">
                  <div className="info-banner info-banner-skeleton" aria-hidden="true" />
                </div>
              ) : banners.length || promoCards.length || stores.length ? (
                <div className="info-content-col info-content-col-banner">
                  {banners.length ? (
                    <div
                      className="info-banner"
                      ref={infoBannerRef}
                      onTouchStart={handleTouchStart}
                      onTouchMove={handleTouchMove}
                      onTouchEnd={handleTouchEnd}
                    >
                      <div
                        className="banner-track"
                        style={{ transform: `translateX(-${activeBanner * 100}%)` }}
                      >
                        {banners.map((banner) => {
                          const hasBannerLink = Boolean(banner.link_url?.trim());
                          const bannerImage =
                            resolveMediaUrl(banner.image_thumb) ||
                            resolveMediaUrl(banner.image);
                          const bannerBackgroundImage = resolveMediaUrl(
                            banner.background_image
                          );
                          const bannerOpacity =
                            typeof banner.background_opacity === "string"
                              ? Number.parseFloat(banner.background_opacity)
                              : Number(banner.background_opacity ?? 60);
                          const bannerAlpha = Number.isFinite(bannerOpacity)
                            ? bannerOpacity > 1
                              ? bannerOpacity / 100
                              : bannerOpacity
                            : 0.6;
                          const bannerColor = hexToRgba(
                            banner.background_color || "#0B6BA7",
                            bannerAlpha
                          );
                          const bannerBody = (
                            <>
                              <div className="banner-content">
                                <h2 className="banner-title">
                                  {banner.title}
                                </h2>
                                <p className="banner-desc">{banner.description}</p>
                              </div>
                              <div
                                className="banner-media"
                                role="img"
                                aria-label={banner.title}
                                style={{
                                  backgroundImage: bannerImage
                                    ? `url(${bannerImage})`
                                    : "none",
                                }}
                              />
                            </>
                          );

                          if (hasBannerLink) {
                            return (
                              <a
                                className="banner-slide"
                                key={banner.id}
                                href={banner.link_url}
                                target="_blank"
                                rel="noreferrer"
                                style={{
                                  backgroundImage: bannerBackgroundImage
                                    ? `url(${bannerBackgroundImage})`
                                    : "none",
                                  backgroundColor: bannerColor ?? "transparent",
                                }}
                              >
                                {bannerBody}
                              </a>
                            );
                          }

                          return (
                            <article
                              className="banner-slide"
                              key={banner.id}
                              style={{
                                backgroundImage: bannerBackgroundImage
                                  ? `url(${bannerBackgroundImage})`
                                  : "none",
                                backgroundColor: bannerColor ?? "transparent",
                              }}
                            >
                              {bannerBody}
                            </article>
                          );
                        })}
                      </div>

                      {bannerCount > 1 ? (
                        <div className="banner-pagination" aria-label="Pagination">
                          {Array.from({ length: bannerCount }, (_, index) => (
                            <button
                              key={`dot-${index}`}
                              type="button"
                              className={`dot ${index === activeBanner ? "active" : ""}`}
                              aria-label={`Показать баннер ${index + 1}`}
                              onClick={() => {
                                setActiveBanner(index);
                                lastBannerInteractionAt.current = Date.now();
                              }}
                            />
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {isHeroLoading ? (
                <div className="info-content-col info-content-col-right" aria-hidden="true">
                  <section className="promo-cards promo-cards-skeleton">
                    {Array.from({ length: 4 }, (_, index) => (
                      <div key={`promo-skeleton-${index}`} className="promo-card promo-card-skeleton" />
                    ))}
                  </section>
                  <section className="delivery-selector-section delivery-selector-skeleton">
                    <div className="delivery-selector-card">
                      <div className="delivery-address-row delivery-address-row-skeleton" />
                    </div>
                  </section>
                </div>
              ) : promoCards.length || stores.length ? (
                <div className="info-content-col info-content-col-right">
                  {promoCards.length ? (
                    <section className="promo-cards" aria-label="Подборки">
                      {promoCards.map((card) => {
                        const image = resolveMediaUrl(card.image) || "/static/images/placeholder.png";
                        const isLinkCard = card.scenario === "link" && card.link_url.trim();

                        if (isLinkCard) {
                          return (
                            <a
                              key={`promo-card-${card.id}`}
                              className="promo-card"
                              href={card.link_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              <img className="promo-card-image" src={image} alt="" />
                            </a>
                          );
                        }

                        return (
                          <button
                            key={`promo-card-${card.id}`}
                            type="button"
                            className="promo-card promo-card-button"
                            onClick={() => {
                              if (!card.products?.length) return;
                              setPromoProductsModal({ products: card.products });
                            }}
                          >
                            <img className="promo-card-image" src={image} alt="" />
                          </button>
                        );
                      })}
                    </section>
                  ) : null}

                  {stores.length ? (
                    <section className="delivery-selector-section" aria-label="Доставка по адресу">
                      <div
                        className={`delivery-selector-card ${
                          selectedDeliveryServices.length ? "has-services" : ""
                        }`}
                      >
                        <div className="delivery-address-picker" ref={storePickerRootRef}>
                          <div className="delivery-address-row">
                            <img
                              className="delivery-address-icon"
                              src="/static/icons/location.svg"
                              alt=""
                              aria-hidden="true"
                            />
                            <button
                              type="button"
                              className="delivery-address-trigger"
                              onClick={openStorePicker}
                              aria-haspopup="listbox"
                              aria-expanded={isStorePickerOpen}
                              aria-controls="delivery-store-picker"
                            >
                              <span className="delivery-address-trigger-text">
                                {selectedStore?.address || "Выберите адрес доставки"}
                              </span>
                              <img
                                className={`delivery-address-trigger-arrow ${
                                  isStorePickerOpen ? "is-open" : ""
                                }`}
                                src="/static/icons/arrow.svg"
                                alt=""
                                aria-hidden="true"
                              />
                            </button>
                          </div>
                          {isStorePickerOpen ? (
                            <div
                              id="delivery-store-picker"
                              className="delivery-address-popup is-open"
                              role="listbox"
                              aria-label="Адреса магазинов"
                            >
                              {stores.map((store) => (
                                <button
                                  key={`store-picker-${store.id}`}
                                  type="button"
                                  className={`delivery-address-option ${
                                    selectedStore?.id === store.id ? "is-active" : ""
                                  }`}
                                  role="option"
                                  aria-selected={selectedStore?.id === store.id}
                                  onClick={() => {
                                    setSelectedStoreId(store.id);
                                    closeStorePicker();
                                  }}
                                >
                                  {store.address}
                                </button>
                              ))}
                            </div>
                          ) : null}
                        </div>

                        {selectedDeliveryServices.length ? (
                          <div className="delivery-services-grid" aria-label="Сервисы доставки">
                            {selectedDeliveryServices.map((delivery) => (
                              <button
                                type="button"
                                className={`delivery-service-chip delivery-service-chip--${delivery.service_type}`}
                                key={delivery.id}
                                onClick={() => handleOpenDeliveryModal(delivery)}
                              >
                                <img
                                  className="delivery-service-icon"
                                  src={DELIVERY_SERVICE_META[delivery.service_type].icon}
                                  alt={DELIVERY_SERVICE_META[delivery.service_type].label}
                                />
                                <span>{DELIVERY_SERVICE_META[delivery.service_type].label}</span>
                              </button>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </section>
                  ) : null}
                </div>
              ) : null}

            </div>
          </div>
        </section>
        {isDesktopScrollbar && pageScrollbar.thumbHeight > 0 ? (
          <div
            className="page-scrollbar"
            aria-hidden="true"
            style={
              {
                "--page-scrollbar-top": `${pageScrollbar.top}px`,
                "--page-scrollbar-thumb-top": `${pageScrollbar.thumbTop}px`,
                "--page-scrollbar-thumb-height": `${pageScrollbar.thumbHeight}px`,
              } as React.CSSProperties
            }
          >
            <span className="page-scrollbar-thumb" />
          </div>
        ) : null}

        <section className="main" aria-label="Main" ref={mainSectionRef}>
          <div className="main-container">
            <div className="main-layout">
              <aside className="desktop-filter-sidebar" aria-label="Фильтры каталога">
                <div className="desktop-filter-panel">
                  <div className="desktop-filter-group">
                    <h3 className="desktop-filter-title">Категории</h3>
                    <div className="filter-grid desktop-filter-grid">
                      <button
                        type="button"
                        className={`filter-cell ${selectedCategories.length === 0 ? "is-selected" : ""}`}
                        onClick={resetCategories}
                      >
                        <span className="filter-cell-image-wrap">
                          <img
                            className="filter-cell-image"
                            src={
                              resolveMediaUrl(filterOptions.all_categories_image) ||
                              "/static/images/placeholder.png"
                            }
                            alt=""
                          />
                        </span>
                        <span className="filter-cell-label">Все категории</span>
                      </button>
                      {filterOptions.categories.map((option) => {
                        const isSelected = selectedCategories.includes(option.slug);
                        return (
                          <button
                            key={option.id}
                            type="button"
                            className={`filter-cell ${isSelected ? "is-selected" : ""} ${
                              !option.enabled && !isSelected ? "is-disabled" : ""
                            }`}
                            onClick={() => toggleCategory(option)}
                          >
                            <span className="filter-cell-image-wrap">
                              <img
                                className="filter-cell-image"
                                src={
                                  resolveMediaUrl(option.image) ||
                                  "/static/images/placeholder.png"
                                }
                                alt={option.title}
                              />
                            </span>
                            <span className="filter-cell-label">{option.title}</span>
                            {!shouldHidePrices && option.discount_badge ? (
                              <span className="filter-cell-discount">{option.discount_badge}</span>
                            ) : null}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="desktop-filter-group">
                    <h3 className="desktop-filter-title">Страны</h3>
                    <div className="filter-grid desktop-filter-grid">
                      <button
                        type="button"
                        className={`filter-cell ${selectedCountries.length === 0 ? "is-selected" : ""}`}
                        onClick={resetCountries}
                      >
                        <span className="filter-cell-image-wrap">
                          <img
                            className="filter-cell-image"
                            src={
                              resolveMediaUrl(filterOptions.all_countries_image) ||
                              "/static/images/placeholder.png"
                            }
                            alt=""
                          />
                        </span>
                        <span className="filter-cell-label">Все страны</span>
                      </button>
                      {filterOptions.countries.map((option) => {
                        const isSelected = selectedCountries.includes(option.slug);
                        return (
                          <button
                            key={option.id}
                            type="button"
                            className={`filter-cell ${isSelected ? "is-selected" : ""} ${
                              !option.enabled && !isSelected ? "is-disabled" : ""
                            }`}
                            onClick={() => toggleCountry(option)}
                          >
                            <span className="filter-cell-image-wrap">
                              <img
                                className="filter-cell-image"
                                src={
                                  resolveMediaUrl(option.image) ||
                                  "/static/images/placeholder.png"
                                }
                                alt={option.title}
                              />
                            </span>
                            <span className="filter-cell-label">{option.title}</span>
                            {!shouldHidePrices && option.discount_badge ? (
                              <span className="filter-cell-discount">{option.discount_badge}</span>
                            ) : null}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </aside>

              <div className="main-content">
                <div className="main-header">
                  <div
                    className={`search-row ${shouldHidePrices ? "is-sort-hidden" : ""}`}
                    aria-label="Search"
                  >
                    <label className="search-field">
                      <input
                        className="search-input"
                        type="text"
                        placeholder="Поиск по товарам"
                        value={searchInput}
                        onChange={(event) => setSearchInput(event.target.value)}
                        onKeyDown={handleSearchKeyDown}
                      />
                      {searchQuery ? (
                        <button
                          className="search-action"
                          type="button"
                          onClick={resetSearch}
                          aria-label="Сбросить поиск"
                        >
                          <img
                            className="search-action-icon"
                            src="/static/icons/close.svg"
                            alt=""
                          />
                        </button>
                      ) : (
                        <button
                          className="search-action"
                          type="button"
                          onClick={applySearch}
                          aria-label="Искать"
                        >
                          <img
                            className="search-action-icon"
                            src="/static/icons/search.svg"
                            alt=""
                          />
                        </button>
                      )}
                    </label>
                    {!shouldHidePrices ? (
                      <button
                        ref={sortButtonRef}
                        className={`sort-button ${isSortOpen ? "is-open" : ""}`}
                        type="button"
                        onClick={openSortPopup}
                      >
                        <img
                          className="sort-icon"
                          src="/static/icons/sort.svg"
                          alt=""
                        />
                        <span>сортировка</span>
                      </button>
                    ) : null}
                  </div>

                  <div className="quick-filters" aria-label="Quick filters">
                    <button
                      className={`btn btn-filter ${selectedCategories.length ? "is-selected" : ""}`}
                      type="button"
                      onClick={openCategoryModal}
                    >
                      <img
                        className="btn-icon"
                        src="/static/icons/categories.svg"
                        alt=""
                      />
                      {selectedCategories.length
                        ? `Категории (${selectedCategories.length})`
                        : "Категории"}
                    </button>
                    <button
                      className={`btn btn-filter ${selectedCountries.length ? "is-selected" : ""}`}
                      type="button"
                      onClick={openCountryModal}
                    >
                      <img
                        className="btn-icon"
                        src="/static/icons/countries.svg"
                        alt=""
                      />
                      {selectedCountries.length
                        ? `Страны (${selectedCountries.length})`
                        : "Страны"}
                    </button>
                  </div>
                </div>

                <div className="product-grid" aria-label="Products">
                  {isProductsLoading ? (
                    skeletonItems.map((item) => (
                      <div className="product-card product-card-skeleton" key={`skeleton-${item}`}>
                        <div className="product-media">
                          <div className="product-image-skeleton" />
                        </div>
                        <div className="product-info">
                          <div className="product-title-skeleton" />
                          <div className="product-meta">
                            <div className="product-price-skeleton" />
                          </div>
                        </div>
                      </div>
                    ))
                  ) : products.length === 0 && searchQuery ? (
                    <div className="catalog-empty" role="status" aria-live="polite">
                      <img
                        className="catalog-empty-image"
                        src="/static/images/not-found.png"
                        alt="Ничего не найдено"
                      />
                      <p className="catalog-empty-text">
                        Ничего не найдено, попробуй найти что-то ещё
                      </p>
                    </div>
                  ) : (
                    products.map((product) => (
                      <Link
                        className="product-card"
                        key={product.id}
                        href={`/p/${product.slug}`}
                        scroll={false}
                        onClick={(event) =>
                          handleProductClick(event, product.slug, product)
                        }
                      >
                        <div className="product-media">
                          <div className="product-badges">
                            {product.is_new ? (
                              <span className="product-badge">новинка</span>
                            ) : null}
                            {!shouldHidePrices && product.has_discount && product.discount_label ? (
                              <span className="product-badge product-badge-discount">
                                {product.discount_label}
                              </span>
                            ) : null}
                          </div>
                          {product.photo ? (
                            <img
                              className="product-image"
                              src={resolveMediaUrl(product.photo) ?? ""}
                              alt={product.title}
                              loading="lazy"
                              decoding="async"
                            />
                          ) : null}
                        </div>
                        <div className="product-info">
                          <h4 className="product-title">{product.title}</h4>
                          <div className="product-meta">
                            {!shouldHidePrices ? (
                              product.has_discount && product.discounted_price ? (
                                <span className="product-price-wrap">
                                  <span className="product-price product-price-old">
                                    {formatPrice(product.original_price || product.price)}
                                  </span>
                                  <span className="product-price product-price-discount">
                                    {formatPrice(product.discounted_price)}
                                  </span>
                                </span>
                              ) : (
                                <span className="product-price">
                                  {formatPrice(product.price)}
                                </span>
                              )
                            ) : null}
                            {product.spicy > 0 ? (
                              <div className="product-spicy" aria-label="Spicy">
                                {Array.from({ length: product.spicy }, (_, index) => (
                                  <img
                                    key={`${product.id}-spicy-${index}`}
                                    className="spicy-icon is-active"
                                    src="/static/icons/spicy.svg"
                                    alt=""
                                  />
                                ))}
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </Link>
                    ))
                  )}
                </div>

                {totalPages > 1 ? (
                  <div className="catalog-pagination" aria-label="Pagination" role="navigation">
                    {paginationItems.map((item, index) =>
                      typeof item === "number" ? (
                        <button
                          key={`page-${item}`}
                          type="button"
                          className={`catalog-page-btn ${item === safeCurrentPage ? "is-active" : ""}`}
                          onClick={() => {
                            setIsProductsLoading(true);
                            setCurrentPage(item);
                          }}
                        >
                          {item}
                        </button>
                      ) : (
                        <button
                          key={`ellipsis-${item}-${index}`}
                          type="button"
                          className="catalog-page-btn is-ellipsis"
                          disabled
                          aria-hidden="true"
                        >
                          ...
                        </button>
                      )
                    )}
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </section>

        {activeSection ? (
          <section className="about-section" aria-label="About section" ref={aboutSectionRef}>
            <div className="main-container">
              <div className="about-frame">
                <div
                  className="about-block-inner"
                  onTouchStart={handleAboutTouchStart}
                  onTouchMove={handleAboutTouchMove}
                  onTouchEnd={handleAboutTouchEnd}
                >
                  {activeSection.section_type === "location" ? (
                    <div className="about-content-frame is-map">
                      <div id="yandex-about-map-frame" className="about-map-frame" />
                    </div>
                  ) : (
                    <div
                      className="about-content-frame"
                      style={{ backgroundImage: `url(${aboutCover})` }}
                      role="img"
                      aria-label={activeSection.title}
                    />
                  )}

                  <div className="about-info-tabs">
                    <div className="modal-tabs about-tabs-row" role="tablist" aria-label="About tabs">
                      {aboutSections.map((section) => (
                        <button
                          key={section.id}
                          className={`tab ${safeActiveAboutSlug === section.slug ? "is-active" : ""}`}
                          type="button"
                          onClick={() => setActiveAboutTab(section.slug)}
                        >
                          {section.title}
                        </button>
                      ))}
                    </div>

                    <div className="modal-content about-scroll-area">
                      {activeSection.description ? (
                        <p className="about-text">{activeSection.description}</p>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        ) : null}

        <footer className="site-footer" aria-label="Footer" ref={footerSectionRef}>
          <div className="main-container">
            <div className="footer-grid">
              <section className="footer-col footer-col-stores" aria-label="Наши адреса и телефоны">
                <h3 className="footer-title">Наши контакты</h3>
                {footerRows.map((row, index) => {
                  const phoneHref = toTelHref(row.phone);
                  return (
                    <div className="footer-store-row" key={`store-row-${index}`}>
                      <span className="footer-store-address">{row.address}</span>
                      <span className="footer-store-separator" aria-hidden="true" />
                      {phoneHref ? (
                        <a className="footer-store-phone" href={phoneHref}>
                          {row.phone}
                        </a>
                      ) : (
                        <span className="footer-store-phone">{row.phone}</span>
                      )}
                    </div>
                  );
                })}
              </section>

              <section className="footer-col" aria-label="Наши ресурсы">
                <h3 className="footer-title">Наши ресурсы</h3>
                <div className="footer-socials">
                  {footerSocialLinks.map((item) => (
                    <a
                      key={`social-${item.platform}`}
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={SOCIAL_LABELS[item.platform]}
                    >
                      <img
                        src={SOCIAL_ICONS[item.platform]}
                        alt={SOCIAL_LABELS[item.platform]}
                      />
                    </a>
                  ))}
                </div>
              </section>

              <section className="footer-col footer-col-maker" aria-label="Создание сайта">
                <h3 className="footer-title">Создание сайта</h3>
                <a
                  className="footer-maker-btn"
                  href={STATIC_FOOTER_MAKER.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <img src="/static/icons/telegram.svg" alt="" />
                  <span>{STATIC_FOOTER_MAKER.label}</span>
                </a>
              </section>
            </div>

            <div className="footer-divider" />
            {siteSettings?.legal_text ? (
              <p className="footer-legal">{siteSettings.legal_text}</p>
            ) : null}
          </div>
        </footer>
      </main>

      {!shouldHidePrices && isSortOpen && sortPopupPosition ? (
        <div className="sort-overlay" onClick={closeSortPopup}>
          <div
            className="sort-popup"
            style={{
              top: sortPopupPosition.top,
              left: sortPopupPosition.left,
              width: sortPopupPosition.width,
            }}
            onClick={(event) => event.stopPropagation()}
          >
            {SORT_OPTIONS.map((option) => (
              <button
                key={option.key}
                type="button"
                className={`sort-popup-row ${sortBy === option.key ? "is-active" : ""}`}
                onClick={() => applySort(option.key)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {filterModal ? (
        <BottomSheet
          overlayClassName="filter-overlay"
          sheetClassName="filter-sheet"
          dragZoneClassName="filter-drag-zone"
          grabberClassName="filter-grabber"
          overlayAlphaVar="--filter-overlay-alpha"
          overlayBaseAlpha={0.45}
          closeDurationMs={460}
          onRequestClose={closeFilterModal}
        >
          {({ requestClose }) => (
            <>
            <button className="desktop-modal-close" type="button" onClick={requestClose}>
              <img src="/static/icons/close.svg" alt="" aria-hidden="true" />
            </button>
            <div className="filter-title-row">
              <h3 className="filter-title">{modalTitle}</h3>
            </div>
            <div className="filter-grid-wrap">
              <div className="filter-grid">
                <button
                  type="button"
                  className={`filter-cell ${isAllSelected ? "is-selected" : ""}`}
                  onClick={() => {
                    if (isCategoryModal) {
                      resetCategories();
                    } else {
                      resetCountries();
                    }
                    requestClose();
                  }}
                >
                  <span className="filter-cell-image-wrap">
                    <img
                      className="filter-cell-image"
                      src={
                        resolveMediaUrl(allFilterImage) ||
                        "/static/images/placeholder.png"
                      }
                      alt=""
                    />
                  </span>
                  <span className="filter-cell-label">
                    {isCategoryModal ? "Все категории" : "Все страны"}
                  </span>
                </button>

                {modalOptions.map((option) => {
                  const isSelected = isCategoryModal
                    ? selectedCategories.includes(option.slug)
                    : selectedCountries.includes(option.slug);

                  return (
                    <button
                      key={option.id}
                      type="button"
                      className={`filter-cell ${isSelected ? "is-selected" : ""} ${
                        !option.enabled && !isSelected ? "is-disabled" : ""
                      }`}
                      onClick={() =>
                        isCategoryModal ? toggleCategory(option) : toggleCountry(option)
                      }
                    >
                      <span className="filter-cell-image-wrap">
                        <img
                          className="filter-cell-image"
                          src={
                            resolveMediaUrl(option.image) ||
                            "/static/images/placeholder.png"
                          }
                          alt={option.title}
                        />
                      </span>
                      <span className="filter-cell-label">{option.title}</span>
                      {!shouldHidePrices && option.discount_badge ? (
                        <span className="filter-cell-discount">{option.discount_badge}</span>
                      ) : null}
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="filter-divider" />
            <div className="filter-actions">
              <button
                className="filter-apply"
                type="button"
                onClick={requestClose}
              >
                Применить
              </button>
            </div>
            </>
          )}
        </BottomSheet>
      ) : null}

      {deliveryModalState && selectedDeliveryMeta ? (
        <BottomSheet
          overlayClassName="delivery-overlay"
          sheetClassName="delivery-sheet"
          dragZoneClassName="delivery-drag-zone"
          grabberClassName="delivery-grabber"
          overlayAlphaVar="--delivery-overlay-alpha"
          overlayBaseAlpha={0.45}
          closeDurationMs={460}
          onRequestClose={() => setDeliveryModalState(null)}
        >
          {({ requestClose }) => (
            <>
              <button className="desktop-modal-close" type="button" onClick={requestClose}>
                <img src="/static/icons/close.svg" alt="" aria-hidden="true" />
              </button>
              <div className="delivery-title-row">
                <h3 className="delivery-title">Зона доставки:</h3>
              </div>
              <div className="delivery-map-frame-wrap">
                <div id="yandex-delivery-map-frame" className="delivery-map-frame" />
              </div>
              <div className="delivery-hint-row">
                <p className="delivery-hint-text">Вы можете оформить заказ по кнопке ниже:</p>
              </div>
              {deliveryModalState.delivery.service_url ? (
                <a
                  className={`delivery-service-chip delivery-service-chip--${deliveryModalState.delivery.service_type} is-modal-link`}
                  href={deliveryModalState.delivery.service_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <img
                    className="delivery-service-icon"
                    src={selectedDeliveryMeta.icon}
                    alt={selectedDeliveryMeta.label}
                  />
                  <span>{selectedDeliveryMeta.label}</span>
                </a>
              ) : modalStorePhoneHref ? (
                <a
                  className={`delivery-service-chip delivery-service-chip--${deliveryModalState.delivery.service_type} is-modal-link`}
                  href={modalStorePhoneHref}
                >
                  <img
                    className="delivery-service-icon"
                    src={selectedDeliveryMeta.icon}
                    alt={selectedDeliveryMeta.label}
                  />
                  <span>{selectedDeliveryMeta.label}</span>
                </a>
              ) : null}
              <div className="delivery-modal-footer">
                <button type="button" className="delivery-apply-btn" onClick={requestClose}>
                  Закрыть
                </button>
              </div>
            </>
          )}
        </BottomSheet>
      ) : null}

      {promoProductsModal ? (
        <BottomSheet
          overlayClassName="promo-overlay"
          sheetClassName="promo-sheet"
          dragZoneClassName="promo-drag-zone"
          grabberClassName="promo-grabber"
          overlayAlphaVar="--promo-overlay-alpha"
          overlayBaseAlpha={0.45}
          closeDurationMs={460}
          onRequestClose={() => setPromoProductsModal(null)}
        >
          {({ requestClose }) => (
            <>
              <div className="promo-title-row">
                <h3 className="promo-title">Новинки</h3>
                <button className="promo-title-close" type="button" onClick={requestClose}>
                  <img src="/static/icons/close.svg" alt="" aria-hidden="true" />
                </button>
              </div>
              <div className="promo-products-grid" aria-label="Товары подборки">
                {promoProductsModal.products.map((product) => (
                  <Link
                    className="promo-product-card"
                    key={`promo-product-${product.id}`}
                    href={`/p/${product.slug}`}
                    scroll={false}
                    onClick={(event) => {
                      handleProductClick(event, product.slug, product);
                      requestClose();
                    }}
                  >
                    <img
                      className="promo-product-image"
                      src={
                        resolveMediaUrl(product.photo_thumb || product.photo) ||
                        "/static/images/placeholder.png"
                      }
                      alt={product.title}
                    />
                    <span className="promo-product-title">{product.title}</span>
                  </Link>
                ))}
              </div>
              <div className="promo-divider" />
              <div className="promo-footer">
                <button
                  type="button"
                  className="promo-close-btn filter-apply"
                  onClick={requestClose}
                >
                  Закрыть
                </button>
              </div>
            </>
          )}
        </BottomSheet>
      ) : null}
    </>
  );
}
