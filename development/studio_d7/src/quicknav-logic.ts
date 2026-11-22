export type QuickLink={id:string;name:string};
export type QuickAction={kind:"clear"|"none"|"move"|"select";index:number};
export function findQuickLinks(items:readonly QuickLink[],query:string):QuickLink[]{
 const q=query.trim().toLocaleLowerCase();
 return q?items.filter(x=>(x.name+" "+x.id).toLocaleLowerCase().includes(q)).slice(0,7):[];
}
export function quickKeyAction(key:string,index:number,length:number):QuickAction{
 if(key==="Escape")return {kind:"clear",index:0};
 if(length<1)return {kind:"none",index:0};
 if(key==="ArrowDown")return {kind:"move",index:(index+1)%length};
 if(key==="ArrowUp")return {kind:"move",index:(index-1+length)%length};
 if(key==="Enter")return {kind:"select",index:Math.min(index,length-1)};
 return {kind:"none",index};
}
