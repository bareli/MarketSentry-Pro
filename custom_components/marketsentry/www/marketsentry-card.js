function h(r,e,t){return e==null||Number.isNaN(e)?"\u2014":r==="outcome"?`${e.toFixed(1)}%`:r==="fx"?`${e.toFixed(4)}${t?` ${t}`:""}`:`${t==="USD"?"$":t?`${t} `:""}${e.toFixed(2)}`}function b(r,e,t){return r==="outcome"?t==null||Number.isNaN(t)?null:`${t>0?"+":""}${t.toFixed(1)}pp`:e==null||Number.isNaN(e)?null:`${e>0?"+":""}${e.toFixed(2)}%`}function C(r){if(r==null||Number.isNaN(r))return"\u2014";let e=Math.abs(r);return e>=1e6?`$${(r/1e6).toFixed(1)}M`:e>=1e3?`$${(r/1e3).toFixed(1)}K`:`$${r.toFixed(0)}`}function w(r,e="en-US"){if(!r)return"\u2014";let t=new Date(r);return Number.isNaN(t.getTime())?"\u2014":t.toLocaleDateString(e,{year:"numeric",month:"short",day:"numeric"})}var j={pre:"pre",regular:"open",post:"after",closed:"closed"};function S(r){return r&&j[r]||"closed"}function v(r,e=new Date){if(r.kind==="outcome"){if(r.resolutionStatus==="resolved")return"resolved";if(r.closed)return"closed";if(r.endDate){let t=(new Date(r.endDate).getTime()-e.getTime())/36e5;if(t>=0&&t<=24)return"closing_soon"}return"live"}return r.kind==="stock"?r.marketState&&r.marketState!=="closed"?"open":"closed":r.kind==="fx"?r.publishedDate&&new Date(r.publishedDate).toDateString()===e.toDateString()?"updated_today":"stale":r.kind==="crypto"?"live":""}function F(r,e){return!e||e.length===0?r:r.filter(t=>e.includes(t.kind))}function z(r,e){if(!e||e==="none")return r.length?[{label:null,rows:r}]:[];let t=new Map;for(let n of r){let o=e==="provider"?n.provider:n.kind;t.has(o)||t.set(o,[]),t.get(o).push(n)}return Array.from(t.entries()).map(([n,o])=>({label:n,rows:o}))}var U=["en","he","de","fr","es","pt-BR","it","nl"],E={en:"en-US",he:"he-IL",de:"de-DE",fr:"fr-FR",es:"es-ES","pt-BR":"pt-BR",it:"it-IT",nl:"nl-NL"},$={en:{empty_card:"No tracked instruments match this card's filters.",empty_card_no_instruments:"No MarketSentry Pro instruments are tracked yet. Add one via Settings > Devices & services > MarketSentry Pro > Add instrument.",empty_instrument:"Entity not found or not a MarketSentry Pro instrument: {entity}",empty_instrument_no_entity:"No instrument is configured for this card yet.",empty_instrument_add_instrument:"Add one via Settings > Devices & services > MarketSentry Pro > Add instrument",group_predictions:"Prediction markets",group_stocks:"Stocks",group_crypto:"Cryptocurrencies",group_fx:"Exchange rates",badge_resolved:"Resolved",badge_closed:"Closed",badge_closing_soon:"Closing soon",badge_live:"Live",badge_open:"Open",badge_stale:"Stale",badge_updated_today:"Updated today",chip_pre:"Pre",chip_open:"Open",chip_after:"After",chip_closed:"Closed",fx_boi:"Bank of Israel",fx_market:"Market",stat_volume_24h:"Volume 24h",stat_liquidity:"Liquidity",stat_prev_close:"Prev close",footer_ends:"Ends {date}",footer_published:"Published {date}",editor_title:"Title (optional)",editor_group_by:"Group by",editor_group_none:"none",editor_group_provider:"provider",editor_group_kind:"kind",editor_kinds:"Kinds (none selected = all)",editor_instrument:"Instrument",editor_choose:"Choose an instrument\u2026",editor_no_instruments:"No MarketSentry Pro instruments found"},he:{empty_card:"\u05D0\u05D9\u05DF \u05DE\u05DB\u05E9\u05D9\u05E8\u05D9\u05DD \u05DE\u05E0\u05D5\u05D8\u05E8\u05D9\u05DD \u05D4\u05EA\u05D5\u05D0\u05DE\u05D9\u05DD \u05D0\u05EA \u05D4\u05DE\u05E1\u05E0\u05E0\u05D9\u05DD \u05E9\u05DC \u05DB\u05E8\u05D8\u05D9\u05E1 \u05D6\u05D4.",empty_card_no_instruments:"\u05D0\u05D9\u05DF \u05E2\u05D3\u05D9\u05D9\u05DF \u05DE\u05DB\u05E9\u05D9\u05E8\u05D9 MarketSentry Pro \u05D1\u05DE\u05E2\u05E7\u05D1. \u05D4\u05D5\u05E1\u05E3 \u05D0\u05D7\u05D3 \u05D3\u05E8\u05DA \u05D4\u05D2\u05D3\u05E8\u05D5\u05EA > \u05DE\u05DB\u05E9\u05D9\u05E8\u05D9\u05DD \u05D5\u05E9\u05D9\u05E8\u05D5\u05EA\u05D9\u05DD > MarketSentry Pro > \u05D4\u05D5\u05E1\u05E4\u05EA \u05DE\u05DB\u05E9\u05D9\u05E8.",empty_instrument:"\u05D4\u05D9\u05E9\u05D5\u05EA \u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D4 \u05D0\u05D5 \u05E9\u05D0\u05D9\u05E0\u05D4 \u05DE\u05DB\u05E9\u05D9\u05E8 MarketSentry Pro: {entity}",empty_instrument_no_entity:"\u05DC\u05D0 \u05D4\u05D5\u05D2\u05D3\u05E8 \u05DE\u05DB\u05E9\u05D9\u05E8 \u05E2\u05D1\u05D5\u05E8 \u05DB\u05E8\u05D8\u05D9\u05E1 \u05D6\u05D4.",empty_instrument_add_instrument:"\u05D4\u05D5\u05E1\u05E3 \u05DE\u05DB\u05E9\u05D9\u05E8 \u05D3\u05E8\u05DA \u05D4\u05D2\u05D3\u05E8\u05D5\u05EA > \u05DE\u05DB\u05E9\u05D9\u05E8\u05D9\u05DD \u05D5\u05E9\u05D9\u05E8\u05D5\u05EA\u05D9\u05DD > MarketSentry Pro > \u05D4\u05D5\u05E1\u05E4\u05EA \u05DE\u05DB\u05E9\u05D9\u05E8",group_predictions:"\u05E9\u05D5\u05E7\u05D9 \u05D7\u05D9\u05D6\u05D5\u05D9",group_stocks:"\u05DE\u05E0\u05D9\u05D5\u05EA",group_crypto:"\u05DE\u05D8\u05D1\u05E2\u05D5\u05EA \u05E7\u05E8\u05D9\u05E4\u05D8\u05D5",group_fx:"\u05E9\u05E2\u05E8\u05D9 \u05D7\u05DC\u05D9\u05E4\u05D9\u05DF",badge_resolved:"\u05E0\u05E4\u05EA\u05E8",badge_closed:"\u05E1\u05D2\u05D5\u05E8",badge_closing_soon:"\u05E0\u05E1\u05D2\u05E8 \u05D1\u05E7\u05E8\u05D5\u05D1",badge_live:"\u05E4\u05E2\u05D9\u05DC",badge_open:"\u05E4\u05EA\u05D5\u05D7",badge_stale:"\u05DC\u05D0 \u05DE\u05E2\u05D5\u05D3\u05DB\u05DF",badge_updated_today:"\u05E2\u05D5\u05D3\u05DB\u05DF \u05D4\u05D9\u05D5\u05DD",chip_pre:"\u05D8\u05E8\u05D5\u05DD",chip_open:"\u05E4\u05EA\u05D5\u05D7",chip_after:"\u05D0\u05D7\u05E8\u05D9",chip_closed:"\u05E1\u05D2\u05D5\u05E8",fx_boi:"\u05D1\u05E0\u05E7 \u05D9\u05E9\u05E8\u05D0\u05DC",fx_market:"\u05E9\u05D5\u05E7",stat_volume_24h:"\u05DE\u05D7\u05D6\u05D5\u05E8 24 \u05E9\u05E2\u05D5\u05EA",stat_liquidity:"\u05E0\u05D6\u05D9\u05DC\u05D5\u05EA",stat_prev_close:"\u05E1\u05D2\u05D9\u05E8\u05D4 \u05E7\u05D5\u05D3\u05DE\u05EA",footer_ends:"\u05DE\u05E1\u05EA\u05D9\u05D9\u05DD \u05D1-{date}",footer_published:"\u05E4\u05D5\u05E8\u05E1\u05DD \u05D1-{date}",editor_title:"\u05DB\u05D5\u05EA\u05E8\u05EA (\u05E8\u05E9\u05D5\u05EA)",editor_group_by:"\u05E7\u05D9\u05D1\u05D5\u05E5 \u05DC\u05E4\u05D9",editor_group_none:"\u05DC\u05DC\u05D0",editor_group_provider:"\u05E1\u05E4\u05E7",editor_group_kind:"\u05E1\u05D5\u05D2",editor_kinds:"\u05E1\u05D5\u05D2\u05D9\u05DD (\u05DC\u05DC\u05D0 \u05D1\u05D7\u05D9\u05E8\u05D4 = \u05D4\u05DB\u05D5\u05DC)",editor_instrument:"\u05DE\u05DB\u05E9\u05D9\u05E8",editor_choose:"\u05D1\u05D7\u05E8 \u05DE\u05DB\u05E9\u05D9\u05E8\u2026",editor_no_instruments:"\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D5 \u05DE\u05DB\u05E9\u05D9\u05E8\u05D9 MarketSentry Pro"},de:{empty_card:"Keine verfolgten Instrumente entsprechen den Filtern dieser Karte.",empty_card_no_instruments:"Es werden noch keine MarketSentry-Pro-Instrumente verfolgt. F\xFCgen Sie eines \xFCber Einstellungen > Ger\xE4te & Dienste > MarketSentry Pro > Instrument hinzuf\xFCgen hinzu.",empty_instrument:"Entit\xE4t nicht gefunden oder kein MarketSentry-Pro-Instrument: {entity}",empty_instrument_no_entity:"F\xFCr diese Karte ist noch kein Instrument konfiguriert.",empty_instrument_add_instrument:"F\xFCgen Sie eines \xFCber Einstellungen > Ger\xE4te & Dienste > MarketSentry Pro > Instrument hinzuf\xFCgen hinzu",group_predictions:"Prognosem\xE4rkte",group_stocks:"Aktien",group_crypto:"Kryptow\xE4hrungen",group_fx:"Wechselkurse",badge_resolved:"Aufgel\xF6st",badge_closed:"Geschlossen",badge_closing_soon:"Schlie\xDFt bald",badge_live:"Live",badge_open:"Offen",badge_stale:"Veraltet",badge_updated_today:"Heute aktualisiert",chip_pre:"Vorb\xF6rse",chip_open:"Offen",chip_after:"Nachb\xF6rse",chip_closed:"Geschlossen",fx_boi:"Bank of Israel",fx_market:"Markt",stat_volume_24h:"24h-Volumen",stat_liquidity:"Liquidit\xE4t",stat_prev_close:"Vorheriger Schluss",footer_ends:"Endet am {date}",footer_published:"Ver\xF6ffentlicht am {date}",editor_title:"Titel (optional)",editor_group_by:"Gruppieren nach",editor_group_none:"keine",editor_group_provider:"Anbieter",editor_group_kind:"Art",editor_kinds:"Arten (keine Auswahl = alle)",editor_instrument:"Instrument",editor_choose:"Instrument w\xE4hlen\u2026",editor_no_instruments:"Keine MarketSentry-Pro-Instrumente gefunden"},fr:{empty_card:"Aucun instrument suivi ne correspond aux filtres de cette carte.",empty_card_no_instruments:"Aucun instrument MarketSentry Pro n'est encore suivi. Ajoutez-en un via Param\xE8tres > Appareils et services > MarketSentry Pro > Ajouter un instrument.",empty_instrument:"Entit\xE9 introuvable ou n'est pas un instrument MarketSentry Pro : {entity}",empty_instrument_no_entity:"Aucun instrument n'est configur\xE9 pour cette carte.",empty_instrument_add_instrument:"Ajoutez-en un via Param\xE8tres > Appareils et services > MarketSentry Pro > Ajouter un instrument",group_predictions:"March\xE9s de pr\xE9diction",group_stocks:"Actions",group_crypto:"Cryptomonnaies",group_fx:"Taux de change",badge_resolved:"R\xE9solu",badge_closed:"Ferm\xE9",badge_closing_soon:"Ferme bient\xF4t",badge_live:"En direct",badge_open:"Ouvert",badge_stale:"Obsol\xE8te",badge_updated_today:"Mis \xE0 jour aujourd'hui",chip_pre:"Avant-bourse",chip_open:"Ouvert",chip_after:"Apr\xE8s-bourse",chip_closed:"Ferm\xE9",fx_boi:"Banque d'Isra\xEBl",fx_market:"March\xE9",stat_volume_24h:"Volume 24h",stat_liquidity:"Liquidit\xE9",stat_prev_close:"Cl\xF4ture pr\xE9c\xE9dente",footer_ends:"Se termine le {date}",footer_published:"Publi\xE9 le {date}",editor_title:"Titre (facultatif)",editor_group_by:"Grouper par",editor_group_none:"aucun",editor_group_provider:"fournisseur",editor_group_kind:"type",editor_kinds:"Types (aucune s\xE9lection = tous)",editor_instrument:"Instrument",editor_choose:"Choisir un instrument\u2026",editor_no_instruments:"Aucun instrument MarketSentry Pro trouv\xE9"},es:{empty_card:"Ning\xFAn instrumento seguido coincide con los filtros de esta tarjeta.",empty_card_no_instruments:"Todav\xEDa no se sigue ning\xFAn instrumento de MarketSentry Pro. A\xF1ade uno desde Configuraci\xF3n > Dispositivos y servicios > MarketSentry Pro > A\xF1adir instrumento.",empty_instrument:"Entidad no encontrada o no es un instrumento de MarketSentry Pro: {entity}",empty_instrument_no_entity:"No hay ning\xFAn instrumento configurado para esta tarjeta.",empty_instrument_add_instrument:"A\xF1ade uno desde Configuraci\xF3n > Dispositivos y servicios > MarketSentry Pro > A\xF1adir instrumento",group_predictions:"Mercados de predicci\xF3n",group_stocks:"Acciones",group_crypto:"Criptomonedas",group_fx:"Tipos de cambio",badge_resolved:"Resuelto",badge_closed:"Cerrado",badge_closing_soon:"Cierra pronto",badge_live:"En vivo",badge_open:"Abierto",badge_stale:"Desactualizado",badge_updated_today:"Actualizado hoy",chip_pre:"Pre-apertura",chip_open:"Abierto",chip_after:"Post-cierre",chip_closed:"Cerrado",fx_boi:"Banco de Israel",fx_market:"Mercado",stat_volume_24h:"Volumen 24h",stat_liquidity:"Liquidez",stat_prev_close:"Cierre anterior",footer_ends:"Termina el {date}",footer_published:"Publicado el {date}",editor_title:"T\xEDtulo (opcional)",editor_group_by:"Agrupar por",editor_group_none:"ninguno",editor_group_provider:"proveedor",editor_group_kind:"tipo",editor_kinds:"Tipos (ninguno seleccionado = todos)",editor_instrument:"Instrumento",editor_choose:"Elige un instrumento\u2026",editor_no_instruments:"No se encontraron instrumentos de MarketSentry Pro"},"pt-BR":{empty_card:"Nenhum instrumento acompanhado corresponde aos filtros deste cart\xE3o.",empty_card_no_instruments:"Nenhum instrumento do MarketSentry Pro est\xE1 sendo acompanhado ainda. Adicione um em Configura\xE7\xF5es > Dispositivos e servi\xE7os > MarketSentry Pro > Adicionar instrumento.",empty_instrument:"Entidade n\xE3o encontrada ou n\xE3o \xE9 um instrumento MarketSentry Pro: {entity}",empty_instrument_no_entity:"Nenhum instrumento est\xE1 configurado para este cart\xE3o ainda.",empty_instrument_add_instrument:"Adicione um em Configura\xE7\xF5es > Dispositivos e servi\xE7os > MarketSentry Pro > Adicionar instrumento",group_predictions:"Mercados de previs\xE3o",group_stocks:"A\xE7\xF5es",group_crypto:"Criptomoedas",group_fx:"Taxas de c\xE2mbio",badge_resolved:"Resolvido",badge_closed:"Fechado",badge_closing_soon:"Fecha em breve",badge_live:"Ao vivo",badge_open:"Aberto",badge_stale:"Desatualizado",badge_updated_today:"Atualizado hoje",chip_pre:"Pr\xE9-mercado",chip_open:"Aberto",chip_after:"P\xF3s-mercado",chip_closed:"Fechado",fx_boi:"Banco de Israel",fx_market:"Mercado",stat_volume_24h:"Volume 24h",stat_liquidity:"Liquidez",stat_prev_close:"Fechamento anterior",footer_ends:"Termina em {date}",footer_published:"Publicado em {date}",editor_title:"T\xEDtulo (opcional)",editor_group_by:"Agrupar por",editor_group_none:"nenhum",editor_group_provider:"provedor",editor_group_kind:"tipo",editor_kinds:"Tipos (nenhum selecionado = todos)",editor_instrument:"Instrumento",editor_choose:"Escolha um instrumento\u2026",editor_no_instruments:"Nenhum instrumento MarketSentry Pro encontrado"},it:{empty_card:"Nessuno strumento seguito corrisponde ai filtri di questa scheda.",empty_card_no_instruments:"Nessuno strumento MarketSentry Pro \xE8 ancora monitorato. Aggiungine uno da Impostazioni > Dispositivi e servizi > MarketSentry Pro > Aggiungi strumento.",empty_instrument:"Entit\xE0 non trovata o non \xE8 uno strumento MarketSentry Pro: {entity}",empty_instrument_no_entity:"Nessuno strumento \xE8 configurato per questa scheda.",empty_instrument_add_instrument:"Aggiungine uno da Impostazioni > Dispositivi e servizi > MarketSentry Pro > Aggiungi strumento",group_predictions:"Mercati predittivi",group_stocks:"Azioni",group_crypto:"Criptovalute",group_fx:"Tassi di cambio",badge_resolved:"Risolto",badge_closed:"Chiuso",badge_closing_soon:"Chiude a breve",badge_live:"Live",badge_open:"Aperto",badge_stale:"Non aggiornato",badge_updated_today:"Aggiornato oggi",chip_pre:"Pre-mercato",chip_open:"Aperto",chip_after:"Post-mercato",chip_closed:"Chiuso",fx_boi:"Banca d'Israele",fx_market:"Mercato",stat_volume_24h:"Volume 24h",stat_liquidity:"Liquidit\xE0",stat_prev_close:"Chiusura precedente",footer_ends:"Termina il {date}",footer_published:"Pubblicato il {date}",editor_title:"Titolo (opzionale)",editor_group_by:"Raggruppa per",editor_group_none:"nessuno",editor_group_provider:"fornitore",editor_group_kind:"tipo",editor_kinds:"Tipi (nessuna selezione = tutti)",editor_instrument:"Strumento",editor_choose:"Scegli uno strumento\u2026",editor_no_instruments:"Nessuno strumento MarketSentry Pro trovato"},nl:{empty_card:"Geen gevolgde instrumenten komen overeen met de filters van deze kaart.",empty_card_no_instruments:"Er worden nog geen MarketSentry Pro-instrumenten gevolgd. Voeg er een toe via Instellingen > Apparaten en services > MarketSentry Pro > Instrument toevoegen.",empty_instrument:"Entiteit niet gevonden of geen MarketSentry Pro-instrument: {entity}",empty_instrument_no_entity:"Er is nog geen instrument geconfigureerd voor deze kaart.",empty_instrument_add_instrument:"Voeg er een toe via Instellingen > Apparaten en services > MarketSentry Pro > Instrument toevoegen",group_predictions:"Voorspellingsmarkten",group_stocks:"Aandelen",group_crypto:"Cryptocurrencies",group_fx:"Wisselkoersen",badge_resolved:"Afgewikkeld",badge_closed:"Gesloten",badge_closing_soon:"Sluit binnenkort",badge_live:"Live",badge_open:"Open",badge_stale:"Verouderd",badge_updated_today:"Vandaag bijgewerkt",chip_pre:"Voorbeurs",chip_open:"Open",chip_after:"Naborsbeurs",chip_closed:"Gesloten",fx_boi:"Bank of Israel",fx_market:"Markt",stat_volume_24h:"24u volume",stat_liquidity:"Liquiditeit",stat_prev_close:"Vorige slotkoers",footer_ends:"Eindigt op {date}",footer_published:"Gepubliceerd op {date}",editor_title:"Titel (optioneel)",editor_group_by:"Groeperen op",editor_group_none:"geen",editor_group_provider:"aanbieder",editor_group_kind:"type",editor_kinds:"Typen (geen selectie = alle)",editor_instrument:"Instrument",editor_choose:"Kies een instrument\u2026",editor_no_instruments:"Geen MarketSentry Pro-instrumenten gevonden"}};function f(r){let e=r?.locale?.language||r?.language||"en";if($[e])return e;let t=e.split("-")[0];return U.find(o=>o.split("-")[0]===t)||"en"}function a(r,e,t){let o=($[r]||$.en)[e]??$.en[e]??e;if(t)for(let[i,s]of Object.entries(t))o=o.replace(`{${i}}`,s);return o}var Y="marketsentry",X=new Set(["probability","price","rate"]);function m(r){if(!r||!r.entities||!r.states)return[];let e=Object.values(r.entities).filter(o=>o.platform===Y),t=e.filter(o=>X.has(o.translation_key)),n=[];for(let o of t){let i=r.states[o.entity_id];if(!i)continue;let s=i.attributes||{},l=o.device_id?r.devices?.[o.device_id]:null,c=l?.name_by_user||l?.name||s.friendly_name||o.entity_id,d={entityId:o.entity_id,deviceId:o.device_id,name:c,kind:s.kind,provider:s.provider,url:s.url,value:["unknown","unavailable"].includes(i.state)?null:Number(i.state),unit:s.unit_of_measurement,resolutionStatus:null,closed:null,endDate:null,marketState:null,publishedDate:s.published_date??null,source:s.source??null,volume24hr:null,liquidity:null,previousClose:null};for(let g of e){if(g.device_id!==o.device_id)continue;let _=r.states[g.entity_id];if(!_)continue;let y=["unknown","unavailable"].includes(_.state)?null:Number(_.state);switch(g.translation_key){case"resolution_status":d.resolutionStatus=_.state;break;case"closed":d.closed=_.state==="on";break;case"end_date":d.endDate=_.state;break;case"market_state":d.marketState=_.state;break;case"volume_24hr":d.volume24hr=y;break;case"liquidity":d.liquidity=y;break;case"previous_close":d.previousClose=y;break;default:break}}n.push(d)}return n}function k(r){if(!r||r.length<2)return{changePct:null,deltaPp:null};let e=r[0].p,n=r[r.length-1].p-e;return{changePct:e?n/e*100:null,deltaPp:n}}function x(r,e=80,t=24){if(!r||r.length<2)return null;let n=r.map(d=>d.p),o=Math.min(...n),s=Math.max(...n)-o||1,l=e/(r.length-1);return`M${r.map((d,g)=>{let _=g*l,y=t-(d.p-o)/s*t;return`${_.toFixed(1)},${y.toFixed(1)}`}).join(" L")}`}function D(r,e=80,t=24){let n=x(r,e,t);if(!n)return null;let o=e/(r.length-1),i=(r.length-1)*o;return`${n} L${i.toFixed(1)},${t} L0,${t} Z`}function O(r,e=80,t=24){if(!r||r.length<2)return null;let n=r.map(d=>d.p),o=Math.min(...n),s=Math.max(...n)-o||1,l=e/(r.length-1),c=r.length-1;return{x:c*l,y:t-(r[c].p-o)/s*t}}function K(r){if(!r||r.length===0)return null;let e=r.map(t=>t.p);return{min:Math.min(...e),max:Math.max(...e)}}var J=6e4,W={polymarket:"Polymarket",finnhub:"Finnhub",alpaca:"Alpaca",coingecko:"CoinGecko"},P=class extends HTMLElement{static getConfigElement(){return document.createElement("marketsentry-card-editor")}static getStubConfig(){return{type:"custom:marketsentry-card",group_by:"kind"}}constructor(){super(),this.attachShadow({mode:"open"}),this._history=new Map,this._lastHistoryFetch=0}setConfig(e){if(e.kinds&&!Array.isArray(e.kinds))throw new Error("marketsentry-card: 'kinds' must be a list");this._config={group_by:"none",kinds:void 0,...e},this._render()}set hass(e){this._hass=e,this._maybeRefreshHistory(),this._render()}getCardSize(){return 1+m(this._hass).length}async _maybeRefreshHistory(){if(!this._hass)return;let e=Date.now();if(e-this._lastHistoryFetch<J)return;this._lastHistoryFetch=e;let t=m(this._hass);await Promise.all(t.map(async n=>{if(n.deviceId)try{let o=await this._hass.callWS({type:"marketsentry/history",device_id:n.deviceId});this._history.set(n.entityId,o?.history??[])}catch{}})),this._render()}_render(){if(!this.shadowRoot)return;if(!this._hass||!this._config){this.shadowRoot.innerHTML="";return}let e=m(this._hass),t=F(e,this._config.kinds),n=z(t,this._config.group_by),o=f(this._hass);this.shadowRoot.innerHTML=`
      <style>${Z}</style>
      <ha-card>
        ${this._config.title?`<h1 class="card-header">${p(this._config.title)}</h1>`:""}
        <div class="content">
          ${n.length===0?`<div class="empty">${p(a(o,e.length===0?"empty_card_no_instruments":"empty_card"))}</div>`:""}
          ${n.map(i=>this._renderGroup(i,o)).join("")}
        </div>
      </ha-card>
    `}_groupLabel(e,t){if(this._config.group_by==="provider")return W[e]||(e==="fx"?a(t,"group_fx"):e);if(this._config.group_by==="kind"){if(e==="outcome")return a(t,"group_predictions");if(e==="stock")return a(t,"group_stocks");if(e==="crypto")return a(t,"group_crypto");if(e==="fx")return a(t,"group_fx")}return e}_renderGroup(e,t){let n=e.label!=null?this._groupLabel(e.label,t):null;return`
      ${n?`<div class="group-label">${p(n)}</div>`:""}
      ${e.rows.map(o=>this._renderRow(o,t)).join("")}
    `}_renderRow(e,t){return e.kind==="outcome"?this._renderOutcomeRow(e,t):this._renderGenericRow(e,t)}_renderOutcomeRow(e,t){let n=this._history.get(e.entityId)||[],{deltaPp:o}=k(n),i=b(e.kind,null,o),s=(o??0)>=0?"positive":"negative",l=v(e),c=a(t,`badge_${l}`),d=H(e.url),g=e.value==null?0:Math.min(100,Math.max(0,e.value));return`
      <div class="row" part="row">
        <div class="row-name" title="${A(e.name)}">
          ${d?`<a href="${d}" target="_blank" rel="noopener">${p(e.name)}</a>`:p(e.name)}
        </div>
        <div class="row-chips">
          <span class="badge badge-${q(l)}">${p(c)}</span>
        </div>
        <div class="prob-line">
          <div class="prob-bar"><div class="prob-fill" style="width:${g}%"></div></div>
          <div class="prob-value">
            <span class="value" dir="ltr">${p(h(e.kind,e.value,e.unit))}</span>
            ${i?`<span class="change ${s}" dir="ltr">${p(i)}</span>`:""}
          </div>
        </div>
      </div>
    `}_renderGenericRow(e,t){let n=this._history.get(e.entityId)||[],{changePct:o,deltaPp:i}=k(n),s=x(n),l=b(e.kind,o,i),c=(i??o??0)>=0?"positive":"negative",d=v(e),g=a(t,`badge_${d}`),_=H(e.url);return`
      <div class="row" part="row">
        <div class="row-top">
          <div class="row-name" title="${A(e.name)}">
            ${_?`<a href="${_}" target="_blank" rel="noopener">${p(e.name)}</a>`:p(e.name)}
          </div>
          <div class="row-value">
            <div class="value" dir="ltr">${p(h(e.kind,e.value,e.unit))}</div>
            ${l?`<div class="change ${c}" dir="ltr">${p(l)}</div>`:""}
          </div>
        </div>
        <div class="row-bottom">
          <div class="row-chips">
            ${e.kind==="stock"?`<span class="chip">${p(a(t,`chip_${S(e.marketState)}`))}</span>`:""}
            ${e.kind==="fx"?`<span class="chip">${p(e.source==="boi"||/boi/.test(e.source||"")?a(t,"fx_boi"):a(t,"fx_market"))}</span>`:""}
            ${e.kind!=="stock"?`<span class="badge badge-${q(d)}">${p(g)}</span>`:""}
          </div>
          <div class="row-spark">
            ${s?`<svg viewBox="0 0 80 24" preserveAspectRatio="none"><path d="${s}" fill="none" stroke="currentColor" stroke-width="1.5" /></svg>`:""}
          </div>
        </div>
      </div>
    `}};function p(r){return String(r??"").replace(/[&<>"']/g,e=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[e])}function A(r){return p(r)}function H(r){if(!r)return null;try{let e=new URL(r,window.location.origin);return e.protocol!=="http:"&&e.protocol!=="https:"?null:A(e.href)}catch{return null}}function q(r){return String(r).toLowerCase().replace(/[\s_]+/g,"-")}var Z=`
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
`;customElements.define("marketsentry-card",P);window.customCards=window.customCards||[];window.customCards.push({type:"marketsentry-card",name:"MarketSentry Pro",description:"Rows for every tracked Polymarket/Finnhub/Alpaca/FX instrument, grouped and filterable.",preview:!0});var Q=[{value:"outcome",labelKey:"group_predictions"},{value:"stock",labelKey:"group_stocks"},{value:"crypto",labelKey:"group_crypto"},{value:"fx",labelKey:"group_fx"}],M=class extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"})}setConfig(e){let t={group_by:"none",kinds:void 0,...e},n=JSON.stringify(t);this._configKey!==n&&(this._config=t,this._configKey=n,this._render())}set hass(e){this._hass=e}connectedCallback(){this._render()}_emitChange(){this._configKey=JSON.stringify(this._config),this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:!0,composed:!0}))}_render(){if(!this.shadowRoot||!this._config)return;this.shadowRoot.textContent="";let e=document.createElement("style");e.textContent=ee,this.shadowRoot.appendChild(e);let t=document.createElement("div");t.className="editor";let n=f(this._hass);t.appendChild(this._buildTitleField(n)),t.appendChild(this._buildGroupByField(n)),t.appendChild(this._buildKindsField(n)),this.shadowRoot.appendChild(t)}_buildTitleField(e){let t=document.createElement("div");t.className="field";let n=document.createElement("label");n.textContent=a(e,"editor_title");let o=document.createElement("input");return o.type="text",o.value=this._config.title||"",o.addEventListener("input",()=>{this._config={...this._config,title:o.value||void 0},this._emitChange()}),t.append(n,o),t}_buildGroupByField(e){let t=document.createElement("div");t.className="field";let n=document.createElement("label");n.textContent=a(e,"editor_group_by");let o=document.createElement("select");for(let i of["none","provider","kind"]){let s=document.createElement("option");s.value=i,s.textContent=a(e,`editor_group_${i}`),s.selected=this._config.group_by===i,o.appendChild(s)}return o.addEventListener("change",()=>{this._config={...this._config,group_by:o.value},this._emitChange()}),t.append(n,o),t}_buildKindsField(e){let t=document.createElement("div");t.className="field";let n=document.createElement("label");n.textContent=a(e,"editor_kinds"),t.appendChild(n);let o=new Set(this._config.kinds||[]);for(let{value:i,labelKey:s}of Q){let l=document.createElement("label");l.className="checkbox-row";let c=document.createElement("input");c.type="checkbox",c.checked=o.has(i),c.addEventListener("change",()=>{let d=new Set(this._config.kinds||[]);c.checked?d.add(i):d.delete(i),this._config={...this._config,kinds:d.size?Array.from(d):void 0},this._emitChange()}),l.append(c,document.createTextNode(` ${a(e,s)}`)),t.appendChild(l)}return t}},ee=`
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
`;customElements.define("marketsentry-card-editor",M);var te=6e4,R=class extends HTMLElement{static getConfigElement(){return document.createElement("marketsentry-instrument-card-editor")}static getStubConfig(e){return{type:"custom:marketsentry-instrument-card",entity:m(e)[0]?.entityId||""}}constructor(){super(),this.attachShadow({mode:"open"}),this._history=[],this._lastHistoryFetch=0}setConfig(e){this._config={...e},this._render()}set hass(e){this._hass=e,this._maybeRefreshHistory(),this._render()}getCardSize(){return 3}_findRow(){return this._hass&&m(this._hass).find(e=>e.entityId===this._config.entity)||null}async _maybeRefreshHistory(){if(!this._hass)return;let e=Date.now();if(e-this._lastHistoryFetch<te)return;this._lastHistoryFetch=e;let t=this._findRow();if(t?.deviceId){try{let n=await this._hass.callWS({type:"marketsentry/history",device_id:t.deviceId});this._history=n?.history??[]}catch{}this._render()}}_render(){if(!this.shadowRoot)return;if(!this._hass||!this._config){this.shadowRoot.innerHTML="";return}let e=this._findRow(),t=f(this._hass);this.shadowRoot.innerHTML=`
      <style>${re}</style>
      <ha-card>
        <div class="content">
          ${e?this._renderBody(e,t):this._renderEmpty(t)}
        </div>
      </ha-card>
    `}_renderEmpty(e){return this._config.entity?`<div class="empty">${u(a(e,"empty_instrument",{entity:this._config.entity}))}</div>`:`
        <div class="empty">
          ${u(a(e,"empty_instrument_no_entity"))}
          <a href="/config/integrations/integration/marketsentry">${u(a(e,"empty_instrument_add_instrument"))}</a>.
        </div>
      `}_renderBody(e,t){return e.kind==="outcome"?this._renderOutcome(e,t):this._renderGeneric(e,t)}_renderOutcome(e,t){let{deltaPp:n}=k(this._history),o=b(e.kind,null,n),i=(n??0)>=0?"positive":"negative",s=v(e),l=a(t,`badge_${s}`),c=G(e.url),d=e.value==null?0:Math.min(100,Math.max(0,e.value));return`
      <div class="title" title="${L(e.name)}">
        ${c?`<a href="${c}" target="_blank" rel="noopener">${u(e.name)}</a>`:u(e.name)}
      </div>
      <div class="chips">
        <span class="badge badge-${V(s)}">${u(l)}</span>
      </div>
      <div class="prob-line">
        <div class="prob-bar"><div class="prob-fill" style="width:${d}%"></div></div>
        <div class="prob-value">
          <span class="value" dir="ltr">${u(h(e.kind,e.value,e.unit))}</span>
          ${o?`<span class="change ${i}" dir="ltr">${u(o)}</span>`:""}
        </div>
      </div>
      <div class="stats">
        <div class="stat"><span class="stat-label">${u(a(t,"stat_volume_24h"))}</span><span class="stat-value" dir="ltr">${C(e.volume24hr)}</span></div>
        <div class="stat"><span class="stat-label">${u(a(t,"stat_liquidity"))}</span><span class="stat-value" dir="ltr">${C(e.liquidity)}</span></div>
      </div>
      <div class="footer">${u(a(t,"footer_ends",{date:w(e.endDate,E[t])}))}</div>
    `}_renderGeneric(e,t){let{changePct:n,deltaPp:o}=k(this._history),i=x(this._history,280,60),s=D(this._history,280,60),l=O(this._history,280,60),c=K(this._history),d=b(e.kind,n,o),g=(o??n??0)>=0?"positive":"negative",_=v(e),y=a(t,`badge_${_}`),N=G(e.url);return`
      <div class="title" title="${L(e.name)}">
        ${N?`<a href="${N}" target="_blank" rel="noopener">${u(e.name)}</a>`:u(e.name)}
      </div>
      <div class="chips">
        ${e.kind==="stock"?`<span class="chip">${u(a(t,`chip_${S(e.marketState)}`))}</span>`:""}
        ${e.kind==="fx"?`<span class="chip">${u(e.source==="boi"||/boi/.test(e.source||"")?a(t,"fx_boi"):a(t,"fx_market"))}</span>`:""}
        ${e.kind!=="stock"?`<span class="badge badge-${V(_)}">${u(y)}</span>`:""}
      </div>
      <div class="big-value">
        <span class="value" dir="ltr">${u(h(e.kind,e.value,e.unit))}</span>
        ${d?`<span class="change ${g}" dir="ltr">${u(d)}</span>`:""}
      </div>
      <div class="big-spark">
        ${i?`<svg viewBox="0 0 280 60" preserveAspectRatio="none">
                ${s?`<path d="${s}" fill="currentColor" fill-opacity="0.12" stroke="none" />`:""}
                <path d="${i}" fill="none" stroke="currentColor" stroke-width="2" />
                ${l?`<circle cx="${l.x.toFixed(1)}" cy="${l.y.toFixed(1)}" r="3" fill="currentColor" />`:""}
              </svg>`:""}
        ${c&&c.max!==c.min?`<div class="spark-range" dir="ltr">
                <span>${u(h(e.kind,c.max,e.unit))}</span>
                <span>${u(h(e.kind,c.min,e.unit))}</span>
              </div>`:""}
      </div>
      ${e.kind==="stock"?`<div class="stats"><div class="stat"><span class="stat-label">${u(a(t,"stat_prev_close"))}</span><span class="stat-value" dir="ltr">${u(h(e.kind,e.previousClose,e.unit))}</span></div></div>`:""}
      ${e.kind==="fx"?`<div class="footer">${u(a(t,"footer_published",{date:w(e.publishedDate,E[t])}))}</div>`:""}
    `}};function u(r){return String(r??"").replace(/[&<>"']/g,e=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[e])}function L(r){return u(r)}function G(r){if(!r)return null;try{let e=new URL(r,window.location.origin);return e.protocol!=="http:"&&e.protocol!=="https:"?null:L(e.href)}catch{return null}}function V(r){return String(r).toLowerCase().replace(/[\s_]+/g,"-")}var re=`
  :host { display: block; }
  ha-card { padding: 16px; }
  .content { display: flex; flex-direction: column; gap: 10px; }
  .empty { color: var(--secondary-text-color); }
  .empty a { color: var(--primary-color); }
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
  .big-spark { position: relative; width: 100%; height: 60px; color: var(--primary-color); }
  .big-spark svg { width: 100%; height: 100%; display: block; }
  .spark-range {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: flex-end;
    padding: 2px 0;
    pointer-events: none;
    font-size: 0.68rem;
    color: var(--secondary-text-color);
  }
  .spark-range span {
    background: var(--card-background-color);
    border-radius: 4px;
    padding: 1px 4px;
  }
  .stats { display: flex; gap: 20px; margin-top: 2px; }
  .stat { display: flex; flex-direction: column; gap: 2px; }
  .stat-label { font-size: 0.72rem; color: var(--secondary-text-color); text-transform: uppercase; }
  .stat-value { font-size: 0.95rem; font-weight: 600; color: var(--primary-text-color); }
  .footer { font-size: 0.8rem; color: var(--secondary-text-color); }
`;customElements.define("marketsentry-instrument-card",R);window.customCards=window.customCards||[];window.customCards.push({type:"marketsentry-instrument-card",name:"MarketSentry Pro (single instrument)",description:"One tracked instrument per card, with a kind-specific detailed view (Polymarket probability bar + stats, stock/FX price + sparkline).",preview:!0});var T=class extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"})}setConfig(e){let t={...e},n=JSON.stringify(t);this._configKey!==n&&(this._config=t,this._configKey=n,this._render())}set hass(e){this._hass=e;let t=m(e),n=JSON.stringify(t.map(o=>[o.entityId,o.name]));this._rowsKey!==n&&(this._rowsKey=n,this._render())}connectedCallback(){this._render()}_emitChange(){this._configKey=JSON.stringify(this._config),this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:!0,composed:!0}))}_render(){if(!this.shadowRoot||!this._config)return;this.shadowRoot.textContent="";let e=document.createElement("style");e.textContent=ne,this.shadowRoot.appendChild(e);let t=document.createElement("div");t.className="editor",t.appendChild(this._buildEntityField()),this.shadowRoot.appendChild(t)}_buildEntityField(){let e=f(this._hass),t=document.createElement("div");t.className="field";let n=document.createElement("label");n.textContent=a(e,"editor_instrument"),t.appendChild(n);let o=this._hass?m(this._hass):[],i=document.createElement("select"),s=document.createElement("option");s.value="",s.textContent=o.length?a(e,"editor_choose"):a(e,"editor_no_instruments"),s.disabled=!0,s.selected=!this._config.entity,i.appendChild(s);for(let l of o){let c=document.createElement("option");c.value=l.entityId,c.textContent=l.name,c.selected=this._config.entity===l.entityId,i.appendChild(c)}return i.addEventListener("change",()=>{this._config={...this._config,entity:i.value},this._emitChange()}),t.appendChild(i),t}},ne=`
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
`;customElements.define("marketsentry-instrument-card-editor",T);function B(r,e){let t=r?.kinds,n=m(e),o=t?n.filter(i=>t.includes(i.kind)):n;return o.length===0?{cards:[{type:"markdown",content:"No MarketSentry Pro instruments are tracked yet. Add one via Settings > Devices & services > MarketSentry Pro > Add instrument."}]}:{cards:[{type:"custom:marketsentry-card",title:r?.title??"Markets",group_by:r?.group_by??"kind",...t?{kinds:t}:{}},...o.map(i=>({type:"custom:marketsentry-instrument-card",entity:i.entityId}))]}}var I=class extends HTMLElement{static async generate(e,t){return B(e,t)}};customElements.define("ll-strategy-view-marketsentry",I);
