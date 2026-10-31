function m(t,e,n){return e==null||Number.isNaN(e)?"\u2014":t==="outcome"?`${e.toFixed(1)}%`:t==="fx"?`${e.toFixed(4)}${n?` ${n}`:""}`:`${n==="USD"?"$":n?`${n} `:""}${e.toFixed(2)}`}function f(t,e,n){return t==="outcome"?n==null||Number.isNaN(n)?null:`${n>0?"+":""}${n.toFixed(1)}pp`:e==null||Number.isNaN(e)?null:`${e>0?"+":""}${e.toFixed(2)}%`}function k(t){if(t==null||Number.isNaN(t))return"\u2014";let e=Math.abs(t);return e>=1e6?`$${(t/1e6).toFixed(1)}M`:e>=1e3?`$${(t/1e3).toFixed(1)}K`:`$${t.toFixed(0)}`}function $(t){if(!t)return"\u2014";let e=new Date(t);return Number.isNaN(e.getTime())?"\u2014":e.toLocaleDateString("en-US",{year:"numeric",month:"short",day:"numeric"})}var z={pre:"Pre",regular:"Open",post:"After",closed:"Closed"};function x(t){return t&&z[t]||"Closed"}function g(t,e=new Date){if(t.kind==="outcome"){if(t.resolutionStatus==="resolved")return"Resolved";if(t.closed)return"Closed";if(t.endDate){let n=(new Date(t.endDate).getTime()-e.getTime())/36e5;if(n>=0&&n<=24)return"Closing soon"}return"Live"}return t.kind==="stock"?t.marketState&&t.marketState!=="closed"?"Open":"Closed":t.kind==="fx"?t.publishedDate&&new Date(t.publishedDate).toDateString()===e.toDateString()?"Updated today":"Stale":""}function L(t,e){return!e||e.length===0?t:t.filter(n=>e.includes(n.kind))}function F(t,e){if(!e||e==="none")return t.length?[{label:null,rows:t}]:[];let n=new Map;for(let r of t){let i=e==="provider"?r.provider:r.kind;n.has(i)||n.set(i,[]),n.get(i).push(r)}return Array.from(n.entries()).map(([r,i])=>({label:r,rows:i}))}var D="marketsentry",I=new Set(["probability","price","rate"]);function p(t){if(!t||!t.entities||!t.states)return[];let e=Object.values(t.entities).filter(i=>i.platform===D),n=e.filter(i=>I.has(i.translation_key)),r=[];for(let i of n){let o=t.states[i.entity_id];if(!o)continue;let a=o.attributes||{},s=i.device_id?t.devices?.[i.device_id]:null,c=s?.name_by_user||s?.name||a.friendly_name||i.entity_id,d={entityId:i.entity_id,deviceId:i.device_id,name:c,kind:a.kind,provider:a.provider,url:a.url,value:["unknown","unavailable"].includes(o.state)?null:Number(o.state),unit:a.unit_of_measurement,resolutionStatus:null,closed:null,endDate:null,marketState:null,publishedDate:a.published_date??null,source:a.source??null,volume24hr:null,liquidity:null,previousClose:null};for(let b of e){if(b.device_id!==i.device_id)continue;let h=t.states[b.entity_id];if(!h)continue;let y=["unknown","unavailable"].includes(h.state)?null:Number(h.state);switch(b.translation_key){case"resolution_status":d.resolutionStatus=h.state;break;case"closed":d.closed=h.state==="on";break;case"end_date":d.endDate=h.state;break;case"market_state":d.marketState=h.state;break;case"volume_24hr":d.volume24hr=y;break;case"liquidity":d.liquidity=y;break;case"previous_close":d.previousClose=y;break;default:break}}r.push(d)}return r}function v(t){if(!t||t.length<2)return{changePct:null,deltaPp:null};let e=t[0].p,r=t[t.length-1].p-e;return{changePct:e?r/e*100:null,deltaPp:r}}function _(t,e=80,n=24){if(!t||t.length<2)return null;let r=t.map(d=>d.p),i=Math.min(...r),a=Math.max(...r)-i||1,s=e/(t.length-1);return`M${t.map((d,b)=>{let h=b*s,y=n-(d.p-i)/a*n;return`${h.toFixed(1)},${y.toFixed(1)}`}).join(" L")}`}var K=6e4,O={provider:{polymarket:"Polymarket",finnhub:"Finnhub",alpaca:"Alpaca",fx:"Exchange rates"},kind:{outcome:"Prediction markets",stock:"Stocks",fx:"Exchange rates"}},w=class extends HTMLElement{static getConfigElement(){return document.createElement("marketsentry-card-editor")}static getStubConfig(){return{type:"custom:marketsentry-card",group_by:"kind"}}constructor(){super(),this.attachShadow({mode:"open"}),this._history=new Map,this._lastHistoryFetch=0}setConfig(e){if(e.kinds&&!Array.isArray(e.kinds))throw new Error("marketsentry-card: 'kinds' must be a list");this._config={group_by:"none",kinds:void 0,...e},this._render()}set hass(e){this._hass=e,this._maybeRefreshHistory(),this._render()}getCardSize(){return 1+p(this._hass).length}async _maybeRefreshHistory(){if(!this._hass)return;let e=Date.now();if(e-this._lastHistoryFetch<K)return;this._lastHistoryFetch=e;let n=p(this._hass);await Promise.all(n.map(async r=>{if(r.deviceId)try{let i=await this._hass.callWS({type:"marketsentry/history",device_id:r.deviceId});this._history.set(r.entityId,i?.history??[])}catch{}})),this._render()}_render(){if(!this.shadowRoot)return;if(!this._hass||!this._config){this.shadowRoot.innerHTML="";return}let e=p(this._hass),n=L(e,this._config.kinds),r=F(n,this._config.group_by);this.shadowRoot.innerHTML=`
      <style>${A}</style>
      <ha-card>
        ${this._config.title?`<h1 class="card-header">${u(this._config.title)}</h1>`:""}
        <div class="content">
          ${r.length===0?`<div class="empty">No tracked instruments match this card's filters.</div>`:""}
          ${r.map(i=>this._renderGroup(i)).join("")}
        </div>
      </ha-card>
    `}_renderGroup(e){let n=O[this._config.group_by]||{},r=e.label!=null?n[e.label]||e.label:null;return`
      ${r?`<div class="group-label">${u(r)}</div>`:""}
      ${e.rows.map(i=>this._renderRow(i)).join("")}
    `}_renderRow(e){return e.kind==="outcome"?this._renderOutcomeRow(e):this._renderGenericRow(e)}_renderOutcomeRow(e){let n=this._history.get(e.entityId)||[],{deltaPp:r}=v(n),i=f(e.kind,null,r),o=(r??0)>=0?"positive":"negative",a=g(e),s=T(e.url),c=e.value==null?0:Math.min(100,Math.max(0,e.value));return`
      <div class="row" part="row">
        <div class="row-name" title="${C(e.name)}">
          ${s?`<a href="${s}" target="_blank" rel="noopener">${u(e.name)}</a>`:u(e.name)}
        </div>
        <div class="row-chips">
          <span class="badge badge-${H(a)}">${u(a)}</span>
        </div>
        <div class="prob-line">
          <div class="prob-bar"><div class="prob-fill" style="width:${c}%"></div></div>
          <div class="prob-value">
            <span class="value" dir="ltr">${u(m(e.kind,e.value,e.unit))}</span>
            ${i?`<span class="change ${o}" dir="ltr">${u(i)}</span>`:""}
          </div>
        </div>
      </div>
    `}_renderGenericRow(e){let n=this._history.get(e.entityId)||[],{changePct:r,deltaPp:i}=v(n),o=_(n),a=f(e.kind,r,i),s=(i??r??0)>=0?"positive":"negative",c=g(e),d=T(e.url);return`
      <div class="row" part="row">
        <div class="row-top">
          <div class="row-name" title="${C(e.name)}">
            ${d?`<a href="${d}" target="_blank" rel="noopener">${u(e.name)}</a>`:u(e.name)}
          </div>
          <div class="row-value">
            <div class="value" dir="ltr">${u(m(e.kind,e.value,e.unit))}</div>
            ${a?`<div class="change ${s}" dir="ltr">${u(a)}</div>`:""}
          </div>
        </div>
        <div class="row-bottom">
          <div class="row-chips">
            ${e.kind==="stock"?`<span class="chip">${u(x(e.marketState))}</span>`:""}
            ${e.kind==="fx"?`<span class="chip">${e.source==="boi"||/boi/.test(e.source||"")?"Bank of Israel":"Market"}</span>`:""}
            ${e.kind!=="stock"?`<span class="badge badge-${H(c)}">${u(c)}</span>`:""}
          </div>
          <div class="row-spark">
            ${o?`<svg viewBox="0 0 80 24" preserveAspectRatio="none"><path d="${o}" fill="none" stroke="currentColor" stroke-width="1.5" /></svg>`:""}
          </div>
        </div>
      </div>
    `}};function u(t){return String(t??"").replace(/[&<>"']/g,e=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[e])}function C(t){return u(t)}function T(t){if(!t)return null;try{let e=new URL(t,window.location.origin);return e.protocol!=="http:"&&e.protocol!=="https:"?null:C(e.href)}catch{return null}}function H(t){return String(t).toLowerCase().replace(/\s+/g,"-")}var A=`
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
    background: var(--error-color, #f44336);
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
`;customElements.define("marketsentry-card",w);window.customCards=window.customCards||[];window.customCards.push({type:"marketsentry-card",name:"MarketSentry Pro",description:"Rows for every tracked Polymarket/Finnhub/Alpaca/FX instrument, grouped and filterable.",preview:!0});var B=[{value:"outcome",label:"Prediction markets"},{value:"stock",label:"Stocks"},{value:"fx",label:"Exchange rates"}],S=class extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"})}setConfig(e){let n={group_by:"none",kinds:void 0,...e},r=JSON.stringify(n);this._configKey!==r&&(this._config=n,this._configKey=r,this._render())}set hass(e){this._hass=e}connectedCallback(){this._render()}_emitChange(){this._configKey=JSON.stringify(this._config),this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:!0,composed:!0}))}_render(){if(!this.shadowRoot||!this._config)return;this.shadowRoot.textContent="";let e=document.createElement("style");e.textContent=G,this.shadowRoot.appendChild(e);let n=document.createElement("div");n.className="editor",n.appendChild(this._buildTitleField()),n.appendChild(this._buildGroupByField()),n.appendChild(this._buildKindsField()),this.shadowRoot.appendChild(n)}_buildTitleField(){let e=document.createElement("div");e.className="field";let n=document.createElement("label");n.textContent="Title (optional)";let r=document.createElement("input");return r.type="text",r.value=this._config.title||"",r.addEventListener("input",()=>{this._config={...this._config,title:r.value||void 0},this._emitChange()}),e.append(n,r),e}_buildGroupByField(){let e=document.createElement("div");e.className="field";let n=document.createElement("label");n.textContent="Group by";let r=document.createElement("select");for(let i of["none","provider","kind"]){let o=document.createElement("option");o.value=i,o.textContent=i,o.selected=this._config.group_by===i,r.appendChild(o)}return r.addEventListener("change",()=>{this._config={...this._config,group_by:r.value},this._emitChange()}),e.append(n,r),e}_buildKindsField(){let e=document.createElement("div");e.className="field";let n=document.createElement("label");n.textContent="Kinds (none selected = all)",e.appendChild(n);let r=new Set(this._config.kinds||[]);for(let{value:i,label:o}of B){let a=document.createElement("label");a.className="checkbox-row";let s=document.createElement("input");s.type="checkbox",s.checked=r.has(i),s.addEventListener("change",()=>{let c=new Set(this._config.kinds||[]);s.checked?c.add(i):c.delete(i),this._config={...this._config,kinds:c.size?Array.from(c):void 0},this._emitChange()}),a.append(s,document.createTextNode(` ${o}`)),e.appendChild(a)}return e}},G=`
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
`;customElements.define("marketsentry-card-editor",S);var U=6e4,E=class extends HTMLElement{static getConfigElement(){return document.createElement("marketsentry-instrument-card-editor")}static getStubConfig(e){return{type:"custom:marketsentry-instrument-card",entity:p(e)[0]?.entityId||""}}constructor(){super(),this.attachShadow({mode:"open"}),this._history=[],this._lastHistoryFetch=0}setConfig(e){if(!e.entity)throw new Error("marketsentry-instrument-card: 'entity' is required");this._config={...e},this._render()}set hass(e){this._hass=e,this._maybeRefreshHistory(),this._render()}getCardSize(){return 3}_findRow(){return this._hass&&p(this._hass).find(e=>e.entityId===this._config.entity)||null}async _maybeRefreshHistory(){if(!this._hass)return;let e=Date.now();if(e-this._lastHistoryFetch<U)return;this._lastHistoryFetch=e;let n=this._findRow();if(n?.deviceId){try{let r=await this._hass.callWS({type:"marketsentry/history",device_id:n.deviceId});this._history=r?.history??[]}catch{}this._render()}}_render(){if(!this.shadowRoot)return;if(!this._hass||!this._config){this.shadowRoot.innerHTML="";return}let e=this._findRow();this.shadowRoot.innerHTML=`
      <style>${q}</style>
      <ha-card>
        <div class="content">
          ${e?this._renderBody(e):`<div class="empty">Entity not found or not a MarketSentry Pro instrument: ${l(this._config.entity)}</div>`}
        </div>
      </ha-card>
    `}_renderBody(e){return e.kind==="outcome"?this._renderOutcome(e):this._renderGeneric(e)}_renderOutcome(e){let{deltaPp:n}=v(this._history),r=f(e.kind,null,n),i=(n??0)>=0?"positive":"negative",o=g(e),a=M(e.url),s=e.value==null?0:Math.min(100,Math.max(0,e.value));return`
      <div class="title" title="${R(e.name)}">
        ${a?`<a href="${a}" target="_blank" rel="noopener">${l(e.name)}</a>`:l(e.name)}
      </div>
      <div class="chips">
        <span class="badge badge-${P(o)}">${l(o)}</span>
      </div>
      <div class="prob-line">
        <div class="prob-bar"><div class="prob-fill" style="width:${s}%"></div></div>
        <div class="prob-value">
          <span class="value" dir="ltr">${l(m(e.kind,e.value,e.unit))}</span>
          ${r?`<span class="change ${i}" dir="ltr">${l(r)}</span>`:""}
        </div>
      </div>
      <div class="stats">
        <div class="stat"><span class="stat-label">Volume 24h</span><span class="stat-value" dir="ltr">${k(e.volume24hr)}</span></div>
        <div class="stat"><span class="stat-label">Liquidity</span><span class="stat-value" dir="ltr">${k(e.liquidity)}</span></div>
      </div>
      <div class="footer">Ends ${l($(e.endDate))}</div>
    `}_renderGeneric(e){let{changePct:n,deltaPp:r}=v(this._history),i=_(this._history,280,60),o=f(e.kind,n,r),a=(r??n??0)>=0?"positive":"negative",s=g(e),c=M(e.url);return`
      <div class="title" title="${R(e.name)}">
        ${c?`<a href="${c}" target="_blank" rel="noopener">${l(e.name)}</a>`:l(e.name)}
      </div>
      <div class="chips">
        ${e.kind==="stock"?`<span class="chip">${l(x(e.marketState))}</span>`:""}
        ${e.kind==="fx"?`<span class="chip">${e.source==="boi"||/boi/.test(e.source||"")?"Bank of Israel":"Market"}</span>`:""}
        ${e.kind!=="stock"?`<span class="badge badge-${P(s)}">${l(s)}</span>`:""}
      </div>
      <div class="big-value">
        <span class="value" dir="ltr">${l(m(e.kind,e.value,e.unit))}</span>
        ${o?`<span class="change ${a}" dir="ltr">${l(o)}</span>`:""}
      </div>
      <div class="big-spark">
        ${i?`<svg viewBox="0 0 280 60" preserveAspectRatio="none"><path d="${i}" fill="none" stroke="currentColor" stroke-width="2" /></svg>`:""}
      </div>
      ${e.kind==="stock"?`<div class="stats"><div class="stat"><span class="stat-label">Prev close</span><span class="stat-value" dir="ltr">${l(m(e.kind,e.previousClose,e.unit))}</span></div></div>`:""}
      ${e.kind==="fx"?`<div class="footer">Published ${l($(e.publishedDate))}</div>`:""}
    `}};function l(t){return String(t??"").replace(/[&<>"']/g,e=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[e])}function R(t){return l(t)}function M(t){if(!t)return null;try{let e=new URL(t,window.location.origin);return e.protocol!=="http:"&&e.protocol!=="https:"?null:R(e.href)}catch{return null}}function P(t){return String(t).toLowerCase().replace(/\s+/g,"-")}var q=`
  :host { display: block; }
  ha-card { padding: 16px; }
  .content { display: flex; flex-direction: column; gap: 10px; }
  .empty { color: var(--secondary-text-color); }
  .title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--primary-text-color);
    line-height: 1.3;
  }
  .title a { color: inherit; text-decoration: none; }
  .title a:hover { text-decoration: underline; }
  .chips { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .badge {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .badge-live, .badge-open, .badge-updated-today { background: rgba(var(--rgb-green-color, 76, 175, 80), 0.18); color: var(--success-color, #4caf50); }
  .badge-closing-soon { background: rgba(var(--rgb-orange-color, 255, 152, 0), 0.18); color: var(--warning-color, #ff9800); }
  .badge-closed, .badge-resolved, .badge-stale { background: var(--secondary-background-color); color: var(--secondary-text-color); }
  .prob-line { display: flex; align-items: center; gap: 12px; margin-top: 4px; }
  .prob-bar {
    flex: 1 1 auto;
    height: 10px;
    border-radius: 999px;
    background: var(--error-color, #f44336);
    overflow: hidden;
  }
  .prob-fill { height: 100%; border-radius: 999px; background: var(--success-color, #4caf50); }
  .prob-value { flex: 0 0 auto; display: flex; align-items: baseline; gap: 8px; white-space: nowrap; }
  .prob-value .value { font-size: 1.4rem; font-weight: 700; color: var(--primary-text-color); }
  .big-value { display: flex; align-items: baseline; gap: 10px; margin-top: 4px; }
  .big-value .value { font-size: 1.8rem; font-weight: 700; color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
  .change { font-size: 0.95rem; font-variant-numeric: tabular-nums; }
  .change.positive { color: var(--success-color, #4caf50); }
  .change.negative { color: var(--error-color, #f44336); }
  .big-spark { width: 100%; height: 60px; color: var(--primary-color); }
  .big-spark svg { width: 100%; height: 100%; display: block; }
  .stats { display: flex; gap: 20px; margin-top: 2px; }
  .stat { display: flex; flex-direction: column; gap: 2px; }
  .stat-label { font-size: 0.72rem; color: var(--secondary-text-color); text-transform: uppercase; }
  .stat-value { font-size: 0.95rem; font-weight: 600; color: var(--primary-text-color); }
  .footer { font-size: 0.8rem; color: var(--secondary-text-color); }
`;customElements.define("marketsentry-instrument-card",E);window.customCards=window.customCards||[];window.customCards.push({type:"marketsentry-instrument-card",name:"MarketSentry Pro (single instrument)",description:"One tracked instrument per card, with a kind-specific detailed view (Polymarket probability bar + stats, stock/FX price + sparkline).",preview:!0});var N=class extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"})}setConfig(e){let n={...e},r=JSON.stringify(n);this._configKey!==r&&(this._config=n,this._configKey=r,this._render())}set hass(e){this._hass=e;let n=p(e),r=JSON.stringify(n.map(i=>[i.entityId,i.name]));this._rowsKey!==r&&(this._rowsKey=r,this._render())}connectedCallback(){this._render()}_emitChange(){this._configKey=JSON.stringify(this._config),this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:!0,composed:!0}))}_render(){if(!this.shadowRoot||!this._config)return;this.shadowRoot.textContent="";let e=document.createElement("style");e.textContent=Y,this.shadowRoot.appendChild(e);let n=document.createElement("div");n.className="editor",n.appendChild(this._buildEntityField()),this.shadowRoot.appendChild(n)}_buildEntityField(){let e=document.createElement("div");e.className="field";let n=document.createElement("label");n.textContent="Instrument",e.appendChild(n);let r=this._hass?p(this._hass):[],i=document.createElement("select"),o=document.createElement("option");o.value="",o.textContent=r.length?"Choose an instrument\u2026":"No MarketSentry Pro instruments found",o.disabled=!0,o.selected=!this._config.entity,i.appendChild(o);for(let a of r){let s=document.createElement("option");s.value=a.entityId,s.textContent=a.name,s.selected=this._config.entity===a.entityId,i.appendChild(s)}return i.addEventListener("change",()=>{this._config={...this._config,entity:i.value},this._emitChange()}),e.appendChild(i),e}},Y=`
  .editor { display: flex; flex-direction: column; gap: 16px; padding: 8px 0; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  label { font-size: 0.9rem; color: var(--primary-text-color); }
  select {
    padding: 8px;
    border-radius: 4px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color);
    color: var(--primary-text-color);
  }
`;customElements.define("marketsentry-instrument-card-editor",N);
