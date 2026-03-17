"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { formatPrice, resolveMediaUrl } from "@/lib/api";
import { getProduct, getSiteSettingsRaw, type ProductDetail } from "@/lib/catalog-api";
import {
  MODAL_BACK_KEY,
  PENDING_FILTERS_KEY,
  getCatalogReturnUrl,
  makePreviewKey,
  removeSessionItem,
  setSessionJson,
  setSessionItem,
  getSessionItem,
} from "@/lib/catalog-storage";
import BottomSheet from "@/components/BottomSheet";

type TabKey = "description" | "ingredients" | "preparation" | "serving";

const TAB_DEFS: { key: TabKey; label: string }[] = [
  { key: "description", label: "Описание" },
  { key: "ingredients", label: "Состав" },
  { key: "preparation", label: "Приготовление" },
  { key: "serving", label: "Подача" },
];

export default function ProductModalPage() {
  const router = useRouter();
  const params = useParams();
  const slug = typeof params.slug === "string" ? params.slug : params.slug?.[0];

  const [fetchedProductBySlug, setFetchedProductBySlug] = useState<{
    slug: string;
    product: ProductDetail;
  } | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey | null>(null);
  const [resolvedSlug, setResolvedSlug] = useState<string | null>(() => slug ?? null);
  const [hidePrices, setHidePrices] = useState(true);
  const tabTouchStart = useRef<{ x: number; y: number } | null>(null);
  const tabTouchCurrent = useRef<{ x: number; y: number } | null>(null);
  const product = slug && fetchedProductBySlug?.slug === slug ? fetchedProductBySlug.product : null;

  useEffect(() => {
    if (!slug) return;

    const controller = new AbortController();

    getProduct(slug, {
      signal: controller.signal,
    })
      .then((data: ProductDetail | null) => {
        setResolvedSlug(slug);
        if (!data) return;
        setFetchedProductBySlug({ slug, product: data });
        setSessionJson(makePreviewKey(slug), data);
      })
      .catch(() => {
        setResolvedSlug(slug);
      });

    return () => controller.abort();
  }, [slug]);

  useEffect(() => {
    const controller = new AbortController();

    getSiteSettingsRaw<{ hide_prices?: unknown }>({
      signal: controller.signal,
    })
      .then((data: { hide_prices?: unknown } | null) => {
        setHidePrices(Boolean(data?.hide_prices));
      })
      .catch(() => {
        setHidePrices(true);
      });

    return () => controller.abort();
  }, []);

  const availableTabs = useMemo(() => {
    if (!product) return [];
    return TAB_DEFS.filter((tab) => {
      const value = product[tab.key];
      return typeof value === "string" ? value.trim().length > 0 : Boolean(value);
    });
  }, [product]);

  const tabsToRender = availableTabs.length ? availableTabs : [TAB_DEFS[0]];

  const resolvedActiveTab =
    activeTab && tabsToRender.some((tab) => tab.key === activeTab)
      ? activeTab
      : tabsToRender[0]?.key ?? null;

  const handleTabsTouchStart = (event: React.TouchEvent<HTMLElement>) => {
    if (tabsToRender.length < 2) return;
    const touch = event.touches[0];
    if (!touch) return;
    const point = { x: touch.clientX, y: touch.clientY };
    tabTouchStart.current = point;
    tabTouchCurrent.current = point;
  };

  const handleTabsTouchMove = (event: React.TouchEvent<HTMLElement>) => {
    const touch = event.touches[0];
    if (!touch || !tabTouchStart.current) return;
    tabTouchCurrent.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleTabsTouchEnd = () => {
    if (!tabTouchStart.current || !tabTouchCurrent.current) return;

    const deltaX = tabTouchStart.current.x - tabTouchCurrent.current.x;
    const deltaY = Math.abs(tabTouchStart.current.y - tabTouchCurrent.current.y);
    const swipeThreshold = 42;

    if (Math.abs(deltaX) > swipeThreshold && Math.abs(deltaX) > deltaY) {
      const currentIndex = tabsToRender.findIndex(
        (tab) => tab.key === resolvedActiveTab
      );
      if (currentIndex >= 0) {
        const targetIndex =
          deltaX > 0
            ? Math.min(currentIndex + 1, tabsToRender.length - 1)
            : Math.max(currentIndex - 1, 0);
        const target = tabsToRender[targetIndex];
        if (target && target.key !== resolvedActiveTab) {
          setActiveTab(target.key);
        }
      }
    }

    tabTouchStart.current = null;
    tabTouchCurrent.current = null;
  };

  const navigateToCatalog = useCallback(
    (target: string) => {
      router.replace(target, { scroll: false });
    },
    [router]
  );

  const closeRoute = useCallback(() => {
    if (typeof window === "undefined") {
      router.replace("/");
      return;
    }

    const target = getCatalogReturnUrl() ?? "/";
    const shouldUseBack = getSessionItem(MODAL_BACK_KEY) === "1";
    removeSessionItem(MODAL_BACK_KEY);

    if (!shouldUseBack) {
      navigateToCatalog(target);
      return;
    }

    router.back();
    const fallbackTimer = window.setTimeout(() => {
      if (window.location.pathname.startsWith("/p/")) {
        navigateToCatalog(target);
      }
    }, 320);
    void fallbackTimer;
  }, [navigateToCatalog, router]);

  const applyFilterFromTag = useCallback(
    (kind: "category" | "country", closeModal?: () => void) => {
      if (!product) {
        closeRoute();
        return;
      }

      const payload =
        kind === "category"
          ? { category: [product.category_slug], country: [] }
          : { category: [], country: [product.country_slug] };

      if (setSessionItem(PENDING_FILTERS_KEY, JSON.stringify(payload))) {
        window.dispatchEvent(
          new CustomEvent("hanguk:apply-filters", { detail: payload })
        );
      }

      if (closeModal) {
        closeModal();
        return;
      }

      closeRoute();
    },
    [closeRoute, product]
  );

  if (!product) {
    return (
      <BottomSheet
        overlayClassName="modal-overlay"
        sheetClassName="modal-sheet"
        dragZoneClassName="modal-drag-zone"
        grabberClassName="modal-grabber"
        overlayAlphaVar="--overlay-alpha"
        overlayBaseAlpha={0.5}
        closeDurationMs={460}
        onRequestClose={closeRoute}
      >
        {({ requestClose }) => (
          <>
            <button className="desktop-modal-close" type="button" onClick={requestClose}>
              <img src="/static/icons/close.svg" alt="" aria-hidden="true" />
            </button>
            <div className="modal-content">
              <p>{resolvedSlug === slug ? "Сервис временно недоступен" : "Загрузка..."}</p>
            </div>
            <div className="modal-footer">
              <button className="modal-close" type="button" onClick={requestClose}>
                Закрыть
              </button>
            </div>
          </>
        )}
      </BottomSheet>
    );
  }

  const content = (() => {
    if (!resolvedActiveTab) return "";
    const rawValue = product[resolvedActiveTab];
    if (typeof rawValue === "string") {
      const trimmed = rawValue.trim();
      return trimmed || "Описание отсутствует";
    }
    return rawValue ? String(rawValue) : "Описание отсутствует";
  })();
  const mediaSrc = resolveMediaUrl(product.photo) || "/static/images/placeholder.png";

  return (
    <BottomSheet
      overlayClassName="modal-overlay"
      sheetClassName="modal-sheet"
      dragZoneClassName="modal-drag-zone"
      grabberClassName="modal-grabber"
      overlayAlphaVar="--overlay-alpha"
      overlayBaseAlpha={0.5}
      closeDurationMs={460}
      onRequestClose={closeRoute}
    >
      {({ requestClose }) => (
        <>
          <button className="desktop-modal-close" type="button" onClick={requestClose}>
            <img src="/static/icons/close.svg" alt="" aria-hidden="true" />
          </button>
          <div className="modal-header">
            <div className="modal-media">
              <div className="modal-media-badges">
                {product.is_new ? <span className="product-badge">новинка</span> : null}
                {!hidePrices && product.has_discount && product.discount_label ? (
                  <span className="product-badge product-badge-discount">
                    {product.discount_label}
                  </span>
                ) : null}
              </div>
              <img className="modal-image" src={mediaSrc} alt={product.title} />
            </div>
            <div className="modal-summary">
              <h2 className="modal-title">{product.title}</h2>
              <div className="modal-divider" />
              <div className="modal-meta">
                {!hidePrices ? (
                  product.has_discount && product.discounted_price ? (
                    <span className="modal-price-wrap">
                      <span className="modal-price modal-price-old">
                        {formatPrice(product.original_price || product.price)}
                      </span>
                      <span className="modal-price modal-price-discount">
                        {formatPrice(product.discounted_price)}
                      </span>
                    </span>
                  ) : (
                    <span className="modal-price">{formatPrice(product.price)}</span>
                  )
                ) : null}
                {product.spicy > 0 ? (
                  <div className="modal-spicy" aria-label="Spicy">
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
              <p className="modal-link">Переход к категориям:</p>
              <div className="modal-tags">
                <button
                  className="modal-tag modal-tag-button"
                  type="button"
                  onClick={() => applyFilterFromTag("category", requestClose)}
                >
                  {product.category_title}
                </button>
                <button
                  className="modal-tag modal-tag-button"
                  type="button"
                  onClick={() => applyFilterFromTag("country", requestClose)}
                >
                  {product.country_title}
                </button>
              </div>

              {tabsToRender.length ? (
                <div className="modal-details modal-details-desktop">
                  <div
                    className="modal-tabs"
                    onTouchStart={handleTabsTouchStart}
                    onTouchMove={handleTabsTouchMove}
                    onTouchEnd={handleTabsTouchEnd}
                  >
                    {tabsToRender.map((tab) => (
                      <button
                        key={tab.key}
                        className={`tab ${resolvedActiveTab === tab.key ? "is-active" : ""}`}
                        type="button"
                        onClick={() => setActiveTab(tab.key)}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  <div
                    className="modal-content"
                    onTouchStart={handleTabsTouchStart}
                    onTouchMove={handleTabsTouchMove}
                    onTouchEnd={handleTabsTouchEnd}
                  >
                    <p>{content}</p>
                  </div>
                </div>
              ) : null}
            </div>
          </div>

          {tabsToRender.length ? (
            <div className="modal-details modal-details-mobile">
              <div
                className="modal-tabs"
                onTouchStart={handleTabsTouchStart}
                onTouchMove={handleTabsTouchMove}
                onTouchEnd={handleTabsTouchEnd}
              >
                {tabsToRender.map((tab) => (
                  <button
                    key={tab.key}
                    className={`tab ${resolvedActiveTab === tab.key ? "is-active" : ""}`}
                    type="button"
                    onClick={() => setActiveTab(tab.key)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div
                className="modal-content"
                onTouchStart={handleTabsTouchStart}
                onTouchMove={handleTabsTouchMove}
                onTouchEnd={handleTabsTouchEnd}
              >
                <p>{content}</p>
              </div>
            </div>
          ) : null}

          <div className="modal-footer">
            <button className="modal-close" type="button" onClick={requestClose}>
              Закрыть
            </button>
          </div>
        </>
      )}
    </BottomSheet>
  );
}
