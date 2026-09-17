import type {Investigation} from './types.js';
import {api} from './ui.js';
export type HistoryRow = {id:string;claim:string;verdict:string;createdAt:string;demo:boolean;sourceCount:number};
let browserStorage=false;
export function configureHistory(browser:boolean){browserStorage=browser;}
function open():Promise<IDBDatabase>{return new Promise((resolve,reject)=>{const request=indexedDB.open('veritrace-history',1);request.onupgradeneeded=()=>{request.result.createObjectStore('reports',{keyPath:'id'});};request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(new Error('Browser history is unavailable. Export this report before closing.'));request.onblocked=()=>reject(new Error('Close other VeriTrace tabs to enable browser history.'));});}
export async function saveReport(report:Investigation):Promise<void>{
 if(!browserStorage)return;
 const db=await open();
 try{await new Promise<void>((resolve,reject)=>{const tx=db.transaction('reports','readwrite');tx.objectStore('reports').put(report);tx.oncomplete=()=>resolve();tx.onerror=()=>reject(new Error('Could not save browser history. Export this report before closing.'));tx.onabort=()=>reject(new Error('History save was interrupted. Export the report.'));});}finally{db.close();}
}
export async function listHistory():Promise<HistoryRow[]>{
 if(!browserStorage)return api<HistoryRow[]>('/api/history');
 const db=await open();try{return await new Promise((resolve,reject)=>{const request=db.transaction('reports').objectStore('reports').getAll();request.onsuccess=()=>resolve((request.result as Investigation[]).sort((a,b)=>b.createdAt.localeCompare(a.createdAt)).slice(0,50).map(r=>({id:r.id,claim:r.claim,verdict:r.verdict,createdAt:r.createdAt,demo:r.demo,sourceCount:r.evidence.length})));request.onerror=()=>reject(new Error('Unable to read browser history.'));});}finally{db.close();}
}
export async function getReport(id:string):Promise<Investigation>{
 if(!browserStorage)return api<Investigation>('/api/history/'+id);
 const db=await open();try{return await new Promise((resolve,reject)=>{const request=db.transaction('reports').objectStore('reports').get(id);request.onsuccess=()=>request.result?resolve(request.result):reject(new Error('Report not found in this browser.'));request.onerror=()=>reject(new Error('Unable to read this report.'));});}finally{db.close();}
}
