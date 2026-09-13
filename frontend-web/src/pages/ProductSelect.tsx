import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "../context/AuthContext";
import { apiFetch, ApiError } from "../lib/apiClient";
import type { Product, ProductCreatePayload } from "../types/product";

export function ProductSelect() {
  const { token, role, userId, logout } = useAuth();
  const navigate = useNavigate();

  // Search state
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Selection state
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  // Create form state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [formData, setFormData] = useState<ProductCreatePayload>({
    name: "",
    brand: "",
    manufacturer_name: "",
    manufacturer_address: "",
    category: "",
    barcode: "",
  });

  // Debounced search (300ms)
  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      return;
    }

    let isMounted = true;
    const timer = setTimeout(() => {
      setIsSearching(true);
      setSearchError(null);
      apiFetch<Product[]>(`/products?q=${encodeURIComponent(trimmed)}`, {}, token)
        .then((results) => {
          if (isMounted) {
            setSearchResults(results);
          }
        })
        .catch((err) => {
          if (isMounted) {
            if (err instanceof ApiError) {
              setSearchError(err.message);
            } else {
              setSearchError("Failed to search products. Please check connection.");
            }
          }
        })
        .finally(() => {
          if (isMounted) {
            setIsSearching(false);
          }
        });
    }, 300);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [query, token]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreateProduct = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCreateError(null);
    setSuccessMessage(null);
    setIsSubmitting(true);

    const payload: ProductCreatePayload = {
      name: formData.name.trim(),
      brand: formData.brand?.trim() || null,
      manufacturer_name: formData.manufacturer_name?.trim() || null,
      manufacturer_address: formData.manufacturer_address?.trim() || null,
      category: formData.category?.trim() || null,
      barcode: formData.barcode?.trim() || null,
    };

    try {
      const created = await apiFetch<Product>(
        "/products",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
        token
      );

      // Auto-select newly created product
      setSelectedProduct(created);
      setSuccessMessage(`Product "${created.name}" created and selected successfully.`);
      // Prepend to search results if not already present
      setSearchResults((prev) => [
        created,
        ...prev.filter((p) => p.product_id !== created.product_id),
      ]);
      // Reset form and collapse
      setFormData({
        name: "",
        brand: "",
        manufacturer_name: "",
        manufacturer_address: "",
        category: "",
        barcode: "",
      });
      setIsFormOpen(false);
    } catch (err) {
      if (err instanceof ApiError) {
        setCreateError(err.message);
      } else {
        setCreateError("Failed to create product. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleContinue = () => {
    if (!selectedProduct) return;
    navigate("/scan", {
      state: {
        product: selectedProduct,
        productId: selectedProduct.product_id,
      },
    });
  };

  return (
    <div className="min-h-screen bg-[#F4F6F8] text-[#1A1F26] p-4 sm:p-6 lg:p-8 font-sans antialiased">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header Bar */}
        <header className="flex flex-col sm:flex-row sm:items-center justify-between bg-white border border-[#D8DEE4] rounded-md p-4 sm:p-6 shadow-none">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-[#1F3B57] tracking-tight">
              LMPC Compliance System
            </h1>
            <p className="text-sm text-[#5B6472] mt-0.5">
              Select or Register Product — Inspector Session
            </p>
          </div>
          <div className="flex items-center gap-3 mt-4 sm:mt-0">
            <div className="text-xs bg-[#F4F6F8] border border-[#D8DEE4] px-2.5 py-1.5 rounded font-mono text-[#5B6472]">
              {role} · {userId ? userId.slice(0, 8) : "N/A"}
            </div>
            <button
              type="button"
              onClick={logout}
              className="py-1.5 px-3 bg-white border border-[#D8DEE4] hover:bg-[#F4F6F8] text-[#1A1F26] text-xs font-medium rounded transition-colors"
            >
              Sign out
            </button>
          </div>
        </header>

        {/* Main Card */}
        <div className="bg-white border border-[#D8DEE4] rounded-md overflow-hidden shadow-none">
          {/* Muted gold accent top bar */}
          <div className="h-1 bg-[#B8862E]" />

          <div className="p-6 sm:p-8 space-y-6">
            {/* Notifications */}
            {successMessage && (
              <div
                role="status"
                className="p-3 rounded bg-[#1F3B57]/10 border border-[#1F3B57]/20 text-sm text-[#1F3B57]"
              >
                {successMessage}
              </div>
            )}

            {/* Search Section */}
            <div>
              <label
                htmlFor="product-search-input"
                className="block text-sm font-semibold text-[#1F3B57] mb-1 text-left"
              >
                Search Existing Products
              </label>
              <p className="text-xs text-[#5B6472] mb-2">
                Type product name, brand, or barcode (searches automatically after 300ms)
              </p>
              <div className="relative">
                <input
                  id="product-search-input"
                  type="text"
                  value={query}
                  onChange={(e) => {
                    const val = e.target.value;
                    setQuery(val);
                    if (!val.trim()) {
                      setSearchResults([]);
                      setSearchError(null);
                      setIsSearching(false);
                    }
                  }}
                  placeholder="e.g. Parle-G, Britannia, or 8901063..."
                  className="w-full px-3.5 py-2.5 text-sm border border-[#D8DEE4] rounded bg-white text-[#1A1F26] placeholder-[#5B6472]/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57] focus-visible:border-transparent transition-colors"
                />
                {isSearching && (
                  <div className="absolute right-3 top-3 text-xs text-[#5B6472] animate-pulse">
                    Searching…
                  </div>
                )}
              </div>

              {searchError && (
                <div
                  role="alert"
                  className="mt-2 p-2.5 rounded bg-[#B3261E]/10 border border-[#B3261E]/20 text-xs text-[#B3261E]"
                >
                  {searchError}
                </div>
              )}

              {/* Search Results List */}
              {query.trim().length > 0 && !isSearching && (
                <div className="mt-3">
                  {searchResults.length === 0 ? (
                    <div className="p-4 border border-[#D8DEE4] rounded bg-[#F4F6F8] text-center text-sm text-[#5B6472]">
                      No products found for &ldquo;{query}&rdquo;. You can register it below.
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto border border-[#D8DEE4] rounded p-2">
                      {searchResults.map((product) => {
                        const isSelected =
                          selectedProduct?.product_id === product.product_id;
                        return (
                          <div
                            key={product.product_id}
                            onClick={() => setSelectedProduct(product)}
                            className={`p-3 rounded border cursor-pointer transition-colors flex items-center justify-between ${
                              isSelected
                                ? "bg-[#1F3B57]/5 border-[#1F3B57] ring-1 ring-[#1F3B57]"
                                : "bg-white border-[#D8DEE4] hover:bg-[#F4F6F8]"
                            }`}
                          >
                            <div className="space-y-0.5">
                              <div className="font-semibold text-sm text-[#1F3B57]">
                                {product.name}
                              </div>
                              <div className="text-xs text-[#5B6472] flex items-center gap-3">
                                {product.brand && (
                                  <span>Brand: <strong className="text-[#1A1F26]">{product.brand}</strong></span>
                                )}
                                {product.category && (
                                  <span>Category: {product.category}</span>
                                )}
                                {product.barcode && (
                                  <span className="font-mono bg-[#F4F6F8] px-1.5 py-0.5 rounded border border-[#D8DEE4]">
                                    {product.barcode}
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center">
                              <input
                                type="radio"
                                name="selected-product"
                                checked={isSelected}
                                onChange={() => setSelectedProduct(product)}
                                className="w-4 h-4 text-[#1F3B57] focus:ring-[#1F3B57] border-[#D8DEE4]"
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="relative flex py-2 items-center">
              <div className="flex-grow border-t border-[#D8DEE4]"></div>
              <span className="flex-shrink mx-4 text-xs font-medium text-[#5B6472] uppercase tracking-wider">
                Or Register New
              </span>
              <div className="flex-grow border-t border-[#D8DEE4]"></div>
            </div>

            {/* Create Product Section / Accordion */}
            <div>
              <button
                type="button"
                onClick={() => {
                  setIsFormOpen(!isFormOpen);
                  setCreateError(null);
                }}
                className="w-full py-2 px-4 bg-white border border-[#D8DEE4] hover:bg-[#F4F6F8] text-[#1F3B57] text-sm font-semibold rounded flex items-center justify-between transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57]"
              >
                <span>+ Register New Product</span>
                <span className="text-xs text-[#5B6472]">
                  {isFormOpen ? "Hide Form ▲" : "Show Form ▼"}
                </span>
              </button>

              {isFormOpen && (
                <form
                  onSubmit={handleCreateProduct}
                  className="mt-4 p-5 bg-[#F4F6F8] border border-[#D8DEE4] rounded-md space-y-4 text-left"
                >
                  <h2 className="text-sm font-semibold text-[#1F3B57]">
                    Product Registration Details
                  </h2>

                  {createError && (
                    <div
                      role="alert"
                      className="p-3 rounded bg-[#B3261E]/10 border border-[#B3261E]/20 text-xs text-[#B3261E]"
                    >
                      {createError}
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="sm:col-span-2">
                      <label
                        htmlFor="create-name"
                        className="block text-xs font-semibold text-[#1A1F26] mb-1"
                      >
                        Product Name <span className="text-[#B3261E]">*</span>
                      </label>
                      <input
                        id="create-name"
                        name="name"
                        type="text"
                        required
                        value={formData.name}
                        onChange={handleInputChange}
                        placeholder="e.g. Parle-G Gold Biscuits 100g"
                        className="w-full px-3 py-2 text-sm border border-[#D8DEE4] rounded bg-white text-[#1A1F26] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57]"
                      />
                    </div>

                    <div>
                      <label
                        htmlFor="create-brand"
                        className="block text-xs font-semibold text-[#1A1F26] mb-1"
                      >
                        Brand Name
                      </label>
                      <input
                        id="create-brand"
                        name="brand"
                        type="text"
                        value={formData.brand || ""}
                        onChange={handleInputChange}
                        placeholder="e.g. Parle"
                        className="w-full px-3 py-2 text-sm border border-[#D8DEE4] rounded bg-white text-[#1A1F26] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57]"
                      />
                    </div>

                    <div>
                      <label
                        htmlFor="create-category"
                        className="block text-xs font-semibold text-[#1A1F26] mb-1"
                      >
                        Category
                      </label>
                      <input
                        id="create-category"
                        name="category"
                        type="text"
                        value={formData.category || ""}
                        onChange={handleInputChange}
                        placeholder="e.g. Biscuits & Bakery"
                        className="w-full px-3 py-2 text-sm border border-[#D8DEE4] rounded bg-white text-[#1A1F26] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57]"
                      />
                    </div>

                    <div>
                      <label
                        htmlFor="create-barcode"
                        className="block text-xs font-semibold text-[#1A1F26] mb-1"
                      >
                        Barcode / GTIN
                      </label>
                      <input
                        id="create-barcode"
                        name="barcode"
                        type="text"
                        value={formData.barcode || ""}
                        onChange={handleInputChange}
                        placeholder="e.g. 8901063012345"
                        className="w-full px-3 py-2 text-sm border border-[#D8DEE4] rounded bg-white text-[#1A1F26] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57]"
                      />
                    </div>

                    <div>
                      <label
                        htmlFor="create-manufacturer-name"
                        className="block text-xs font-semibold text-[#1A1F26] mb-1"
                      >
                        Manufacturer Name
                      </label>
                      <input
                        id="create-manufacturer-name"
                        name="manufacturer_name"
                        type="text"
                        value={formData.manufacturer_name || ""}
                        onChange={handleInputChange}
                        placeholder="e.g. Parle Products Pvt Ltd"
                        className="w-full px-3 py-2 text-sm border border-[#D8DEE4] rounded bg-white text-[#1A1F26] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57]"
                      />
                    </div>

                    <div className="sm:col-span-2">
                      <label
                        htmlFor="create-manufacturer-address"
                        className="block text-xs font-semibold text-[#1A1F26] mb-1"
                      >
                        Manufacturer Address
                      </label>
                      <textarea
                        id="create-manufacturer-address"
                        name="manufacturer_address"
                        rows={2}
                        value={formData.manufacturer_address || ""}
                        onChange={handleInputChange}
                        placeholder="e.g. Vile Parle East, Mumbai, Maharashtra 400057"
                        className="w-full px-3 py-2 text-sm border border-[#D8DEE4] rounded bg-white text-[#1A1F26] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57]"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setIsFormOpen(false)}
                      className="px-4 py-2 bg-white border border-[#D8DEE4] hover:bg-gray-50 text-[#1A1F26] text-xs font-medium rounded transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-2 bg-[#1F3B57] hover:bg-[#16293D] disabled:opacity-60 text-white text-xs font-semibold rounded transition-colors"
                    >
                      {isSubmitting ? "Creating…" : "Save & Select Product"}
                    </button>
                  </div>
                </form>
              )}
            </div>

            {/* Selected Product Summary & Continue Action */}
            <div className="pt-4 border-t border-[#D8DEE4] space-y-4">
              {selectedProduct ? (
                <div className="p-4 rounded border border-[#1F3B57]/30 bg-[#1F3B57]/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-left">
                  <div>
                    <div className="text-xs font-medium text-[#5B6472] uppercase tracking-wider">
                      Selected for Inspection
                    </div>
                    <div className="font-bold text-[#1F3B57] text-base">
                      {selectedProduct.name}
                    </div>
                    <div className="text-xs text-[#5B6472] mt-0.5">
                      {selectedProduct.brand && <span>Brand: {selectedProduct.brand} · </span>}
                      <span>Barcode: {selectedProduct.barcode || "N/A"}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedProduct(null)}
                    className="text-xs text-[#5B6472] hover:text-[#B3261E] underline self-start sm:self-center"
                  >
                    Clear selection
                  </button>
                </div>
              ) : (
                <div className="text-xs text-[#5B6472] italic text-center">
                  Please search and select a product, or register a new one to continue.
                </div>
              )}

              <button
                type="button"
                onClick={handleContinue}
                disabled={!selectedProduct}
                className="w-full py-2.5 px-4 bg-[#1F3B57] hover:bg-[#16293D] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F3B57] focus-visible:ring-offset-2"
              >
                Continue to Scan →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
