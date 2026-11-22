import fs from 'node:fs';
import {syncBuiltinESMExports} from 'node:module';
import {resolve, sep} from 'node:path';
const allowed=resolve(process.env.TEMP);
const remove=fs.rmSync;
fs.rmSync=(path,options)=>{
  const target=resolve(String(path));
  if (!target.startsWith(allowed+sep)) throw Error('TEST_CLEANUP_OUTSIDE_PRIVATE_TEMP');
  return remove(path,options);
};
syncBuiltinESMExports();
