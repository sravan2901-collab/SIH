export interface Product {
  product_id: string;
  name: string;
  brand: string | null;
  manufacturer_name: string | null;
  manufacturer_address: string | null;
  category: string | null;
  barcode: string | null;
  created_at: string;
}

export interface ProductCreatePayload {
  name: string;
  brand?: string | null;
  manufacturer_name?: string | null;
  manufacturer_address?: string | null;
  category?: string | null;
  barcode?: string | null;
}
