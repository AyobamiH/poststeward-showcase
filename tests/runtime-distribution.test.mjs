import assert from "node:assert/strict";
import { test } from "node:test";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { syncRuntimeRelease } from "../scripts/sync-runtime-release.mjs";

const revision = "a".repeat(40);
const installer = '#!/usr/bin/env bash\n# https://app.poststeward.com runtime_tree_sha256\n';
function fixture(overrides = {}) {
  return async url => {
    const value = String(url);
    if (value.includes("/contents/")) return Response.json({type:"file",encoding:"base64",content:Buffer.from(installer).toString("base64")});
    if (value.endsWith("/install.sh")) return new Response(overrides.installer || installer);
    if (value.endsWith("/health")) return Response.json({status:"ok",release:overrides.healthRevision || revision});
    const channel = value.includes("beta.json") ? "beta" : "stable";
    return Response.json({schema_version:1,product:"poststeward",channel,revision,runtime_tree_sha256:"b".repeat(64),
      expires_at:new Date(Date.now()+86400000).toISOString(),archive:`https://github.com/AyobamiH/poststeward/archive/${revision}.tar.gz`,...overrides.manifest});
  };
}
test("distribution copies the exact live/source installer and both channel identities",async()=>{
  const root=await mkdtemp(join(tmpdir(),"poststeward-dist-"));
  try{
    const result=await syncRuntimeRelease({send:fixture(),output:pathToFileURL(root+"/"),expected:revision});
    assert.equal(result.revision,revision);
    assert.equal(await readFile(join(root,"install.sh"),"utf8"),installer);
    assert.equal(JSON.parse(await readFile(join(root,"releases/beta.json"),"utf8")).channel,"beta");
  }finally{await rm(root,{recursive:true,force:true});}
});
test("distribution rejects release drift, expiry, foreign archives and changed deployed installer",async()=>{
  for(const overrides of [{healthRevision:"c".repeat(40)},{manifest:{expires_at:"2000-01-01T00:00:00Z"}},
    {manifest:{archive:"https://example.com/runtime.tar.gz"}},{installer:"#!/bin/sh\necho changed\n"}]){
    const root=await mkdtemp(join(tmpdir(),"poststeward-dist-"));
    try{
      await assert.rejects(syncRuntimeRelease({send:fixture(overrides),output:pathToFileURL(root+"/"),expected:revision}));
      await assert.rejects(readFile(join(root,"install.sh")));
    }finally{await rm(root,{recursive:true,force:true});}
  }
});
