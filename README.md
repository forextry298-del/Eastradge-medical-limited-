# Eastradge Capital Investment Platform

This package contains the supplied single-page HTML application prepared for deployment as a Render Static Site.

## Contents

- `index.html` — original uploaded application, preserved as the entry page
- `render.yaml` — Render Blueprint for a static site
- `README.md` — deployment notes

## Deploy on Render

1. Create a new GitHub repository named `eastradge-capital`.
2. Extract this ZIP and upload/push the files in this folder to the repository root.
3. In Render, choose **New + → Blueprint** and connect the repository, or create a **Static Site** from it.
4. If using the Blueprint, Render reads `render.yaml`. If creating a Static Site manually:
   - Build command: leave blank
   - Publish directory: `.`
5. Deploy.

## Important application configuration

The uploaded HTML imports Firebase SDK modules and expects Firebase configuration to be supplied through the variables `__firebase_config` and optionally `__initial_auth_token`. Those variables are not included in this ZIP. Therefore, publishing the static files alone does not configure Firebase authentication or cloud database access.

Before using real accounts or storing investor/customer information, connect your own Firebase project and configure Firebase Authentication and Firestore security rules. Do not place private service-account credentials in the HTML.

The page also contains an AI advisor request with an empty API key. Do not expose a private Gemini API key in client-side HTML; use a secured server-side endpoint if you want that feature enabled.

This package only prepares the supplied page for hosting. It does not verify investment claims, payment instructions, account security, or backend transaction processing.
