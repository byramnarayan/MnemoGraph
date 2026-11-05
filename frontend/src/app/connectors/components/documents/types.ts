export interface DocumentUploadResult {
  title: string;
  indexed_chunks: number;
  entities_found: number;
  storage_key?: string;
  document_id?: string;
}

export interface DocumentUploadFormData {
  file: File | null;
  title: string;
  classification: string;
}

