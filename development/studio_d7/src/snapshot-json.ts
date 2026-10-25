/** Validate bounded JSON syntax and unique decoded keys before materializing it. */
export function parseSnapshotJson(text: string): unknown {
  if (new TextEncoder().encode(text).byteLength > 1_048_576) throw Error('SNAPSHOT_SIZE');
  let i=0,nodes=0;
  const space=()=>{while(/[\x20\t\r\n]/.test(text[i]??'!'))i++;};
  function string(): string {
    const start=i;
    if(text[i++]!=='"')throw Error('JSON_STRING');
    while(i<text.length){
      const ch=text[i++];
      if(ch==='\\'){i++;continue;}
      if(ch==='"')return JSON.parse(text.slice(start,i)) as string;
    }
    throw Error('JSON_STRING');
  }
  function value(depth: number): void {
    if(depth>16 || ++nodes>20_000)throw Error('SNAPSHOT_COMPLEXITY');
    space();const ch=text[i];
    if(ch==='{'){
      i++;space();const seen=new Set<string>();
      if(text[i]==='}'){i++;return;}
      while(true){
        const key=string();if(seen.has(key))throw Error('DUPLICATE_JSON_KEY');seen.add(key);
        space();if(text[i++]!==':')throw Error('JSON_COLON');value(depth+1);space();
        if(text[i]==='}'){i++;return;}
        if(text[i++]!==',')throw Error('JSON_OBJECT');space();
      }
    }
    if(ch==='['){
      i++;space();if(text[i]===']'){i++;return;}
      while(true){value(depth+1);space();if(text[i]===']'){i++;return;}if(text[i++]!==',')throw Error('JSON_ARRAY');}
    }
    if(ch==='"'){string();return;}
    const token=/^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(text.slice(i));
    if(!token)throw Error('JSON_VALUE');
    const parsed: unknown=JSON.parse(token[0]);
    if(typeof parsed==='number' && !Number.isFinite(parsed))throw Error('JSON_NONFINITE');
    i+=token[0].length;
  }
  value(0);space();if(i!==text.length)throw Error('JSON_TRAILING');
  return JSON.parse(text) as unknown;
}
