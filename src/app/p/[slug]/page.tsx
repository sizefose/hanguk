import CatalogPage from "@/app/(catalog)/page";
import ProductModalPage from "@/app/(catalog)/@modal/(.)p/[slug]/page";
import { getCatalogStaticData } from "@/lib/catalog-static.server";

export default async function ProductPage() {
  const initialData = await getCatalogStaticData();

  return (
    <>
      <CatalogPage initialData={initialData} />
      <ProductModalPage />
    </>
  );
}
