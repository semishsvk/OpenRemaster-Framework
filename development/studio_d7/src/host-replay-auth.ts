/** UI-014 exact SOURCE identity layer above the original Inspector wire validator.
 *
 * validateArchivedHost verifies protocol structure but allows a different
 * source report with still-well-formed checkpoint strings. We only replay
 * ONE frozen, SHA-pinned archived Windows pilot. A mutated checkpoint body
 * is never treated as authenticated by the structural wire schema.
 *
 * No host processes or network calls. Local archive identity is not an
 * independent publisher, current Owner, or fresh Witness signature.
 */
import frozen from "./data/host-connector-evidence.json" with {type:"json"};
import {validateArchivedHost,type ArchivedHostReport} from "./host-connector.ts";
export const EXACT_HOST_REPLAY_SOURCE_SHA256 =
 "39316fadd308cf6897949a77d3c7ad65cfa431fa6abdc21d10f8f1fa51202f35";
const exactJson=JSON.stringify(frozen);
export function validatePinnedHostReplay(v:unknown):v is ArchivedHostReport{
 if(!validateArchivedHost(v))return false;
 try{return JSON.stringify(v)===exactJson;}catch{return false;}
}
export function pinnedHostReplayView(v:unknown){
 return validatePinnedHostReplay(v)
  ?{status:"ARCHIVED_ONLY" as const,report:v}
  :{status:"SOURCE_REJECTED_HOLD" as const,report:null};
}
