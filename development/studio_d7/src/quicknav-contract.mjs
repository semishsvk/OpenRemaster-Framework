// Framework-independent keyboard behavior contract for actual unit tests.
export function findQuickLinks(items,query){
 const q=query.trim().toLocaleLowerCase();
 return q?items.filter(x=>(x.name+" "+x.id).toLocaleLowerCase().includes(q)).slice(0,7):[];
}
export function quickKeyAction(key,index,length){
 if(key==="Escape")return {kind:"clear",index:0};
 if(length<1)return {kind:"none",index:0};
 if(key==="ArrowDown")return {kind:"move",index:(index+1)%length};
 if(key==="ArrowUp")return {kind:"move",index:(index-1+length)%length};
 if(key==="Enter")return {kind:"select",index:Math.min(index,length-1)};
 return {kind:"none",index};
}
