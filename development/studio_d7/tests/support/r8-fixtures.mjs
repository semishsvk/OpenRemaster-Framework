import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const pins={
 'studio-wal.json':'e269079c273651c277c8fa31bd7d67bed102f8854927c625a127a54994c638c2',
 'r1.json':'39619dae718bbc4b3a20c6b659ef49e9419d1efd2ec27d5b9a77d72f19206554',
 'r2-wal.json':'2646a36b28108dacd6511f857adf7a18e099462bf5315cbeb2fde8bab86de4a6'
};
export function readR8Fixture(name){
 if(!Object.hasOwn(pins,name))throw Error('FIXTURE_NAME');
 let raw;try{raw=readFileSync(new URL('../fixtures/r8/'+name,import.meta.url));}catch{throw Error('FIXTURE_UNAVAILABLE '+name);}
 if(createHash('sha256').update(raw).digest('hex')!==pins[name])throw Error('FIXTURE_HASH '+name);
 return raw;
}
