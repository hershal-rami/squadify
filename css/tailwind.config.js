const colors = require("tailwindcss/colors");

module.exports = {
    mode: "jit",
    purge: [
        "../squadify/templates/**/*.html"
    ],
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
