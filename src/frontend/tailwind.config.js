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
            }
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}
