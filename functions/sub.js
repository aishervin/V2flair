import { handleSubscription } from "./_lib/sub.js";

export const onRequest = (context) => handleSubscription(context);
