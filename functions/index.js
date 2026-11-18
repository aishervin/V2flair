import { handleSubscription } from "./_lib/sub.js";

// https://subshen.pages.dev/ is dual-purpose, exactly like /sub:
//   • browser  -> index.html (demo + redirect)
//   • client   -> base64 subscription
export const onRequest = (context) => handleSubscription(context);
