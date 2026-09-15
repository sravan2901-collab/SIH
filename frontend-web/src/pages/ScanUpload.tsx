import React, { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate, Navigate } from "react-router";
import { useAuth } from "../context/AuthContext";
import { apiFetch, ApiError } from "../lib/apiClient";
import type { Product } from "../types/product";
import type { ScanRead, ScanStatusRead, ScanStatus } from "../types/scan";

export function ScanUpload() {
  const { token, role, userId, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const product = (location.state as { product?: Product; productId?: string } | null)?.product;
  const productId = (location.state as { product?: Product; productId?: string } | null)?.productId;
  const activeProductId = productId || product?.product_id;

  // File and Upload State
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Scan Processing State
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Clean up object URL when previewUrl changes or component unmounts
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // Poll scan processing status every 3 seconds after successful upload
  useEffect(() => {
    if (!scanId || scanStatus === "done" || scanStatus === "error") {
      return;
    }

    const intervalId = setInterval(async () => {
      try {
        const res = await apiFetch<ScanStatusRead>(`/scans/${scanId}/status`, {}, token);
        setScanStatus(res.status);
        if (res.status === "done") {
          navigate(`/scan/${scanId}/review`);
        }
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        }
      }
    }, 3000);

    return () => clearInterval(intervalId);
  }, [scanId, scanStatus, token, navigate]);

  // Keep /scan reachable only after a product is chosen
  if (!product && !productId) {
    return <Navigate to="/products" replace />;
  }

  const handleFileSelect = (selectedFile: File) => {
    setError(null);
    const validTypes = ["image/jpeg", "image/jpg", "image/png"];
    const validExtensions = [".jpg", ".jpeg", ".png"];
    const lowerName = selectedFile.name.toLowerCase();
    const hasValidExt = validExtensions.some((ext) => lowerName.endsWith(ext));
    const hasValidType = validTypes.includes(selectedFile.type);

    if (!hasValidExt && !hasValidType) {
      setError("Invalid file type. Only JPEG and PNG images are allowed.");
      return;
    }

    if (selectedFile.size === 0) {
      setError("Uploaded file is empty.");
      return;
    }

    if (selectedFile.size > 20 * 1024 * 1024) {
      setError("File size exceeds maximum allowed limit of 20MB.");
      return;
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setFile(selectedFile);
    setPreviewUrl(URL.createObjectURL(selectedFile));
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file || !activeProductId) {
      setError("Please select a label image to upload.");
      return;
    }

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("product_id", activeProductId);
    formData.append("file", file);

    try {
      const res = await apiFetch<ScanRead>(
        "/scans/upload",
        {
          method: "POST",
          body: formData,
        },
        token
      );
      setScanId(res.scan_id);
      setScanStatus(res.status);
      if (res.status === "done") {
        navigate(`/scan/${res.scan_id}/review`);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to upload image. Please try again.");
      }
    } finally {
      setIsUploading(false);
    }
  };

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

          {/* Error Alert */}
          {error && (
            <div
              role="alert"
              className="p-3 rounded bg-[#B3261E]/10 border border-[#B3261E]/20 text-xs text-[#B3261E]"
            >
              {error}
            </div>
          )}

          {/* Label Capture & Upload Section */}
          {!scanStatus ? (
            !file ? (
              <div
                onDragOver={handleDragOver}
                onDragEnter={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-md p-8 text-center cursor-pointer transition-colors ${
                  isDragging
                    ? "border-[#1F3B57] bg-[#1F3B57]/5"
                    : "border-[#D8DEE4] bg-[#F4F6F8] hover:border-[#1F3B57]/50"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/jpg"
                  capture="environment"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFileSelect(e.target.files[0]);
                    }
                  }}
                />
                <div className="flex flex-col items-center justify-center space-y-2">
                  <div className="w-10 h-10 rounded-full bg-white border border-[#D8DEE4] flex items-center justify-center text-[#1F3B57]">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                      />
                    </svg>
                  </div>
                  <div className="text-sm font-semibold text-[#1F3B57]">
                    Drag & drop label image here, or click to browse
                  </div>
                  <p className="text-xs text-[#5B6472]">
                    Supports JPEG or PNG format (max 20MB)
                  </p>
                </div>
              </div>
            ) : (
              <div className="border border-[#D8DEE4] rounded-md p-4 bg-[#F4F6F8] space-y-4">
                <div className="relative rounded overflow-hidden border border-[#D8DEE4] bg-white flex items-center justify-center max-h-60 p-2">
                  <img
                    src={previewUrl!}
                    alt="Label preview"
                    className="max-h-56 w-auto object-contain rounded"
                  />
                </div>
                <div className="flex items-center justify-between text-xs text-[#5B6472]">
                  <span className="truncate max-w-[200px] font-medium text-[#1A1F26]">
                    {file.name}
                  </span>
                  <span>{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={isUploading}
                    onClick={() => {
                      setFile(null);
                      if (previewUrl) URL.revokeObjectURL(previewUrl);
                      setPreviewUrl(null);
                    }}
                    className="flex-1 py-2 px-3 border border-[#D8DEE4] rounded bg-white hover:bg-[#F4F6F8] text-xs font-medium text-[#5B6472] transition-colors disabled:opacity-50"
                  >
                    Change Image
                  </button>
                  <button
                    type="button"
                    disabled={isUploading}
                    onClick={handleUpload}
                    className="flex-1 py-2 px-3 bg-[#1F3B57] hover:bg-[#15283c] text-white rounded text-xs font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {isUploading ? "Uploading..." : "Upload & Analyze Label"}
                  </button>
                </div>
              </div>
            )
          ) : (
            <div className="space-y-4">
              {/* Thumbnail of uploaded image */}
              {previewUrl && (
                <div className="relative rounded overflow-hidden border border-[#D8DEE4] bg-white flex items-center justify-center max-h-40 p-2">
                  <img
                    src={previewUrl}
                    alt="Uploaded label"
                    className="max-h-36 w-auto object-contain rounded"
                  />
                </div>
              )}

              {/* Progress Indicator */}
              <div className="bg-[#F4F6F8] border border-[#D8DEE4] rounded-md p-4 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-[#1F3B57]">Analysis Pipeline</span>
                  <span className="font-mono text-[#5B6472] uppercase text-[10px]">
                    Status: <strong className="text-[#1F3B57]">{scanStatus}</strong>
                  </span>
                </div>

                {/* Progress Steps */}
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { key: "queued", label: "1. Queued" },
                    { key: "processing", label: "2. Processing" },
                    { key: "done", label: "3. Ready" },
                  ].map((step, idx) => {
                    const currentStepIndex =
                      scanStatus === "queued"
                        ? 0
                        : scanStatus === "processing"
                        ? 1
                        : scanStatus === "done"
                        ? 2
                        : -1;
                    const isComplete = currentStepIndex > idx || scanStatus === "done";
                    const isCurrent = currentStepIndex === idx;

                    return (
                      <div
                        key={step.key}
                        className={`text-center py-2 px-1 rounded text-[11px] font-medium transition-all ${
                          isComplete
                            ? "bg-[#1F3B57] text-white"
                            : isCurrent
                            ? "bg-[#B8862E] text-white animate-pulse"
                            : "bg-white border border-[#D8DEE4] text-[#5B6472]"
                        }`}
                      >
                        {step.label}
                      </div>
                    );
                  })}
                </div>

                <div className="text-center text-xs text-[#5B6472] pt-1">
                  {scanStatus === "queued" && "Scan queued. Waiting for worker..."}
                  {scanStatus === "processing" && "Extracting declarations and validating rules..."}
                  {scanStatus === "done" && "Analysis complete! Redirecting to review..."}
                  {scanStatus === "error" && "An error occurred during analysis."}
                </div>
              </div>
            </div>
          )}

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
