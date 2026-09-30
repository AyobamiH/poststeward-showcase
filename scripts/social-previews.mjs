export const origin = "https://poststeward.com";
export const imagePath = "/social/poststeward-v2.png";
export const imageAlt = "PostSteward — Approved publishing. Clear results. For humans and AI agents.";
export const pages = [
  { path: "/", file: "index.html", title: "PostSteward — Approved publishing for AI agents", description: "Give your agents approved copy, connected accounts and a schedule. PostSteward checks their authority and keeps delivery receipts." },
  { path: "/install/", file: "install/index.html", title: "Install PostSteward", description: "Install the Linux runtime, pair your machine with PostSteward Cloud and review activation before local publishing." },
  { path: "/onboarding/", file: "onboarding/index.html", title: "Get started — PostSteward", description: "Set up a workspace, connect an account and review your first post. Add an agent or local runtime when needed; keep control of approval and delivery results." },
  { path: "/agent-guide/", file: "agent-guide/index.html", title: "Agent setup guide — PostSteward", description: "Connect an agent through scoped HTTP, remote MCP or supported browser WebMCP. Understand the 34 operations, owner approval and delivery evidence." },
  { path: "/privacy/", file: "privacy/index.html", title: "Privacy policy — PostSteward", description: "How PostSteward uses, protects, retains and deletes service data, and how to request access or deletion." },
  { path: "/terms/", file: "terms/index.html", title: "Terms of service — PostSteward", description: "Terms for using PostSteward, including agent authority, external providers, subscriptions and service limits." },
  { path: "/data-deletion/", file: "data-deletion/index.html", title: "Request data deletion — PostSteward", description: "How to request deletion of PostSteward workspace data and revoke connected social-provider access." },
  { path: "/workspace/", file: "workspace/index.html", title: "Workspace demo — PostSteward", description: "Explore an inert sample workspace with accounts, projects, reviewed campaigns and delivery receipts. No real posts, tokens or connections are created." },
];
export const attribute = value => value.replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll("'", "&#39;");
export function metadata(page) {
  const image = origin + imagePath;
  const entries = [
    ["name", "description", page.description],
    ["property", "og:type", "website"], ["property", "og:site_name", "PostSteward"],
    ["property", "og:locale", "en_GB"], ["property", "og:title", page.title],
    ["property", "og:description", page.description], ["property", "og:url", origin + page.path],
    ["property", "og:image", image], ["property", "og:image:secure_url", image],
    ["property", "og:image:type", "image/png"], ["property", "og:image:width", "1200"],
    ["property", "og:image:height", "630"], ["property", "og:image:alt", imageAlt],
    ["name", "twitter:card", "summary_large_image"], ["name", "twitter:title", page.title],
    ["name", "twitter:description", page.description], ["name", "twitter:image", image],
    ["name", "twitter:image:alt", imageAlt],
  ];
  return `<title>${attribute(page.title)}</title>\n<link rel="canonical" href="${origin + page.path}">\n` + entries.map(([kind, key, value]) => `<meta ${kind}="${key}" content="${attribute(value)}">`).join("\n");
}
