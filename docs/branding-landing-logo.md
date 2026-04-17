# LexMatePH header branding

The **same logo lockup** (mark + wordmark + tagline) is used in:

- [`LandingPage.jsx`](../src/frontend/src/components/LandingPage.jsx) — marketing glass header.
- [`Layout.jsx`](../src/frontend/src/components/Layout.jsx) — main app chrome (next to the hamburger menu).

Implementation details match between the two; Layout adds explicit `text-black dark:text-zinc-50` on the wordmark for contrast on `APP_HEADER_SURFACE`.

---

## Logo lockup (Landing + Layout)

| Element | Implementation |
|--------|----------------|
| **Mark** | `h-10 w-10` `rounded-xl`, `bg-gradient-to-br from-purple-600 to-violet-600`, white Lucide **`Scale`** `h-5 w-5`, `strokeWidth={2}`, `shadow-md shadow-purple-600/30` |
| **Wordmark** | `font-display` (Playfair Display), `text-lg` / `sm:text-xl`, `font-semibold`, `tracking-tight` |
| **Tagline** | “Your legal companion” in JSX; **`uppercase`** + `tracking-[0.16em]`, `text-[10px]` `font-semibold`, `text-gray-500` / `dark:text-gray-400`, `hidden` below `sm`, `sm:block` |

**Landing only:** inner padding on the glass bar: `px-4 py-2.5 sm:px-5 sm:py-3 lg:px-6`.

---

## Fonts (`tailwind.config.js`)

- **`font-display`** → Playfair Display (landing wordmark).
- **`font-sans`** → Outfit (default body / Layout text).
