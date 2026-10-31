function f(o,e,t){return e==null||Number.isNaN(e)?"\u2014":o==="outcome"?`${e.toFixed(1)}%`:o==="fx"?`${e.toFixed(4)}${t?` ${t}`:""}`:`${t==="USD"?"$":t?`${t} `:""}${e.toFixed(2)}`}function b(o,e,t){return o==="outcome"?t==null||Number.isNaN(t)?null:`${t>0?"+":""}${t.toFixed(1)}pp`:e==null||Number.isNaN(e)?null:`${e>0?"+":""}${e.toFixed(2)}%`}function S(o){if(o==null||Number.isNaN(o))return"\u2014";let e=Math.abs(o);return e>=1e6?`$${(o/1e6).toFixed(1)}M`:e>=1e3?`$${(o/1e3).toFixed(1)}K`:`$${o.toFixed(0)}`}function C(o,e="en-US"){if(!o)return"\u2014";let t=new Date(o);return Number.isNaN(t.getTime())?"\u2014":t.toLocaleDateString(e,{year:"numeric",month:"short",day:"numeric"})}var H={pre:"pre",regular:"open",post:"after",closed:"closed"};function k(o){return o&&H[o]||"closed"}function v(o,e=new Date){if(o.kind==="outcome"){if(o.resolutionStatus==="resolved")return"resolved";if(o.closed)return"closed";if(o.endDate){let t=(new Date(o.endDate).getTime()-e.getTime())/36e5;if(t>=0&&t<=24)return"closing_soon"}return"live"}return o.kind==="stock"?o.marketState&&o.marketState!=="closed"?"open":"closed":o.kind==="fx"?o.publishedDate&&new Date(o.publishedDate).toDateString()===e.toDateString()?"updated_today":"stale":""}function N(o,e){return!e||e.length===0?o:o.filter(t=>e.includes(t.kind))}function I(o,e){if(!e||e==="none")return o.length?[{label:null,rows:o}]:[];let t=new Map;for(let r of o){let n=e==="provider"?r.provider:r.kind;t.has(n)||t.set(n,[]),t.get(n).push(r)}return Array.from(t.entries()).map(([r,n])=>({label:r,rows:n}))}var K=["en","he","de","fr","es","pt-BR","it","nl"],E={en:"en-US",he:"he-IL",de:"de-DE",fr:"fr-FR",es:"es-ES","pt-BR":"pt-BR",it:"it-IT",nl:"nl-NL"},$={en:{empty_card:"No tracked instruments match this card's filters.",empty_instrument:"Entity not found or not a MarketSentry Pro instrument: {entity}",group_predictions:"Prediction markets",group_stocks:"Stocks",group_fx:"Exchange rates",badge_resolved:"Resolved",badge_closed:"Closed",badge_closing_soon:"Closing soon",badge_live:"Live",badge_open:"Open",badge_stale:"Stale",badge_updated_today:"Updated today",chip_pre:"Pre",chip_open:"Open",chip_after:"After",chip_closed:"Closed",fx_boi:"Bank of Israel",fx_market:"Market",stat_volume_24h:"Volume 24h",stat_liquidity:"Liquidity",stat_prev_close:"Prev close",footer_ends:"Ends {date}",footer_published:"Published {date}",editor_title:"Title (optional)",editor_group_by:"Group by",editor_group_none:"none",editor_group_provider:"provider",editor_group_kind:"kind",editor_kinds:"Kinds (none selected = all)",editor_instrument:"Instrument",editor_choose:"Choose an instrument\u2026",editor_no_instruments:"No MarketSentry Pro instruments found"},he:{empty_card:"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E9\u05D9\u05E8\u05D9\u05DD \u05DE\u05E0\u05D5\u05D8\u05E8\u05D9\u05DD \u05D4\u05EA\u05D5\u05D0\u05DE\u05D9\u05DD \u05D0\u05EA \u05D4\u05DE\u05E1\u05E0\u05E0\u05D9\u05DD \u05E9\u05DC \u05DB\u05E8\u05D8\u05D9\u05E1 \u05D6\u05D4.",empty_instrument:"\u05D4\u05D9\u05E9\u05D5\u05EA \u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D4 \u05D0\u05D5 \u05E9\u05D0\u05D9\u05E0\u05D4 \u05DE\u05DB\u05E9\u05D9\u05E8 MarketSentry Pro: {entity}",group_predictions:"\u05E9\u05D5\u05E7\u05D9 \u05D7\u05D9\u05D6\u05D5\u05D9",group_stocks:"\u05DE\u05E0\u05D9\u05D5\u05EA",group_fx:"\u05E9\u05E2\u05E8\u05D9 \u05D7\u05DC\u05D9\u05E4\u05D9\u05DF",badge_resolved:"\u05E0\u05E4\u05EA\u05E8",badge_closed:"\u05E1\u05D2\u05D5\u05E8",badge_closing_soon:"\u05E0\u05E1\u05D2\u05E8 \u05D1\u05E7\u05E8\u05D5\u05D1",badge_live:"\u05E4\u05E2\u05D9\u05DC",badge_open:"\u05E4\u05EA\u05D5\u05D7",badge_stale:"\u05DC\u05D0 \u05DE\u05E2\u05D5\u05D3\u05DB\u05DF",badge_updated_today:"\u05E2\u05D5\u05D3\u05DB\u05DF \u05D4\u05D9\u05D5\u05DD",chip_pre:"\u05D8\u05E8\u05D5\u05DD",chip_open:"\u05E4\u05EA\u05D5\u05D7",chip_after:"\u05D0\u05D7\u05E8\u05D9",chip_closed:"\u05E1\u05D2\u05D5\u05E8",fx_boi:"\u05D1\u05E0\u05E7 \u05D9\u05E9\u05E8\u05D0\u05DC",fx_market:"\u05E9\u05D5\u05E7",stat_volume_24h:"\u05DE\u05D7\u05D6\u05D5\u05E8 24 \u05E9\u05E2\u05D5\u05EA",stat_liquidity:"\u05E0\u05D6\u05D9\u05DC\u05D5\u05EA",stat_prev_close:"\u05E1\u05D2\u05D9\u05E8\u05D4 \u05E7\u05D5\u05D3\u05DE\u05EA",footer_ends:"\u05DE\u05E1\u05EA\u05D9\u05D9\u05DD \u05D1-{date}",footer_published:"\u05E4\u05D5\u05E8\u05E1\u05DD \u05D1-{date}",editor_title:"\u05DB\u05D5\u05EA\u05E8\u05EA (\u05E8\u05E9\u05D5\u05EA)",editor_group_by:"\u05E7\u05D9\u05D1\u05D5\u05E5 \u05DC\u05E4\u05D9",editor_group_none:"\u05DC\u05DC\u05D0",editor_group_provider:"\u05E1\u05E4\u05E7",editor_group_kind:"\u05E1\u05D5\u05D2",editor_kinds:"\u05E1\u05D5\u05D2\u05D9\u05DD (\u05DC\u05DC\u05D0 \u05D1\u05D7\u05D9\u05E8\u05D4 = \u05D4\u05DB\u05D5\u05DC)",editor_instrument:"\u05DE\u05DB\u05E9\u05D9\u05E8",editor_choose:"\u05D1\u05D7\u05E8 \u05DE\u05DB\u05E9\u05D9\u05E8\u2026",editor_no_instruments:"\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D5 \u05DE\u05DB\u05E9\u05D9\u05E8\u05D9 MarketSentry Pro"},de:{empty_card:"Keine verfolgten Instrumente entsprechen den Filtern dieser Karte.",empty_instrument:"Entit\xE4t nicht gefunden oder kein MarketSentry-Pro-Instrument: {entity}",group_predictions:"Prognosem\xE4rkte",group_stocks:"Aktien",group_fx:"Wechselkurse",badge_resolved:"Aufgel\xF6st",badge_closed:"Geschlossen",badge_closing_soon:"Schlie\xDFt bald",badge_live:"Live",badge_open:"Offen",badge_stale:"Veraltet",badge_updated_today:"Heute aktualisiert",chip_pre:"Vorb\xF6rse",chip_open:"Offen",chip_after:"Nachb\xF6rse",chip_closed:"Geschlossen",fx_boi:"Bank of Israel",fx_market:"Markt",stat_volume_24h:"24h-Volumen",stat_liquidity:"Liquidit\xE4t",stat_prev_close:"Vorheriger Schluss",footer_ends:"Endet am {date}",footer_published:"Ver\xF6ffentlicht am {date}",editor_title:"Titel (optional)",editor_group_by:"Gruppieren nach",editor_group_none:"keine",editor_group_provider:"Anbieter",editor_group_kind:"Art",editor_kinds:"Arten (keine Auswahl = alle)",editor_instrument:"Instrument",editor_choose:"Instrument w\xE4hlen\u2026",editor_no_instruments:"Keine MarketSentry-Pro-Instrumente gefunden"},fr:{empty_card:"Aucun instrument suivi ne correspond aux filtres de cette carte.",empty_instrument:"Entit\xE9 introuvable ou n'est pas un instrument MarketSentry Pro : {entity}",group_predictions:"March\xE9s de pr\xE9diction",group_stocks:"Actions",group_fx:"Taux de change",badge_resolved:"R\xE9solu",badge_closed:"Ferm\xE9",badge_closing_soon:"Ferme bient\xF4t",badge_live:"En direct",badge_open:"Ouvert",badge_stale:"Obsol\xE8te",badge_updated_today:"Mis \xE0 jour aujourd'hui",chip_pre:"Avant-bourse",chip_open:"Ouvert",chip_after:"Apr\xE8s-bourse",chip_closed:"Ferm\xE9",fx_boi:"Banque d'Isra\xEBl",fx_market:"March\xE9",stat_volume_24h:"Volume 24h",stat_liquidity:"Liquidit\xE9",stat_prev_close:"Cl\xF4ture pr\xE9c\xE9dente",footer_ends:"Se termine le {date}",footer_published:"Publi\xE9 le {date}",editor_title:"Titre (facultatif)",editor_group_by:"Grouper par",editor_group_none:"aucun",editor_group_provider:"fournisseur",editor_group_kind:"type",editor_kinds:"Types (aucune s\xE9lection = tous)",editor_instrument:"Instrument",editor_choose:"Choisir un instrument\u2026",editor_no_instruments:"Aucun instrument MarketSentry Pro trouv\xE9"},es:{empty_card:"Ning\xFAn instrumento seguido coincide con los filtros de esta tarjeta.",empty_instrument:"Entidad no encontrada o no es un instrumento de MarketSentry Pro: {entity}",group_predictions:"Mercados de predicci\xF3n",group_stocks:"Acciones",group_fx:"Tipos de cambio",badge_resolved:"Resuelto",badge_closed:"Cerrado",badge_closing_soon:"Cierra pronto",badge_live:"En vivo",badge_open:"Abierto",badge_stale:"Desactualizado",badge_updated_today:"Actualizado hoy",chip_pre:"Pre-apertura",chip_open:"Abierto",chip_after:"Post-cierre",chip_closed:"Cerrado",fx_boi:"Banco de Israel",fx_market:"Mercado",stat_volume_24h:"Volumen 24h",stat_liquidity:"Liquidez",stat_prev_close:"Cierre anterior",footer_ends:"Termina el {date}",footer_published:"Publicado el {date}",editor_title:"T\xEDtulo (opcional)",editor_group_by:"Agrupar por",editor_group_none:"ninguno",editor_group_provider:"proveedor",editor_group_kind:"tipo",editor_kinds:"Tipos (ninguno seleccionado = todos)",editor_instrument:"Instrumento",editor_choose:"Elige un instrumento\u2026",editor_no_instruments:"No se encontraron instrumentos de MarketSentry Pro"},"pt-BR":{empty_card:"Nenhum instrumento acompanhado corresponde aos filtros deste cart\xE3o.",empty_instrument:"Entidade n\xE3o encontrada ou n\xE3o \xE9 um instrumento MarketSentry Pro: {entity}",group_predictions:"Mercados de previs\xE3o",group_stocks:"A\xE7\xF5es",group_fx:"Taxas de c\xE2mbio",badge_resolved:"Resolvido",badge_closed:"Fechado",badge_closing_soon:"Fecha em breve",badge_live:"Ao vivo",badge_open:"Aberto",badge_stale:"Desatualizado",badge_updated_today:"Atualizado hoje",chip_pre:"Pr\xE9-mercado",chip_open:"Aberto",chip_after:"P\xF3s-mercado",chip_closed:"Fechado",fx_boi:"Banco de Israel",fx_market:"Mercado",stat_volume_24h:"Volume 24h",stat_liquidity:"Liquidez",stat_prev_close:"Fechamento anterior",footer_ends:"Termina em {date}",footer_published:"Publicado em {date}",editor_title:"T\xEDtulo (opcional)",editor_group_by:"Agrupar por",editor_group_none:"nenhum",editor_group_provider:"provedor",editor_group_kind:"tipo",editor_kinds:"Tipos (nenhum selecionado = todos)",editor_instrument:"Instrumento",editor_choose:"Escolha um instrumento\u2026",editor_no_instruments:"Nenhum instrumento MarketSentry Pro encontrado"},it:{empty_card:"Nessuno strumento seguito corrisponde ai filtri di questa scheda.",empty_instrument:"Entit\xE0 non trovata o non \xE8 uno strumento MarketSentry Pro: {entity}",group_predictions:"Mercati predittivi",group_stocks:"Azioni",group_fx:"Tassi di cambio",badge_resolved:"Risolto",badge_closed:"Chiuso",badge_closing_soon:"Chiude a breve",badge_live:"Live",badge_open:"Aperto",badge_stale:"Non aggiornato",badge_updated_today:"Aggiornato oggi",chip_pre:"Pre-mercato",chip_open:"Aperto",chip_after:"Post-mercato",chip_closed:"Chiuso",fx_boi:"Banca d'Israele",fx_market:"Mercato",stat_volume_24h:"Volume 24h",stat_liquidity:"Liquidit\xE0",stat_prev_close:"Chiusura precedente",footer_ends:"Termina il {date}",footer_published:"Pubblicato il {date}",editor_title:"Titolo (opzionale)",editor_group_by:"Raggruppa per",editor_group_none:"nessuno",editor_group_provider:"fornitore",editor_group_kind:"tipo",editor_kinds:"Tipi (nessuna selezione = tutti)",editor_instrument:"Strumento",editor_choose:"Scegli uno strumento\u2026",editor_no_instruments:"Nessuno strumento MarketSentry Pro trovato"},nl:{empty_card:"Geen gevolgde instrumenten komen overeen met de filters van deze kaart.",empty_instrument:"Entiteit niet gevonden of geen MarketSentry Pro-instrument: {entity}",group_predictions:"Voorspellingsmarkten",group_stocks:"Aandelen",group_fx:"Wisselkoersen",badge_resolved:"Afgewikkeld",badge_closed:"Gesloten",badge_closing_soon:"Sluit binnenkort",badge_live:"Live",badge_open:"Open",badge_stale:"Verouderd",badge_updated_today:"Vandaag bijgewerkt",chip_pre:"Voorbeurs",chip_open:"Open",chip_after:"Naborsbeurs",chip_closed:"Gesloten",fx_boi:"Bank of Israel",fx_market:"Markt",stat_volume_24h:"24u volume",stat_liquidity:"Liquiditeit",stat_prev_close:"Vorige slotkoers",footer_ends:"Eindigt op {date}",footer_published:"Gepubliceerd op {date}",editor_title:"Titel (optioneel)",editor_group_by:"Groeperen op",editor_group_none:"geen",editor_group_provider:"aanbieder",editor_group_kind:"type",editor_kinds:"Typen (geen selectie = alle)",editor_instrument:"Instrument",editor_choose:"Kies een instrument\u2026",editor_no_instruments:"Geen MarketSentry Pro-instrumenten gevonden"}};function m(o){let e=o?.locale?.language||o?.language||"en";if($[e])return e;let t=e.split("-")[0];return K.find(n=>n.split("-")[0]===t)||"en"}function a(o,e,t){let n=($[o]||$.en)[e]??$.en[e]??e;if(t)for(let[s,i]of Object.entries(t))n=n.replace(`{${s}}`,i);return n}var q="marketsentry",B=new Set(["probability","price","rate"]);function g(o){if(!o||!o.entities||!o.states)return[];let e=Object.values(o.entities).filter(n=>n.platform===q),t=e.filter(n=>B.has(n.translation_key)),r=[];for(let n of t){let s=o.states[n.entity_id];if(!s)continue;let i=s.attributes||{},l=n.device_id?o.devices?.[n.device_id]:null,c=l?.name_by_user||l?.name||i.friendly_name||n.entity_id,d={entityId:n.entity_id,deviceId:n.device_id,name:c,kind:i.kind,provider:i.provider,url:i.url,value:["unknown","unavailable"].includes(s.state)?null:Number(s.state),unit:i.unit_of_measurement,resolutionStatus:null,closed:null,endDate:null,marketState:null,publishedDate:i.published_date??null,source:i.source??null,volume24hr:null,liquidity:null,previousClose:null};for(let _ of e){if(_.device_id!==n.device_id)continue;let h=o.states[_.entity_id];if(!h)continue;let x=["unknown","unavailable"].includes(h.state)?null:Number(h.state);switch(_.translation_key){case"resolution_status":d.resolutionStatus=h.state;break;case"closed":d.closed=h.state==="on";break;case"end_date":d.endDate=h.state;break;case"market_state":d.marketState=h.state;break;case"volume_24hr":d.volume24hr=x;break;case"liquidity":d.liquidity=x;break;case"previous_close":d.previousClose=x;break;default:break}}r.push(d)}return r}function y(o){if(!o||o.length<2)return{changePct:null,deltaPp:null};let e=o[0].p,r=o[o.length-1].p-e;return{changePct:e?r/e*100:null,deltaPp:r}}function w(o,e=80,t=24){if(!o||o.length<2)return null;let r=o.map(d=>d.p),n=Math.min(...r),i=Math.max(...r)-n||1,l=e/(o.length-1);return`M${o.map((d,_)=>{let h=_*l,x=t-(d.p-n)/i*t;return`${h.toFixed(1)},${x.toFixed(1)}`}).join(" L")}`}var G=6e4,V={polymarket:"Polymarket",finnhub:"Finnhub",alpaca:"Alpaca"},R=class extends HTMLElement{static getConfigElement(){return document.createElement("marketsentry-card-editor")}static getStubConfig(){return{type:"custom:marketsentry-card",group_by:"kind"}}constructor(){super(),this.attachShadow({mode:"open"}),this._history=new Map,this._lastHistoryFetch=0}setConfig(e){if(e.kinds&&!Array.isArray(e.kinds))throw new Error("marketsentry-card: 'kinds' must be a list");this._config={group_by:"none",kinds:void 0,...e},this._render()}set hass(e){this._hass=e,this._maybeRefreshHistory(),this._render()}getCardSize(){return 1+g(this._hass).length}async _maybeRefreshHistory(){if(!this._hass)return;let e=Date.now();if(e-this._lastHistoryFetch<G)return;this._lastHistoryFetch=e;let t=g(this._hass);await Promise.all(t.map(async r=>{if(r.deviceId)try{let n=await this._hass.callWS({type:"marketsentry/history",device_id:r.deviceId});this._history.set(r.entityId,n?.history??[])}catch{}})),this._render()}_render(){if(!this.shadowRoot)return;if(!this._hass||!this._config){this.shadowRoot.innerHTML="";return}let e=g(this._hass),t=N(e,this._config.kinds),r=I(t,this._config.group_by),n=m(this._hass);this.shadowRoot.innerHTML=`
      <style>${j}</style>
      <ha-card>
        ${this._config.title?`<h1 class="card-header">${p(this._config.title)}</h1>`:""}
        <div class="content">
          ${r.length===0?`<div class="empty">${p(a(n,"empty_card"))}</div>`:""}
          ${r.map(s=>this._renderGroup(s,n)).join("")}
        </div>
      </ha-card>
    `}_groupLabel(e,t){if(this._config.group_by==="provider")return V[e]||(e==="fx"?a(t,"group_fx"):e);if(this._config.group_by==="kind"){if(e==="outcome")return a(t,"group_predictions");if(e==="stock")return a(t,"group_stocks");if(e==="fx")return a(t,"group_fx")}return e}_renderGroup(e,t){let r=e.label!=null?this._groupLabel(e.label,t):null;return`
      ${r?`<div class="group-label">${p(r)}</div>`:""}
      ${e.rows.map(n=>this._renderRow(n,t)).join("")}
    `}_renderRow(e,t){return e.kind==="outcome"?this._renderOutcomeRow(e,t):this._renderGenericRow(e,t)}_renderOutcomeRow(e,t){let r=this._history.get(e.entityId)||[],{deltaPp:n}=y(r),s=b(e.kind,null,n),i=(n??0)>=0?"positive":"negative",l=v(e),c=a(t,`badge_${l}`),d=F(e.url),_=e.value==null?0:Math.min(100,Math.max(0,e.value));return`
      <div class="row" part="row">
        <div class="row-name" title="${T(e.name)}">
          ${d?`<a href="${d}" target="_blank" rel="noopener">${p(e.name)}</a>`:p(e.name)}
        </div>
        <div class="row-chips">
          <span class="badge badge-${z(l)}">${p(c)}</span>
        </div>
        <div class="prob-line">
          <div class="prob-bar"><div class="prob-fill" style="width:${_}%"></div></div>
          <div class="prob-value">
            <span class="value" dir="ltr">${p(f(e.kind,e.value,e.unit))}</span>
            ${s?`<span class="change ${i}" dir="ltr">${p(s)}</span>`:""}
          </div>
        </div>
      </div>
    `}_renderGenericRow(e,t){let r=this._history.get(e.entityId)||[],{changePct:n,deltaPp:s}=y(r),i=w(r),l=b(e.kind,n,s),c=(s??n??0)>=0?"positive":"negative",d=v(e),_=a(t,`badge_${d}`),h=F(e.url);return`
      <div class="row" part="row">
        <div class="row-top">
          <div class="row-name" title="${T(e.name)}">
            ${h?`<a href="${h}" target="_blank" rel="noopener">${p(e.name)}</a>`:p(e.name)}
          </div>
          <div class="row-value">
            <div class="value" dir="ltr">${p(f(e.kind,e.value,e.unit))}</div>
            ${l?`<div class="change ${c}" dir="ltr">${p(l)}</div>`:""}
          </div>
        </div>
        <div class="row-bottom">
          <div class="row-chips">
            ${e.kind==="stock"?`<span class="chip">${p(a(t,`chip_${k(e.marketState)}`))}</span>`:""}
            ${e.kind==="fx"?`<span class="chip">${p(e.source==="boi"||/boi/.test(e.source||"")?a(t,"fx_boi"):a(t,"fx_market"))}</span>`:""}
            ${e.kind!=="stock"?`<span class="badge badge-${z(d)}">${p(_)}</span>`:""}
          </div>
          <div class="row-spark">
            ${i?`<svg viewBox="0 0 80 24" preserveAspectRatio="none"><path d="${i}" fill="none" stroke="currentColor" stroke-width="1.5" /></svg>`:""}
          </div>
        </div>
      </div>
    `}};function p(o){return String(o??"").replace(/[&<>"']/g,e=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[e])}function T(o){return p(o)}function F(o){if(!o)return null;try{let e=new URL(o,window.location.origin);return e.protocol!=="http:"&&e.protocol!=="https:"?null:T(e.href)}catch{return null}}function z(o){return String(o).toLowerCase().replace(/[\s_]+/g,"-")}var j=`
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
`;customElements.define("marketsentry-card",R);window.customCards=window.customCards||[];window.customCards.push({type:"marketsentry-card",name:"MarketSentry Pro",description:"Rows for every tracked Polymarket/Finnhub/Alpaca/FX instrument, grouped and filterable.",preview:!0});var U=[{value:"outcome",labelKey:"group_predictions"},{value:"stock",labelKey:"group_stocks"},{value:"fx",labelKey:"group_fx"}],L=class extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"})}setConfig(e){let t={group_by:"none",kinds:void 0,...e},r=JSON.stringify(t);this._configKey!==r&&(this._config=t,this._configKey=r,this._render())}set hass(e){this._hass=e}connectedCallback(){this._render()}_emitChange(){this._configKey=JSON.stringify(this._config),this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:!0,composed:!0}))}_render(){if(!this.shadowRoot||!this._config)return;this.shadowRoot.textContent="";let e=document.createElement("style");e.textContent=Y,this.shadowRoot.appendChild(e);let t=document.createElement("div");t.className="editor";let r=m(this._hass);t.appendChild(this._buildTitleField(r)),t.appendChild(this._buildGroupByField(r)),t.appendChild(this._buildKindsField(r)),this.shadowRoot.appendChild(t)}_buildTitleField(e){let t=document.createElement("div");t.className="field";let r=document.createElement("label");r.textContent=a(e,"editor_title");let n=document.createElement("input");return n.type="text",n.value=this._config.title||"",n.addEventListener("input",()=>{this._config={...this._config,title:n.value||void 0},this._emitChange()}),t.append(r,n),t}_buildGroupByField(e){let t=document.createElement("div");t.className="field";let r=document.createElement("label");r.textContent=a(e,"editor_group_by");let n=document.createElement("select");for(let s of["none","provider","kind"]){let i=document.createElement("option");i.value=s,i.textContent=a(e,`editor_group_${s}`),i.selected=this._config.group_by===s,n.appendChild(i)}return n.addEventListener("change",()=>{this._config={...this._config,group_by:n.value},this._emitChange()}),t.append(r,n),t}_buildKindsField(e){let t=document.createElement("div");t.className="field";let r=document.createElement("label");r.textContent=a(e,"editor_kinds"),t.appendChild(r);let n=new Set(this._config.kinds||[]);for(let{value:s,labelKey:i}of U){let l=document.createElement("label");l.className="checkbox-row";let c=document.createElement("input");c.type="checkbox",c.checked=n.has(s),c.addEventListener("change",()=>{let d=new Set(this._config.kinds||[]);c.checked?d.add(s):d.delete(s),this._config={...this._config,kinds:d.size?Array.from(d):void 0},this._emitChange()}),l.append(c,document.createTextNode(` ${a(e,i)}`)),t.appendChild(l)}return t}},Y=`
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
`;customElements.define("marketsentry-card-editor",L);var J=6e4,A=class extends HTMLElement{static getConfigElement(){return document.createElement("marketsentry-instrument-card-editor")}static getStubConfig(e){return{type:"custom:marketsentry-instrument-card",entity:g(e)[0]?.entityId||""}}constructor(){super(),this.attachShadow({mode:"open"}),this._history=[],this._lastHistoryFetch=0}setConfig(e){if(!e.entity)throw new Error("marketsentry-instrument-card: 'entity' is required");this._config={...e},this._render()}set hass(e){this._hass=e,this._maybeRefreshHistory(),this._render()}getCardSize(){return 3}_findRow(){return this._hass&&g(this._hass).find(e=>e.entityId===this._config.entity)||null}async _maybeRefreshHistory(){if(!this._hass)return;let e=Date.now();if(e-this._lastHistoryFetch<J)return;this._lastHistoryFetch=e;let t=this._findRow();if(t?.deviceId){try{let r=await this._hass.callWS({type:"marketsentry/history",device_id:t.deviceId});this._history=r?.history??[]}catch{}this._render()}}_render(){if(!this.shadowRoot)return;if(!this._hass||!this._config){this.shadowRoot.innerHTML="";return}let e=this._findRow(),t=m(this._hass);this.shadowRoot.innerHTML=`
      <style>${W}</style>
      <ha-card>
        <div class="content">
          ${e?this._renderBody(e,t):`<div class="empty">${u(a(t,"empty_instrument",{entity:this._config.entity}))}</div>`}
        </div>
      </ha-card>
    `}_renderBody(e,t){return e.kind==="outcome"?this._renderOutcome(e,t):this._renderGeneric(e,t)}_renderOutcome(e,t){let{deltaPp:r}=y(this._history),n=b(e.kind,null,r),s=(r??0)>=0?"positive":"negative",i=v(e),l=a(t,`badge_${i}`),c=O(e.url),d=e.value==null?0:Math.min(100,Math.max(0,e.value));return`
      <div class="title" title="${M(e.name)}">
        ${c?`<a href="${c}" target="_blank" rel="noopener">${u(e.name)}</a>`:u(e.name)}
      </div>
      <div class="chips">
        <span class="badge badge-${D(i)}">${u(l)}</span>
      </div>
      <div class="prob-line">
        <div class="prob-bar"><div class="prob-fill" style="width:${d}%"></div></div>
        <div class="prob-value">
          <span class="value" dir="ltr">${u(f(e.kind,e.value,e.unit))}</span>
          ${n?`<span class="change ${s}" dir="ltr">${u(n)}</span>`:""}
        </div>
      </div>
      <div class="stats">
        <div class="stat"><span class="stat-label">${u(a(t,"stat_volume_24h"))}</span><span class="stat-value" dir="ltr">${S(e.volume24hr)}</span></div>
        <div class="stat"><span class="stat-label">${u(a(t,"stat_liquidity"))}</span><span class="stat-value" dir="ltr">${S(e.liquidity)}</span></div>
      </div>
      <div class="footer">${u(a(t,"footer_ends",{date:C(e.endDate,E[t])}))}</div>
    `}_renderGeneric(e,t){let{changePct:r,deltaPp:n}=y(this._history),s=w(this._history,280,60),i=b(e.kind,r,n),l=(n??r??0)>=0?"positive":"negative",c=v(e),d=a(t,`badge_${c}`),_=O(e.url);return`
      <div class="title" title="${M(e.name)}">
        ${_?`<a href="${_}" target="_blank" rel="noopener">${u(e.name)}</a>`:u(e.name)}
      </div>
      <div class="chips">
        ${e.kind==="stock"?`<span class="chip">${u(a(t,`chip_${k(e.marketState)}`))}</span>`:""}
        ${e.kind==="fx"?`<span class="chip">${u(e.source==="boi"||/boi/.test(e.source||"")?a(t,"fx_boi"):a(t,"fx_market"))}</span>`:""}
        ${e.kind!=="stock"?`<span class="badge badge-${D(c)}">${u(d)}</span>`:""}
      </div>
      <div class="big-value">
        <span class="value" dir="ltr">${u(f(e.kind,e.value,e.unit))}</span>
        ${i?`<span class="change ${l}" dir="ltr">${u(i)}</span>`:""}
      </div>
      <div class="big-spark">
        ${s?`<svg viewBox="0 0 280 60" preserveAspectRatio="none"><path d="${s}" fill="none" stroke="currentColor" stroke-width="2" /></svg>`:""}
      </div>
      ${e.kind==="stock"?`<div class="stats"><div class="stat"><span class="stat-label">${u(a(t,"stat_prev_close"))}</span><span class="stat-value" dir="ltr">${u(f(e.kind,e.previousClose,e.unit))}</span></div></div>`:""}
      ${e.kind==="fx"?`<div class="footer">${u(a(t,"footer_published",{date:C(e.publishedDate,E[t])}))}</div>`:""}
    `}};function u(o){return String(o??"").replace(/[&<>"']/g,e=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[e])}function M(o){return u(o)}function O(o){if(!o)return null;try{let e=new URL(o,window.location.origin);return e.protocol!=="http:"&&e.protocol!=="https:"?null:M(e.href)}catch{return null}}function D(o){return String(o).toLowerCase().replace(/[\s_]+/g,"-")}var W=`
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
`;customElements.define("marketsentry-instrument-card",A);window.customCards=window.customCards||[];window.customCards.push({type:"marketsentry-instrument-card",name:"MarketSentry Pro (single instrument)",description:"One tracked instrument per card, with a kind-specific detailed view (Polymarket probability bar + stats, stock/FX price + sparkline).",preview:!0});var P=class extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"})}setConfig(e){let t={...e},r=JSON.stringify(t);this._configKey!==r&&(this._config=t,this._configKey=r,this._render())}set hass(e){this._hass=e;let t=g(e),r=JSON.stringify(t.map(n=>[n.entityId,n.name]));this._rowsKey!==r&&(this._rowsKey=r,this._render())}connectedCallback(){this._render()}_emitChange(){this._configKey=JSON.stringify(this._config),this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:!0,composed:!0}))}_render(){if(!this.shadowRoot||!this._config)return;this.shadowRoot.textContent="";let e=document.createElement("style");e.textContent=X,this.shadowRoot.appendChild(e);let t=document.createElement("div");t.className="editor",t.appendChild(this._buildEntityField()),this.shadowRoot.appendChild(t)}_buildEntityField(){let e=m(this._hass),t=document.createElement("div");t.className="field";let r=document.createElement("label");r.textContent=a(e,"editor_instrument"),t.appendChild(r);let n=this._hass?g(this._hass):[],s=document.createElement("select"),i=document.createElement("option");i.value="",i.textContent=n.length?a(e,"editor_choose"):a(e,"editor_no_instruments"),i.disabled=!0,i.selected=!this._config.entity,s.appendChild(i);for(let l of n){let c=document.createElement("option");c.value=l.entityId,c.textContent=l.name,c.selected=this._config.entity===l.entityId,s.appendChild(c)}return s.addEventListener("change",()=>{this._config={...this._config,entity:s.value},this._emitChange()}),t.appendChild(s),t}},X=`
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
`;customElements.define("marketsentry-instrument-card-editor",P);
