/** HTTPS upgrade only; every HTTPS request retains the static asset service. */
export default {
  /** @param {Request} request @param {Env} env */
  fetch(request, env) {
    const url = new URL(request.url);
    if (url.protocol === "http:") {
      url.protocol = "https:";
      if (!["poststeward.com", "www.poststeward.com"].includes(url.hostname)) url.host = "poststeward.com";
      return new Response(null, {status:301,headers:{Location:url.href,"Strict-Transport-Security":"max-age=31536000; includeSubDomains","X-Content-Type-Options":"nosniff"}});
    }
    return env.ASSETS.fetch(request);
  },
};
