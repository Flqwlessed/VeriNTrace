                                              
                                                               
export async function startInvestigation(text       ,urls         ,update              )                                      {
 const response=await fetch('/api/investigate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,urls}),signal:AbortSignal.timeout(210000)});
 if(!response.ok){let message='Request failed ('+response.status+'). Check the server or deployment logs.';try{message=(await response.json()).error||message;}catch{}throw new Error(message);}
 if(!response.headers.get('Content-Type')?.includes('application/x-ndjson'))return response.json();
 if(!response.body)throw new Error('The server returned an empty response.');
 const reader=response.body.getReader(),decoder=new TextDecoder(),states                      ={};let buffer='',result                   =null;
 const consume=(line       )=>{if(!line.trim())return;const event=JSON.parse(line);if(event.type==='stage'){states[event.stage]=event.state;update({...states});}if(event.type==='result')result=event.result;if(event.type==='error')throw new Error(event.error);};
 try{while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop() ;for(const line of lines)consume(line);}buffer+=decoder.decode();consume(buffer);}finally{reader.releaseLock();}
 if(!result)throw new Error('The investigation ended before a report arrived. The function may have timed out; retry or inspect the deployment logs.');
 return result;
}
