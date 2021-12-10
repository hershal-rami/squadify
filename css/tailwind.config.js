const colors = require("tailwindcss/colors");

module.exports = {
    content: [
        "../squadify/templates/**/*.html"
    ],
    theme: {
        extend: {
            fontFamily: {
                "sans": "Inter"
            }
        },
    },
    plugins: [
        require("@tailwindcss/forms")
    ],
}
