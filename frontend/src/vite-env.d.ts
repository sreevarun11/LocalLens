/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MAP_STYLE_URL?: string;
  readonly VITE_GOOGLE_MAPS_BROWSER_KEY?: string;
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  readonly VITE_API_BASE_URL: string;
  readonly VITE_RAZORPAY_KEY_ID: string;
  readonly VITE_FEATURE_3D: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
