# BeAstar Mobile — React Native (Expo) Scaffold

Calls the FastAPI backend end to end: signup → face verification → photo
upload → generation → status polling → share screen with QR code →
leaderboard.

## What's here

- **`App.tsx`** — root component, wires i18n + auth context + navigation
- **`src/api/client.ts`** — one typed function per backend endpoint,
  matching `app/main.py`'s Pydantic models field-for-field
- **`src/context/AuthContext.tsx`** — session state (user id persisted via
  `expo-secure-store`)
- **`src/navigation/AppNavigator.tsx`** — typed stack navigator, routes to
  Signup or Create depending on whether a session exists
- **`src/screens/`** — Signup, VerifyFace (camera capture), Create
  (scenario + resolution picker + photo upload + generate), 
  GenerationStatus (polls the job), Share (QR code + native share sheet),
  Leaderboard
- **`src/i18n/`** — i18next setup with the same English/Tagalog catalogs
  as the backend

## Honest verification note

There's no network access in the environment this was built in, so
`npm install` and a real `tsc`/Metro build could not be run. Every file
was checked for structural syntax validity (balanced braces/parens/JSX),
but **you should run `npm install && npx tsc --noEmit` yourself before
treating this as verified** — that's a real gap, not a hidden one.

## Setup

```bash
npm install
npx expo start
```

Set your backend URL before running:

```bash
EXPO_PUBLIC_API_BASE_URL=https://your-api-domain.com npx expo start
```

## Known gaps (real, not hidden)

- **No video playback yet** — `ShareScreen` has a placeholder where
  `expo-av`'s `<Video>` component belongs; swapping it in is small but
  wasn't done here since it needs a real rendered video URL to test against.
- **No Stripe/GCash checkout screens yet** — the API client has
  `startGcashCheckout()` wired, but no screen calls it yet; the PayMongo
  checkout is a webview/redirect flow (`checkout_url`) that needs
  `expo-web-browser` or a WebView component.
- **No push notifications** — "your video is ready" today only works if
  the user stays on the GenerationStatus screen; a real app needs a push
  notification for renders that take longer, which means an Expo push
  token registration flow against a backend endpoint that doesn't exist yet.
- **No offline/error-boundary handling beyond basic try/catch** — fine for
  a scaffold, not fine for "commercial global platform."
- **App icons, splash art, and store listing assets** — none exist; these
  are design deliverables, not code.
- **Dream-thread update videos pass through as local file URIs** — 
  `PostDreamUpdateScreen` doesn't yet upload the video to storage first;
  it needs the same upload-then-get-URL pattern as `uploadSelfie` in
  `api/client.ts`, which wasn't built as part of this feature yet.
- **`isFollowing` state in `DreamThreadScreen` is local-only** — the
  backend's follow/unfollow endpoints don't return the caller's current
  follow status yet, so this resets on screen reload. Needs a
  `GET .../is-following` endpoint or including it in the thread response.
