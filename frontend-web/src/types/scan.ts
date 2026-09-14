export type ScanStatus = "queued" | "processing" | "done" | "needs_review" | "error";

export interface ScanRead {
  scan_id: string;
  product_id: string;
  uploaded_by: string;
  raw_image_path: string;
  preprocessed_image_path: string | null;
  capture_timestamp: string;
  status: ScanStatus;
}

export interface ScanStatusRead {
  scan_id: string;
  status: ScanStatus;
}
