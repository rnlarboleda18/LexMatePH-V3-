/**
 * This Vite app does not execute Clerk Edge middleware. For a future Next.js app,
 * add /legal(.*) to public routes. In App.jsx, /legal and /about use PublicLayout.
 */
export const LEXMATE_PUBLIC_PATHS = [/^\/legal(\/.*)?$/, /^\/about\/?$/];

export {};
