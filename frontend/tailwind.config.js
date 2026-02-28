/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            keyframes: {
                shine: {
                    '0%': { backgroundPosition: '200% center' },
                    '100%': { backgroundPosition: '-200% center' },
                }
            },
            animation: {
                shine: 'shine 1.5s linear infinite',
            }
        },
    },
    plugins: [],
}
