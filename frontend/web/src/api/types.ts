// AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
// Run: python backend/scripts/generate_typescript_client.py

export interface FeedbackRequest {
  user_id: string;
  garment_id: number;
  action: string;
  weight?: any;
  negative?: any;
}
export interface HTTPValidationError {
  detail?: ValidationError[];
}
export interface IngestRequest {
  external_id: string;
  image_base64: string;
  attributes?: any;
  title?: any;
  brand?: any;
  price?: any;
  currency?: any;
}
export interface InventoryBatchUploadRequest {
  items: InventoryUploadRequest[];
  overwrite?: boolean;
}
export interface InventoryProcessRequest {
  image_id?: any;
  overwrite?: boolean;
  model?: any;
  limit?: any;
}
export interface InventoryUploadRequest {
  filename: string;
  image_base64: string;
  overwrite?: boolean;
}
export interface PreferenceExtractRequest {
  conversation: string;
  model?: any;
}
export interface RefreshDescriptionRequest {
  garment_id: number;
  model?: any;
  overwrite?: boolean;
}
export interface SearchRequest {
  query: string;
  limit?: any;
  model?: any;
  user_id?: any;
  force?: any;
}
export interface SearchResponse {
  query?: any;
  results?: any;
  attributes?: any;
  ambiguous?: any;
  clarification?: any;
  off_topic?: any;
  off_topic_reason?: any;
  message?: any;
}
export interface SearchResultItem {
  garment_id?: any;
  score?: any;
  title?: any;
  brand?: any;
  price?: any;
  currency?: any;
  image_path?: any;
  description?: any;
  attributes?: any;
  explanation?: any;
}
export interface ValidationError {
  loc: any[];
  msg: string;
  type: string;
}
