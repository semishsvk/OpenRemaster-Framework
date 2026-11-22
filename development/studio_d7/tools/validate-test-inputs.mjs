import {readR8Fixture} from '../tests/support/r8-fixtures.mjs';
import {validateDependencies,dependency,projectRoot} from '../tests/support/local-dependencies.mjs';
for(const name of ['r1.json','r2-wal.json','studio-wal.json'])readR8Fixture(name);
validateDependencies();dependency('typescript');dependency('react');dependency('react-dom/server');
console.log(JSON.stringify({state:'PASS_EXACT_PROJECT_TEST_INPUTS',projectRoot,cwd:process.cwd(),fixtures:3}));
