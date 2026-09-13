import { useLocation, useNavigate, Navigate } from "react-router";
import { useAuth } from "../context/AuthContext";
import type { Product } from "../types/product";

export function Scan() {
  const { role, userId, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const product = (location.state as { product?: Product; productId?: string } | null)?.product;
  const productId = (location.state as { product?: Product; productId?: string } | null)?.productId;

  // Keep /scan reachable only after a product is chosen
  if (!product && !productId) {
    return <Navigate to="/products" replace />;
  }

  return (
    <div className="min-h-screen bg-[#F4F6F8] text-[#1A1F26] p-4 sm:p-8 flex flex-col items-center justify-center font-sans antialiased">
      <div className="w-full max-w-lg bg-white border border-[#D8DEE4] rounded-md overflow-hidden shadow-none">
        <div className="h-1 bg-[#B8862E]" />
        <div className="p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between border-b border-[#D8DEE4] pb-4">
            <div>
              <h1 className="text-xl font-bold text-[#1F3B57]">Scan & Capture</h1>
              <p className="text-xs text-[#5B6472] mt-0.5">
                LMPC Package Label Compliance Scanner
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/products")}
              className="text-xs text-[#1F3B57] hover:underline font-medium border border-[#D8DEE4] px-2.5 py-1 rounded bg-white hover:bg-[#F4F6F8]"
            >
              ← Change Product
            </button>
          </div>

          {/* Active Product Banner */}
          <div className="bg-[#1F3B57]/5 border border-[#1F3B57]/20 p-4 rounded-md text-left space-y-1">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[#5B6472]">
              Inspecting Product
            </div>
            <div className="text-base font-bold text-[#1F3B57]">
              {product ? product.name : "Selected Product"}
            </div>
            <div className="text-xs text-[#5B6472] flex flex-wrap gap-x-4 gap-y-1 pt-1">
              {product?.brand && <span>Brand: <strong className="text-[#1A1F26]">{product.brand}</strong></span>}
              {product?.category && <span>Category: {product.category}</span>}
              <span>Barcode: <code className="bg-white px-1 py-0.5 rounded border border-[#D8DEE4] font-mono">{product?.barcode || "N/A"}</code></span>
            </div>
            <div className="text-[10px] text-[#5B6472] font-mono pt-1">
              ID: {productId || product?.product_id}
            </div>
          </div>

          {/* Label Capture Placeholder (Phase 3 UI stub) */}
          <div className="border-2 border-dashed border-[#D8DEE4] rounded-md p-8 text-center bg-[#F4F6F8]">
            <div className="text-sm font-semibold text-[#1F3B57] mb-1">
              Label Image Capture
            </div>
            <p className="text-xs text-[#5B6472] max-w-sm mx-auto">
              Camera capture and image upload capabilities will be wired in Phase 3.
            </p>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="text-xs text-[#5B6472] font-mono">
              Inspector: {role} · {userId ? userId.slice(0, 8) : ""}
            </div>
            <button
              type="button"
              onClick={logout}
              className="py-1.5 px-3 bg-white border border-[#D8DEE4] hover:bg-[#F4F6F8] text-[#1A1F26] text-xs font-medium rounded transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
