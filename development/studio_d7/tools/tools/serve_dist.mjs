import http from "node:http";
import {canonicalRoute} from "./canonical_proxy.mjs";
import fs from "node:fs/promises";
import path from "node:path";
import assert from "node:assert/strict";
import crypto from "node:crypto";

const base = path.resolve(import.meta.dirname, "..");
const dist = path.join(base, "dist");
const LOCAL_CAPTURE_FILE = path.join(base, "src", "data", "inspector-observation.json");
const CROSSPLANE_CAPTURE_FILE = path.join(base, "src", "data", "crossplane-observation.json");
const BOUNDED_CAPTURE_FILE = path.join(base, "src", "data", "bounded-plan-evidence.json");
const GAME_COMPLETION_CAPTURE_FILE = path.join(base,"src","data","game-completion-board.json");
const GAME_COMPLETION_SHA256 = "c4cfe09b4ddc35094f490d3a79b817d26dddab6ba0d69e52b3810159f4909e5c";
const HOST_REPLAY_CAPTURE_FILE = path.join(base,"src","data","host-connector-evidence.json");
const HOST_REPLAY_SHA256 = "39316fadd308cf6897949a77d3c7ad65cfa431fa6abdc21d10f8f1fa51202f35";
const contentTypes = {
  ".png": "image/png", ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
};
const csp = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-src 'none'; base-uri 'none'";
const dataUrl = "/api/inspector/snapshot";
const crossplaneUrl = "/api/crossplane/snapshot";
const boundedUrl = "/api/bounded-plan/snapshot";
const gameCompletionUrl = "/api/game-completion/snapshot";
const hostReplayUrl = "/api/host-replay/snapshot";
const nodeNoticeUrl = "/notices/node-v24.19.0-LICENSE.txt";
const noticeFile = path.join(dist,"notices","node-v24.19.0-LICENSE.txt");
const noticeSHA256 = "d9c4eeda951d6d08f4aa1316b61aafcf67e6da5f79b18f8edeb56fa6abdc038c";
// This server NEVER invokes the Inspector Host or any process. It only serves a
// fixed operator-created read-only projection and prebuilt frontend assets.
const server = http.createServer(async (req, res) => {
  const port = server.address()?.port;
  const host = req.headers.host ?? "";
  const accepted = host === "127.0.0.1:" + port || host === "localhost:" + port;
  if (!accepted || req.headers["sec-fetch-site"] === "cross-site") {
    res.writeHead(403); res.end("Forbidden"); return;
  }
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { Allow: "GET, HEAD" }); res.end("Method not allowed"); return;
  }
  if (await canonicalRoute(req,res)) return;
  const raw = (req.url ?? "/").split("?")[0];
  const storedFiles = {"/stored/inspector-observation.json": "inspector-observation.json", "/stored/crossplane-observation.json": "crossplane-observation.json", "/stored/bounded-plan-evidence.json": "bounded-plan-evidence.json", "/stored/game-completion-board.json": "game-completion-board.json", "/stored/host-connector-evidence.json": "host-connector-evidence.json"};
  const storedFile = !String(req.url).includes('?') ? storedFiles[raw] : undefined;
  const isCoreOrion = (raw === "/api/core-orion/snapshot" || raw === "/core-orion-observation.json") && !String(req.url).includes("?");
  const isData = (storedFile === "inspector-observation.json" || raw === dataUrl) && !String(req.url).includes("?");
  const isCrossplane = (storedFile === "crossplane-observation.json" || raw === crossplaneUrl) && !String(req.url).includes("?");
  const isBounded = (storedFile === "bounded-plan-evidence.json" || raw === boundedUrl) && !String(req.url).includes("?");
  const isGameCompletion = (storedFile === "game-completion-board.json" || raw === gameCompletionUrl) && !String(req.url).includes("?");
  const isHostReplay = (storedFile === "host-connector-evidence.json" || raw === hostReplayUrl) && !String(req.url).includes("?");
  const isNotice = raw === nodeNoticeUrl && !String(req.url).includes("?");
  const staticAllowed = raw === "/" || raw === "/index.html" || raw === "/favicon.png" || /^\/assets\/[A-Za-z0-9._-]+\.(js|css|png)$/.test(raw);
  if (!isCoreOrion && !isData && !isCrossplane && !isBounded && !isGameCompletion && !isHostReplay && !isNotice && !staticAllowed) { res.writeHead(404); res.end("Not found"); return; }
  const file = storedFile ? path.join(dist,'stored',storedFile) : isCoreOrion ? path.join(base,"src/data/core-orion-observation.json") : isData ? LOCAL_CAPTURE_FILE : isCrossplane ? CROSSPLANE_CAPTURE_FILE : isBounded ? BOUNDED_CAPTURE_FILE : isGameCompletion ? GAME_COMPLETION_CAPTURE_FILE : isHostReplay ? HOST_REPLAY_CAPTURE_FILE : isNotice ? noticeFile : path.join(dist, raw === "/" ? "index.html" : raw.slice(1));
  try {
    const data = await fs.readFile(file);
    if (data.length > (isCoreOrion ? 8192 : isHostReplay ? 40000 : isGameCompletion ? 32000 : isBounded ? 32768 : isData || isCrossplane ? 131072 : isNotice ? 260000 : 2_000_000)) throw Error("Oversize");
    if (isGameCompletion && crypto.createHash("sha256").update(data).digest("hex")!==GAME_COMPLETION_SHA256) throw Error("GAME_COMPLETION_HASH_DRIFT");
    if (isHostReplay && crypto.createHash("sha256").update(data).digest("hex")!==HOST_REPLAY_SHA256) throw Error("HOST_REPLAY_HASH_DRIFT");
    if (isNotice && crypto.createHash("sha256").update(data).digest("hex") !== noticeSHA256) throw Error("NOTICE_HASH_CHANGED");
    res.writeHead(200, {
      "Content-Type": isNotice ? "text/plain; charset=utf-8" : contentTypes[path.extname(file)] || "application/octet-stream",
      "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
      "Content-Security-Policy": csp, "Referrer-Policy": "no-referrer",
      "X-Frame-Options": "DENY", "Cross-Origin-Resource-Policy": "same-origin",
    });
    res.end(req.method === "HEAD" ? undefined : data);
  } catch { res.writeHead(404); res.end("Not found"); }
});
const selfTest = process.argv.includes("--self-test");
server.listen(0, "127.0.0.1", async () => {
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : 1421;
  if (!selfTest) {
    console.log(JSON.stringify({port}));
    return;
  }
  try {
    const host = "http://127.0.0.1:" + port;
    const ok = await fetch(host + "/");
    assert.equal(ok.status, 200);
    assert.match(await ok.text(), /OpenRemaster Studio/);
    const data = await fetch(host + dataUrl);
    assert.equal(data.status, 200);
    const projection = await data.json();
    assert.equal(projection.schema, "OpenRemaster.StudioInspectorCapture.v1");
    assert.equal(projection.productionAdmission, "HOLD");
    assert.equal(projection.dispatchAuthorized, false);
    const cp = await fetch(host + crossplaneUrl);
    assert.equal(cp.status, 200);
    const crossplane = await cp.json();
    assert.equal(crossplane.schema, "OpenRemaster.StudioCrossplaneCapture.v1");
    assert.equal(crossplane.productionAdmission, "HOLD");
    assert.equal(crossplane.dispatchAuthorized, false);
    assert.equal(crossplane.modelInvocationAuthorized, false);
    const cpPost=await fetch(host + crossplaneUrl,{method:"POST"});
    assert.equal(cpPost.status,405);
    const cpQuery=await fetch(host + crossplaneUrl + "?path=../../secrets");
    assert.equal(cpQuery.status,404);
    const cpCross=await fetch(host + crossplaneUrl,{headers:{"Sec-Fetch-Site":"cross-site"}});
    assert.equal(cpCross.status,403);
    const notice = await fetch(host + nodeNoticeUrl);
    assert.equal(notice.status,200);
    assert.match(notice.headers.get("content-type")||"",/text\/plain/);
    assert.equal(crypto.createHash("sha256").update(Buffer.from(await notice.arrayBuffer())).digest("hex"),noticeSHA256);
    const noticeHead = await fetch(host + nodeNoticeUrl,{method:"HEAD"});
    assert.equal(noticeHead.status,200); assert.equal(await noticeHead.text(),"");
    const noticePost=await fetch(host + nodeNoticeUrl,{method:"POST"});
    assert.equal(noticePost.status,405);
    const noticeQuery=await fetch(host + nodeNoticeUrl + "?filename=../secret");
    assert.equal(noticeQuery.status,404);
    const noticeCrossSite=await fetch(host + nodeNoticeUrl,{headers:{"Sec-Fetch-Site":"cross-site"}});
    assert.equal(noticeCrossSite.status,403);
    const task=await fetch(host + boundedUrl);
    assert.equal(task.status,200);
    const taskBody=await task.json();
    assert.equal(taskBody.schema,"OpenRemaster.StudioBoundedPlanEvidence.v1");
    assert.equal(taskBody.productionAdmission,"HOLD_NO_AUTO_RETRY");
    assert.equal(taskBody.dispatchAuthorized,false);
    assert.equal(taskBody.workerStartAuthorized,false);
    const taskHead=await fetch(host+boundedUrl,{method:"HEAD"});
    assert.equal(taskHead.status,200);assert.equal(await taskHead.text(),"");
    const taskPost=await fetch(host+boundedUrl,{method:"POST"});
    assert.equal(taskPost.status,405);
    const taskQuery=await fetch(host+boundedUrl+"?path=../../private");
    assert.equal(taskQuery.status,404);
    const taskCross=await fetch(host+boundedUrl,{headers:{"Sec-Fetch-Site":"cross-site"}});
    assert.equal(taskCross.status,403);
    const gameSnapshot=await fetch(host+gameCompletionUrl);
    assert.equal(gameSnapshot.status,200);
    const gameBody=Buffer.from(await gameSnapshot.arrayBuffer());
    assert.equal(crypto.createHash("sha256").update(gameBody).digest("hex"),GAME_COMPLETION_SHA256);
    const gameSource=JSON.parse(gameBody.toString("utf8"));
    assert.equal(gameSource.schema,"OpenRemaster.StudioGameCompletionReadiness.v1");
    assert.equal(gameSource.policy.productionAdmission,"HOLD_NO_AUTO_RETRY");
    assert.equal(gameSource.policy.gameDispatch,false);
    assert.equal(gameSource.firstDivergence.validEventPairs,0);
    assert.equal(gameSource.games.length,2);
    assert.equal(gameSource.games.reduce((sum,g)=>sum+g.taskGraph.length,0),9);
    const gameHead=await fetch(host+gameCompletionUrl,{method:"HEAD"});
    assert.equal(gameHead.status,200);assert.equal(await gameHead.text(),"");
    const gamePost=await fetch(host+gameCompletionUrl,{method:"POST"});
    assert.equal(gamePost.status,405);
    const gameQuery=await fetch(host+gameCompletionUrl+"?file=../../game");
    assert.equal(gameQuery.status,404);
    const gameCross=await fetch(host+gameCompletionUrl,{headers:{"Sec-Fetch-Site":"cross-site"}});
    assert.equal(gameCross.status,403);
    const historicalHost=await fetch(host+hostReplayUrl);
    assert.equal(historicalHost.status,200);
    const historicalData=Buffer.from(await historicalHost.arrayBuffer());
    assert.equal(crypto.createHash("sha256").update(historicalData).digest("hex"),HOST_REPLAY_SHA256);
    const archived=JSON.parse(historicalData.toString("utf8"));
    assert.equal(archived.schema,"OpenRemaster.StudioHostConnectorOfflineFixture.v1");
    assert.equal(archived.security.liveHostConnected,false);
    assert.equal(archived.responseFixtures.length,6);
    const hostHead=await fetch(host+hostReplayUrl,{method:"HEAD"});
    assert.equal(hostHead.status,200);assert.equal(await hostHead.text(),"");
    const hostPost=await fetch(host+hostReplayUrl,{method:"POST"});
    assert.equal(hostPost.status,405);
    const hostQuery=await fetch(host+hostReplayUrl+"?path=../../private");
    assert.equal(hostQuery.status,404);
    const hostCross=await fetch(host+hostReplayUrl,{headers:{"Sec-Fetch-Site":"cross-site"}});
    assert.equal(hostCross.status,403);
    const forbidden = await fetch(host + "/not-in-allowlist");
    assert.equal(forbidden.status, 404);
    const method = await fetch(host + dataUrl, { method: "POST" });
    assert.equal(method.status, 405);
    const crossSite = await fetch(host + dataUrl, { headers: { "Sec-Fetch-Site": "cross-site" } });
    assert.equal(crossSite.status, 403);
    const evilHostStatus = await new Promise((resolve, reject) => {
      const req = http.request(host + dataUrl, { headers: { Host: "evil.example:1421" } }, res => {
        res.resume(); resolve(res.statusCode);
      });
      req.on("error", reject); req.end();
    });
    assert.equal(evilHostStatus, 403);
    const unknown = await fetch(host + dataUrl + "?file=../../secret");
    assert.equal(unknown.status, 404);
    const head = await fetch(host + dataUrl, { method: "HEAD" });
    assert.equal(head.status, 200);
    assert.equal(await head.text(), "");
    for(const file of ['inspector-observation.json','crossplane-observation.json','bounded-plan-evidence.json','game-completion-board.json','host-connector-evidence.json']){
      const url=host+'/stored/'+file;
      const response=await fetch(url);assert.equal(response.status,200);
      assert.equal(crypto.createHash('sha256').update(Buffer.from(await response.arrayBuffer())).digest('hex'),crypto.createHash('sha256').update(await fs.readFile(path.join(dist,'stored',file))).digest('hex'));
      const h=await fetch(url,{method:'HEAD'});assert.equal(h.status,200);assert.equal(await h.text(),'');
      assert.equal((await fetch(url,{method:'POST'})).status,405);
      assert.equal((await fetch(url+'?path=other')).status,404);
    }
    console.log("STORED_ASSET_FIVE_ROUTES_GET_HEAD_POST_QUERY_PASS");
    console.log("LOOPBACK_CAPTURE_READONLY_SELF_TEST_PASS");
  } catch (error) { console.error(error); process.exitCode = 2; }
  finally { server.close(); }
});
