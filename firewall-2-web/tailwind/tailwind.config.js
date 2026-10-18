/**
 * Tailwind build config for the Aurelian Dynamics portal.
 *
 * This is a BUILD-TIME artifact only. The compiled, minified output is
 * committed to static/css/app.css and shipped with the app, so the running
 * container needs no Node toolchain and no network access.
 *
 * To rebuild the stylesheet (optional):
 *   cd firewall-1-web
 *   npm install
 *   npm run build:css
 */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
