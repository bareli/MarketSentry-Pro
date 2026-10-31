function m(t,e,n){return e==null||Number.isNaN(e)?"\u2014":t==="outcome"?`${e.toFixed(1)}%`:t==="fx"?`${e.toFixed(4)}${n?` ${n}`:""}`:`${n==="USD"?"$":n?`${n} `:""}${e.toFixed(2)}`}function f(t,e,n){return t==="outcome"?n==null||Number.isNaN(n)?null:`${n>0?"+":""}${n.toFixed(1)}pp`:e==null||Number.isNaN(e)?null:`${e>0?"+":""}${e.toFixed(2)}%`}var R={pre:"Pre",regular:"Open",post:"After",closed:"Closed"};function _(t){return t&&R[t]||"Closed"}function g(t,e=new Date){if(t.kind==="outcome"){if(t.resolutionStatus==="resolved")return"Resolved";if(t.closed)return"Closed";if(t.endDate){let n=(new Date(t.endDate).getTime()-e.getTime())/36e5;if(n>=0&&n<=24)return"Closing soon"}return"Live"}return t.kind==="stock"?t.marketState&&t.marketState!=="closed"?"Open":"Closed":t.kind==="fx"?t.publishedDate&&new Date(t.publishedDate).toDateString()===e.toDateString()?"Updated today":"Stale":""}function k(t,e){return!e||e.length===0?t:t.filter(n=>e.includes(n.kind))}function w(t,e){if(!e||e==="none")return t.length?[{label:null,rows:t}]:[];let n=new Map;for(let r of t){let o=e==="provider"?r.provider:r.kind;n.has(o)||n.set(o,[]),n.get(o).push(r)}return Array.from(n.entries()).map(([r,o])=>({label:r,rows:o}))}var F="marketsentry",L=new Set(["probability","price","rate"]);function h(t){if(!t||!t.entities||!t.states)return[];let e=Object.values(t.entities).filter(o=>o.platform===F),n=e.filter(o=>L.has(o.translation_key)),r=[];for(let o of n){let i=t.states[o.entity_id];if(!i)continue;let a=i.attributes||{},s=o.device_id?t.devices?.[o.device_id]:null,c=s?.name_by_user||s?.name||a.friendly_name||o.entity_id,d={entityId:o.entity_id,deviceId:o.device_id,name:c,kind:a.kind,provider:a.provider,url:a.url,value:["unknown","unavailable"].includes(i.state)?null:Number(i.state),unit:a.unit_of_measurement,resolutionStatus:null,closed:null,endDate:null,marketState:null,publishedDate:a.published_date??null,source:a.source??null};for(let p of e){if(p.device_id!==o.device_id)continue;let u=t.states[p.entity_id];if(u)switch(p.translation_key){case"resolution_status":d.resolutionStatus=u.state;break;case"closed":d.closed=u.state==="on";break;case"end_date":d.endDate=u.state;break;case"market_state":d.marketState=u.state;break;default:break}}r.push(d)}return r}function b(t){if(!t||t.length<2)return{changePct:null,deltaPp:null};let e=t[0].p,r=t[t.length-1].p-e;return{changePct:e?r/e*100:null,deltaPp:r}}function $(t,e=80,n=24){if(!t||t.length<2)return null;let r=t.map(d=>d.p),o=Math.min(...r),a=Math.max(...r)-o||1,s=e/(t.length-1);return`M${t.map((d,p)=>{let u=p*s,C=n-(d.p-o)/a*n;return`${u.toFixed(1)},${C.toFixed(1)}`}).join(" L")}`}var T=6e4,N={provider:{polymarket:"Polymarket",finnhub:"Finnhub",alpaca:"Alpaca",fx:"Exchange rates"},kind:{outcome:"Prediction markets",stock:"Stocks",fx:"Exchange rates"}},v=class extends HTMLElement{static getConfigElement(){return document.createElement("marketsentry-card-editor")}static getStubConfig(){return{type:"custom:marketsentry-card",group_by:"kind"}}constructor(){super(),this.attachShadow({mode:"open"}),this._history=new Map,this._lastHistoryFetch=0}setConfig(e){if(e.kinds&&!Array.isArray(e.kinds))throw new Error("marketsentry-card: 'kinds' must be a list");this._config={group_by:"none",kinds:void 0,...e},this._render()}set hass(e){this._hass=e,this._maybeRefreshHistory(),this._render()}getCardSize(){return 1+h(this._hass).length}async _maybeRefreshHistory(){if(!this._hass)return;let e=Date.now();if(e-this._lastHistoryFetch<T)return;this._lastHistoryFetch=e;let n=h(this._hass);await Promise.all(n.map(async r=>{if(r.deviceId)try{let o=await this._hass.callWS({type:"marketsentry/history",device_id:r.deviceId});this._history.set(r.entityId,o?.history??[])}catch{}})),this._render()}_render(){if(!this.shadowRoot)return;if(!this._hass||!this._config){this.shadowRoot.innerHTML="";return}let e=h(this._hass),n=k(e,this._config.kinds),r=w(n,this._config.group_by);this.shadowRoot.innerHTML=`
      <style>${A}</style>
      <ha-card>
        ${this._config.title?`<h1 class="card-header">${l(this._config.title)}</h1>`:""}
        <div class="content">
          ${r.length===0?`<div class="empty">No tracked instruments match this card's filters.</div>`:""}
          ${r.map(o=>this._renderGroup(o)).join("")}
        </div>
      </ha-card>
    `}_renderGroup(e){let n=N[this._config.group_by]||{},r=e.label!=null?n[e.label]||e.label:null;return`
      ${r?`<div class="group-label">${l(r)}</div>`:""}
      ${e.rows.map(o=>this._renderRow(o)).join("")}
    `}_renderRow(e){return e.kind==="outcome"?this._renderOutcomeRow(e):this._renderGenericRow(e)}_renderOutcomeRow(e){let n=this._history.get(e.entityId)||[],{deltaPp:r}=b(n),o=f(e.kind,null,r),i=(r??0)>=0?"positive":"negative",a=g(e),s=S(e.url),c=e.value==null?0:Math.min(100,Math.max(0,e.value));return`
      <div class="row" part="row">
        <div class="row-name" title="${x(e.name)}">
          ${s?`<a href="${s}" target="_blank" rel="noopener">${l(e.name)}</a>`:l(e.name)}
        </div>
        <div class="row-chips">
          <span class="badge badge-${E(a)}">${l(a)}</span>
        </div>
        <div class="prob-line">
          <div class="prob-bar"><div class="prob-fill" style="width:${c}%"></div></div>
          <div class="prob-value">
            <span class="value" dir="ltr">${l(m(e.kind,e.value,e.unit))}</span>
            ${o?`<span class="change ${i}" dir="ltr">${l(o)}</span>`:""}
          </div>
        </div>
      </div>
    `}_renderGenericRow(e){let n=this._history.get(e.entityId)||[],{changePct:r,deltaPp:o}=b(n),i=$(n),a=f(e.kind,r,o),s=(o??r??0)>=0?"positive":"negative",c=g(e),d=S(e.url);return`
      <div class="row" part="row">
        <div class="row-top">
          <div class="row-name" title="${x(e.name)}">
            ${d?`<a href="${d}" target="_blank" rel="noopener">${l(e.name)}</a>`:l(e.name)}
          </div>
          <div class="row-value">
            <div class="value" dir="ltr">${l(m(e.kind,e.value,e.unit))}</div>
            ${a?`<div class="change ${s}" dir="ltr">${l(a)}</div>`:""}
          </div>
        </div>
        <div class="row-bottom">
          <div class="row-chips">
            ${e.kind==="stock"?`<span class="chip">${l(_(e.marketState))}</span>`:""}
            ${e.kind==="fx"?`<span class="chip">${e.source==="boi"||/boi/.test(e.source||"")?"Bank of Israel":"Market"}</span>`:""}
            ${e.kind!=="stock"?`<span class="badge badge-${E(c)}">${l(c)}</span>`:""}
          </div>
          <div class="row-spark">
            ${i?`<svg viewBox="0 0 80 24" preserveAspectRatio="none"><path d="${i}" fill="none" stroke="currentColor" stroke-width="1.5" /></svg>`:""}
          </div>
        </div>
      </div>
    `}};function l(t){return String(t??"").replace(/[&<>"']/g,e=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[e])}function x(t){return l(t)}function S(t){if(!t)return null;try{let e=new URL(t,window.location.origin);return e.protocol!=="http:"&&e.protocol!=="https:"?null:x(e.href)}catch{return null}}function E(t){return String(t).toLowerCase().replace(/\s+/g,"-")}var A=`
  :host { display: block; }
  ha-card { padding: 0; }
  .card-header {
    padding: 16px 16px 0;
    font-size: 1.2rem;
    color: var(--ha-card-header-color, var(--primary-text-color));
  }
  .content { padding: 8px 0 16px; }
  .empty {
    padding: 0 16px;
    color: var(--secondary-text-color);
  }
  .group-label {
    padding: 12px 16px 4px;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--secondary-text-color);
    text-transform: uppercase;
  }
  .row {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 16px;
    border-bottom: 1px solid var(--divider-color);
  }
  .row:last-child { border-bottom: none; }
  .row-top {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }
  .row-name {
    flex: 1 1 auto;
    min-width: 0;
    font-weight: 500;
    color: var(--primary-text-color);
    white-space: normal;
    overflow-wrap: break-word;
    line-height: 1.3;
  }
  .row-name a { color: inherit; text-decoration: none; }
  .row-name a:hover { text-decoration: underline; }
  .row-bottom {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .row-chips { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .badge {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .badge-live, .badge-open, .badge-updated-today { background: rgba(var(--rgb-green-color, 76, 175, 80), 0.18); color: var(--success-color, #4caf50); }
  .badge-closing-soon { background: rgba(var(--rgb-orange-color, 255, 152, 0), 0.18); color: var(--warning-color, #ff9800); }
  .badge-closed, .badge-resolved, .badge-stale { background: var(--secondary-background-color); color: var(--secondary-text-color); }
  .row-spark {
    flex: 0 0 80px;
    width: 80px;
    height: 24px;
    color: var(--primary-color);
  }
  .row-spark svg { width: 100%; height: 100%; display: block; }
  .prob-line {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .prob-bar {
    flex: 1 1 auto;
    height: 8px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    overflow: hidden;
  }
  .prob-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--success-color, #4caf50);
  }
  .prob-value {
    flex: 0 0 auto;
    display: flex;
    align-items: baseline;
    gap: 8px;
    white-space: nowrap;
  }
  .prob-value .value { font-size: 1rem; }
  .prob-value .change { font-size: 0.8rem; }
  .row-value {
    flex: 0 0 auto;
    text-align: end;
    min-width: 72px;
  }
  .value {
    font-weight: 600;
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
  }
  .change {
    font-size: 0.8rem;
    font-variant-numeric: tabular-nums;
  }
  .change.positive { color: var(--success-color, #4caf50); }
  .change.negative { color: var(--error-color, #f44336); }
`;customElements.define("marketsentry-card",v);window.customCards=window.customCards||[];window.customCards.push({type:"marketsentry-card",name:"MarketSentry Pro",description:"Rows for every tracked Polymarket/Finnhub/Alpaca/FX instrument, grouped and filterable.",preview:!0});var M=[{value:"outcome",label:"Prediction markets"},{value:"stock",label:"Stocks"},{value:"fx",label:"Exchange rates"}],y=class extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"})}setConfig(e){this._config={group_by:"none",kinds:void 0,...e},this._render()}set hass(e){this._hass=e}connectedCallback(){this._render()}_emitChange(){this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:!0,composed:!0}))}_render(){if(!this.shadowRoot||!this._config)return;this.shadowRoot.textContent="";let e=document.createElement("style");e.textContent=D,this.shadowRoot.appendChild(e);let n=document.createElement("div");n.className="editor",n.appendChild(this._buildTitleField()),n.appendChild(this._buildGroupByField()),n.appendChild(this._buildKindsField()),this.shadowRoot.appendChild(n)}_buildTitleField(){let e=document.createElement("div");e.className="field";let n=document.createElement("label");n.textContent="Title (optional)";let r=document.createElement("input");return r.type="text",r.value=this._config.title||"",r.addEventListener("input",()=>{this._config={...this._config,title:r.value||void 0},this._emitChange()}),e.append(n,r),e}_buildGroupByField(){let e=document.createElement("div");e.className="field";let n=document.createElement("label");n.textContent="Group by";let r=document.createElement("select");for(let o of["none","provider","kind"]){let i=document.createElement("option");i.value=o,i.textContent=o,i.selected=this._config.group_by===o,r.appendChild(i)}return r.addEventListener("change",()=>{this._config={...this._config,group_by:r.value},this._emitChange()}),e.append(n,r),e}_buildKindsField(){let e=document.createElement("div");e.className="field";let n=document.createElement("label");n.textContent="Kinds (none selected = all)",e.appendChild(n);let r=new Set(this._config.kinds||[]);for(let{value:o,label:i}of M){let a=document.createElement("label");a.className="checkbox-row";let s=document.createElement("input");s.type="checkbox",s.checked=r.has(o),s.addEventListener("change",()=>{let c=new Set(this._config.kinds||[]);s.checked?c.add(o):c.delete(o),this._config={...this._config,kinds:c.size?Array.from(c):void 0},this._emitChange()}),a.append(s,document.createTextNode(` ${i}`)),e.appendChild(a)}return e}},D=`
  .editor { display: flex; flex-direction: column; gap: 16px; padding: 8px 0; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  label { font-size: 0.9rem; color: var(--primary-text-color); }
  input[type="text"], select {
    padding: 8px;
    border-radius: 4px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color);
    color: var(--primary-text-color);
  }
  .checkbox-row { display: flex; align-items: center; gap: 6px; font-size: 0.9rem; }
`;customElements.define("marketsentry-card-editor",y);
