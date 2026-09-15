export const esc = (value         )         => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c] ));
export const date = (value               )         => value ? new Date(value).toLocaleDateString(undefined, {day:'numeric',month:'short',year:'numeric'}) : 'Date unknown';
export function link(url               , label = 'Read original source ↗')         {
 try { if (!url || !['http:', 'https:'].includes(new URL(url).protocol)) return '<span class="muted">No source URL · fictional demo</span>'; }
 catch { return '<span>No valid source URL</span>'; }
 return `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`;
}
export async function api   (path        , body         )             {
 const response = await fetch(path, {method: body ? 'POST' : 'GET', headers: body ? {'Content-Type':'application/json'} : {}, body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(20000)});
 const data = await response.json();
 if (!response.ok) throw new Error(data.error || 'Request failed. Please try again.');
 return data;
}
export const el =                                      (id        )    => document.getElementById(id)     ;
