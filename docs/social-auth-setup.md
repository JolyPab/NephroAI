# Web social authentication setup

NephroAI supports Google and Facebook on the Angular `/auth` page. The browser
receives a short-lived provider credential and sends it to
`POST /api/auth/social`; the backend verifies it before issuing the NephroAI
JWT. Provider secrets must never be added to Angular environment files.

## Google

1. In Google Cloud Console, configure the OAuth consent screen.
2. Create an OAuth 2.0 Client ID with application type **Web application**.
3. Add the production JavaScript origins:
   - `https://app.nephroai.ec`
   - `https://app.nephroai.mx`
4. Add `http://localhost:4200` and/or `http://127.0.0.1:4200` only for local
   development.
5. Set the public web client ID in the server environment:

   ```dotenv
   GOOGLE_OAUTH_CLIENT_ID=1234567890-example.apps.googleusercontent.com
   ```

This flow uses the Google Identity Services ID token and does not require a
Google client secret in NephroAI.

Official references:

- <https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid>
- <https://developers.google.com/identity/gsi/web/guides/display-button>
- <https://developers.google.com/identity/sign-in/web/backend-auth>

## Facebook

1. Create a Meta app and add **Facebook Login** for the web.
2. Add `app.nephroai.ec` and `app.nephroai.mx` to the app domains and configure
   the corresponding HTTPS website URLs.
3. Enable Client OAuth Login, Web OAuth Login, and HTTPS enforcement.
4. Request only `public_profile` and `email`; the NephroAI UI does not request
   additional Facebook data.
5. Keep the app in development mode while testing with app roles/test users,
   then complete Meta's requirements before switching it live.
6. Set the server environment:

   ```dotenv
   FACEBOOK_APP_ID=1234567890
   FACEBOOK_APP_SECRET=replace-with-the-server-only-secret
   FACEBOOK_API_VERSION=v25.0
   ```

`FACEBOOK_APP_SECRET` is used only by the backend to validate the user access
token through Graph API and to generate `appsecret_proof`.

Official reference:

- <https://developers.facebook.com/docs/facebook-login/web>

## Deploy and smoke check

The variables are passed to the `api` container by `docker-compose.yml`. After
updating the production `.env`, rebuild/restart the API through the normal
deployment flow. Verify the public configuration without exposing secrets:

```bash
curl -fsS https://app.nephroai.ec/api/auth/social/config
```

Expected shape:

```json
{
  "googleClientId": "...apps.googleusercontent.com",
  "facebookAppId": "...",
  "facebookApiVersion": "v25.0"
}
```

The buttons are hidden when their corresponding public identifier is absent.
