import {useEffect,useRef,useState,type KeyboardEvent} from "react";
import {findQuickLinks,quickKeyAction,type QuickLink} from "./quicknav-logic";
export default function QuickNavigation({items,onNavigate}:{items:readonly QuickLink[];onNavigate:(id:string)=>void}){
 const [query,setQuery]=useState("");
 const [active,setActive]=useState(0);
 const [open,setOpen]=useState(false);
 const input=useRef<HTMLInputElement>(null);
 const matches=findQuickLinks(items,query);
 const visible=open && query.trim().length>0;
 const select=(item:QuickLink)=>{onNavigate(item.id);setQuery("");setActive(0);setOpen(false);input.current?.focus();};
 useEffect(()=>{
  const shortcut=(event:globalThis.KeyboardEvent)=>{
   if((event.ctrlKey||event.metaKey)&&!event.altKey&&!event.isComposing&&event.key.toLowerCase()==='k'){
    event.preventDefault();input.current?.focus();input.current?.select();setOpen(true);
   }
  };
  window.addEventListener('keydown',shortcut);return()=>window.removeEventListener('keydown',shortcut);
 },[]);
 const onKeyDown=(event:KeyboardEvent<HTMLInputElement>)=>{
  const action=quickKeyAction(event.key,active,visible?matches.length:0);
  if(action.kind==="clear"){event.preventDefault();setQuery("");setActive(0);setOpen(false);}
  if(action.kind==="move"){event.preventDefault();setActive(action.index);}
  if(action.kind==="select"){event.preventDefault();select(matches[action.index]);}
 };
 return <section className="ux-quick-nav" aria-label="Quick navigation" onBlur={event=>{if(!event.currentTarget.contains(event.relatedTarget))setOpen(false);}}>
  <label htmlFor="ux-page-search">Find a Studio page</label>
  <input ref={input} id="ux-page-search" type="search" role="combobox" aria-autocomplete="list" aria-expanded={visible&&matches.length>0} aria-controls={visible&&matches.length?"ux-page-results":undefined} aria-activedescendant={visible&&matches.length?"ux-page-option-"+Math.min(active,matches.length-1):undefined} value={query} onFocus={()=>setOpen(true)} onChange={e=>{setQuery(e.target.value);setActive(0);setOpen(true);}} onKeyDown={onKeyDown} placeholder="Search tools… (Ctrl+K)" autoComplete="off"/>
  {visible&&matches.length>0&&<div id="ux-page-results" role="listbox" aria-label="Matching pages" className="ux-quick-results">
   {matches.map((item,i)=><button id={"ux-page-option-"+i} role="option" aria-selected={i===active} type="button" key={item.id} onClick={()=>select(item)}>{item.name}</button>)}
  </div>}
  {visible&&!matches.length&&<p role="status">No matching pages</p>}
 </section>;
}
