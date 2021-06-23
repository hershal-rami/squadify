const colors = require("tailwindcss/colors");

module.exports = {
    purge: {
        enabled: true,
        content: [
            "../squadify/templates/*.html"
        ],
    },
    darkMode: false,
    theme: {
        extend: {
            colors: {
                gray: colors.gray,
                green: colors.green,
            }
        },
    },
    variants: {},
    plugins: [
        require("@tailwindcss/forms")
    ],
}
