import test from "node:test";
import assert from "node:assert/strict";
import edge from "../src/asset-edge.js";
test("HTTP aliases upgrade to HTTPS before any asset access; foreign hosts cannot become redirect targets", async () => {
  let calls=0;
  const env={ASSETS:{fetch(){calls++;throw new Error("Must not reach assets on HTTP");}}};
  for(const host of ["poststeward.com","www.poststeward.com","outside.example"]){
    const response=await edge.fetch(new Request(`http://${host}/install/?mode=read`),env);
    assert.equal(response.status,301);
    assert.equal(response.headers.get("location"),`https://${host==='outside.example'?'poststeward.com':host}/install/?mode=read`);
  }
  assert.equal(calls,0);
});
test("HTTPS streams the unchanged asset response and preserves method, errors and security headers", async () => {
  for(const method of ["GET","HEAD"]){
    const request=new Request("https://poststeward.com/missing",{method});
    const original=new Response(method==='HEAD'?null:'Not found',{status:404,headers:{"Content-Security-Policy":"default-src 'self'","X-Content-Type-Options":"nosniff"}});
    const response=await edge.fetch(request,{ASSETS:{fetch(actual){assert.equal(actual,request);return original;}}});
    assert.equal(response,original);
  }
});
