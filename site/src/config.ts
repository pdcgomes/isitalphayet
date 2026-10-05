export const SITE_URL: string = import.meta.env.VITE_SITE_URL || "https://isitalphayet.com";
export const SITE_HOST = SITE_URL.replace(/^https?:\/\//, "");

// Set VITE_REPO_URL in Vercel once the public GitHub repo exists; links to the code stay hidden until then.
export const REPO_URL: string | undefined = import.meta.env.VITE_REPO_URL || undefined;
