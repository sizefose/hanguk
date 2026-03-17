import { apiFetchOr, type ApiFetchOptions } from "@/lib/api-client";

export type ProductDetail = {
  id: number;
  title: string;
  slug: string;
  description: string;
  ingredients: string;
  preparation: string;
  serving: string;
  photo: string | null;
  photo_thumb: string | null;
  price: string;
  original_price: string;
  discounted_price: string | null;
  has_discount: boolean;
  discount_label: string | null;
  spicy: number;
  is_new: boolean;
  category: number;
  country: number;
  category_title: string;
  category_slug: string;
  category_image: string | null;
  country_title: string;
  country_slug: string;
  country_image: string | null;
};

export const getProduct = (
  slug: string,
  options: ApiFetchOptions = {}
): Promise<ProductDetail | null> =>
  apiFetchOr<ProductDetail | null>(`/products/${slug}/`, null, {
    cache: "no-store",
    ...options,
  });

export const getSiteSettingsRaw = <T = unknown>(
  options: ApiFetchOptions = {}
): Promise<T | null> =>
  apiFetchOr<T | null>("/site-settings/", null, {
    cache: "no-store",
    ...options,
  });
