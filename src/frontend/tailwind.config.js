/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class', // Enable class-based dark mode
    theme: {
        extend: {
            colors: {
                /** Panel / card / chrome borders — from `index.css` :root & `.dark` */
                lex: {
                    DEFAULT: 'var(--lex-border)',
                    strong: 'var(--lex-border-strong)',
                },
                // Dark Mode
                dark: {
                    bg: '#242424',
                    card: '#1a1a1a',
                    text: 'rgba(255, 255, 255, 0.87)',
                },
                // Light Mode
                light: {
                    bg: '#ffffff',
                    card: '#f9f9f9',
                    text: '#213547',
                },
                // Accents
                primary: {
                    DEFAULT: '#646cff', // Indigo
                    hover: '#535bf2',   // Violet
                }
            },
            fontFamily: {
                sans: ['Outfit', 'Inter', 'system-ui', 'Avenir', 'Helvetica', 'Arial', 'sans-serif'],
                display: ['"Playfair Display"', 'Georgia', 'Cambria', 'Times New Roman', 'serif'],
            },
            /** Panel / card radius — match Bar question cards (`rounded-lg` = 0.5rem) app-wide */
            borderRadius: {
                md: '0.5rem',
                xl: '0.5rem',
                '2xl': '0.5rem',
                '3xl': '0.5rem',
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}
