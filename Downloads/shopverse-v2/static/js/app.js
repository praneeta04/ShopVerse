/* ═══════════════════════════════════════════════════════════
   SMARTAISLE v2 — Global App JS
   Real Voice AI (multilingual), Geofence, Chat, Navigation
═══════════════════════════════════════════════════════════ */

const DEMO_LAT = 17.4401, DEMO_LNG = 78.4987;
const AMB_LAT  = 17.4156, AMB_LNG  = 78.4347;

let userLat = null, userLng = null;
let chatOpen = false, notifPanelOpen = false, userMenuOpen = false;
let geofenceInterval = null;
let notifications = [];
let chatHistory = [];

// ── Voice state ───────────────────────────────────────────
let recognition = null;
let isListening  = false;
let synth = window.speechSynthesis;
let voiceHistory = [];
let currentVoiceLang = 'en-IN';
const supportedLangs = {
  'en-IN':'English (India)', 'hi-IN':'हिंदी', 'te-IN':'తెలుగు',
  'ta-IN':'தமிழ்', 'kn-IN':'ಕನ್ನಡ', 'ml-IN':'മലയാളം',
  'mr-IN':'मराठी', 'bn-IN':'বাংলা', 'gu-IN':'ગુજરાતી',
  'pa-IN':'ਪੰਜਾਬੀ', 'ur-IN':'اردو', 'fr-FR':'Français',
  'es-ES':'Español', 'ar-SA':'العربية', 'zh-CN':'中文',
  'de-DE':'Deutsch', 'ja-JP':'日本語', 'ko-KR':'한국어'
};

// ══ ON PAGE LOAD ══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  initAuth();
  initGeolocation();
  requestNotificationPermission();
  buildLangSelector();

  document.addEventListener('click', e => {
    if (!e.target.closest('#userDropdown') && !e.target.closest('#userAvatar')) closeUserMenu();
    if (!e.target.closest('#notifPanel') && !e.target.closest('#notifBtn')) closeNotifPanel();
  });
  window.addEventListener('scroll', () => {
    const nav = document.getElementById('navbar');
    if (nav) nav.style.background = window.scrollY > 10 ? 'rgba(5,9,20,0.97)' : 'rgba(5,9,20,0.85)';
  });
  const notifBtn = document.getElementById('notifBtn');
  if (notifBtn) notifBtn.addEventListener('click', e => { e.stopPropagation(); toggleNotifPanel(); });
});

// ══ AUTH ══════════════════════════════════════════════════
function initAuth() {
  const user = JSON.parse(localStorage.getItem('smartaisle_user') || 'null');
  const loginBtn  = document.getElementById('loginBtn');
  const avatarEl  = document.getElementById('userAvatar');
  const avatarIni = document.getElementById('avatarInitial');
  if (user) {
    if (loginBtn)  loginBtn.style.display  = 'none';
    if (avatarEl)  avatarEl.style.display  = 'flex';
    if (avatarIni) avatarIni.textContent   = (user.name||'U')[0].toUpperCase();
    if (document.getElementById('dropName'))  document.getElementById('dropName').textContent  = user.name;
    if (document.getElementById('dropEmail')) document.getElementById('dropEmail').textContent = user.email;
    if (document.getElementById('dropAvatar'))document.getElementById('dropAvatar').textContent= (user.name||'U')[0].toUpperCase();
  } else {
    if (avatarEl) avatarEl.style.display = 'none';
    if (loginBtn) loginBtn.style.display = 'flex';
  }
}
function toggleUserMenu() {
  userMenuOpen = !userMenuOpen;
  const d = document.getElementById('userDropdown');
  if (d) d.classList.toggle('open', userMenuOpen);
  if (notifPanelOpen) closeNotifPanel();
}
function closeUserMenu() { userMenuOpen = false; const d=document.getElementById('userDropdown'); if(d)d.classList.remove('open'); }
function logout() {
  localStorage.removeItem('smartaisle_user');
  sessionStorage.removeItem('userLat'); sessionStorage.removeItem('userLng');
  window.location.href = '/login';
}

// ══ GEOLOCATION ══════════════════════════════════════════
function initGeolocation() {
  const sLat = sessionStorage.getItem('userLat');
  const sLng = sessionStorage.getItem('userLng');
  if (sLat && sLng) { userLat=parseFloat(sLat); userLng=parseFloat(sLng); startGeofenceMonitoring(); return; }
  requestLocationAccess();
}

function requestLocationAccess() {
  if (!navigator.geolocation) {
    alert('Geolocation is not supported by your browser.');
    return;
  }
  navigator.geolocation.getCurrentPosition(
    pos => {
      userLat = pos.coords.latitude; userLng = pos.coords.longitude;
      sessionStorage.setItem('userLat', userLat); sessionStorage.setItem('userLng', userLng);
      startGeofenceMonitoring();
      navigator.geolocation.watchPosition(p => {
        userLat=p.coords.latitude; userLng=p.coords.longitude;
        sessionStorage.setItem('userLat',userLat); sessionStorage.setItem('userLng',userLng);
      }, null, {enableHighAccuracy:true,maximumAge:5000});
    },
    err => {
      userLat=DEMO_LAT; userLng=DEMO_LNG; startGeofenceMonitoring();
      if (err.code===1) alert('Location permission denied. Please enable location access in your browser settings to use location-based features.');
    },
    {enableHighAccuracy:true,timeout:10000}
  );
}

// ══ GEOFENCE MONITORING ══════════════════════════════════
const triggeredStores = new Set();
function startGeofenceMonitoring() {
  if (geofenceInterval) clearInterval(geofenceInterval);
  checkGeofenceStatus();
  geofenceInterval = setInterval(checkGeofenceStatus, 30000);
}
async function checkGeofenceStatus() {
  if (!userLat||!userLng) return;
  try {
    const res  = await fetch('/api/geofence/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:userLat,lng:userLng})});
    const data = await res.json();
    if (data.success && data.triggered.length) {
      for (const t of data.triggered) {
        if (!triggeredStores.has(t.store_id)) {
          triggeredStores.add(t.store_id);
          onGeofenceTriggered(t);
          setTimeout(()=>triggeredStores.delete(t.store_id), 5*60*1000);
        }
      }
    }
  } catch(e){}
}
function onGeofenceTriggered(trigger) {
  showGeofenceAlert(trigger.store_name, trigger.notification_body);
  if (Notification.permission==='granted') {
    const n = new Notification(trigger.notification_title,{body:trigger.notification_body,tag:`geo-${trigger.store_id}`,requireInteraction:true});
    n.onclick = ()=>{ window.focus(); window.location.href='/offers'; };
  }
  addNotification(trigger.notification_title, trigger.notification_body);
  if (trigger.offers&&trigger.offers.length)
    setTimeout(()=>addNotification('🏷️ New Offer!',`${trigger.offers[0].title}: ${trigger.offers[0].description}`),2000);
}
function showGeofenceAlert(storeName,message) {
  const a=document.getElementById('geofenceAlert');
  const t=document.getElementById('gaTitle');
  const m=document.getElementById('gaMsg');
  if (!a) return;
  if (t) t.textContent=`📍 You're near ${storeName}!`;
  if (m) m.textContent=message;
  a.classList.add('show');
  setTimeout(()=>closeGeofenceAlert(), 8000);
}
function closeGeofenceAlert() { const a=document.getElementById('geofenceAlert'); if(a)a.classList.remove('show'); }

// ══ NOTIFICATIONS ════════════════════════════════════════
function requestNotificationPermission() {
  if (typeof Notification!=='undefined'&&Notification.permission==='default')
    setTimeout(()=>Notification.requestPermission(),3000);
}
function addNotification(title,message) {
  notifications.unshift({title,message,time:new Date()});
  const badge=document.getElementById('notifBadge');
  if (badge){badge.style.display='flex';badge.textContent=Math.min(notifications.length,9);}
  const list=document.getElementById('notifList');
  if (list) renderNotifList(list);
}
function renderNotifList(list) {
  if (!notifications.length){list.innerHTML='<div class="notif-empty">No notifications yet</div>';return;}
  list.innerHTML=notifications.slice(0,10).map(n=>`<div class="notif-item"><div class="notif-item-title">${n.title}</div><div class="notif-item-msg">${n.message}</div></div>`).join('');
}
function clearNotifications() {
  notifications=[];
  const badge=document.getElementById('notifBadge'); if(badge)badge.style.display='none';
  const list=document.getElementById('notifList');  if(list)list.innerHTML='<div class="notif-empty">No notifications yet</div>';
}
function toggleNotifPanel() {
  notifPanelOpen=!notifPanelOpen;
  const p=document.getElementById('notifPanel'); if(p)p.classList.toggle('open',notifPanelOpen);
  const l=document.getElementById('notifList');  if(l)renderNotifList(l);
  if (userMenuOpen) closeUserMenu();
}
function closeNotifPanel(){notifPanelOpen=false;const p=document.getElementById('notifPanel');if(p)p.classList.remove('open');}

// ══ AI CHAT (Real LLM) ════════════════════════════════════
function toggleChat() {
  chatOpen=!chatOpen;
  const w=document.getElementById('chatWidget'); if(w)w.classList.toggle('open',chatOpen);
  if (chatOpen) setTimeout(()=>{const i=document.getElementById('chatInput');if(i)i.focus();},200);
}
function handleChatKey(e){if(e.key==='Enter')sendChatMessage();}

async function sendChatMessage() {
  const input=document.getElementById('chatInput');
  const query=input?input.value.trim():'';
  if (!query) return;
  appendChatMessage(query,'user');
  if (input) input.value='';
  chatHistory.push({role:'user',content:query});
  const tid='typing-'+Date.now();
  appendTypingIndicator(tid);
  try {
    const res=await fetch('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({query,lat:userLat||DEMO_LAT,lng:userLng||DEMO_LNG,history:chatHistory})});
    const data=await res.json();
    removeTypingIndicator(tid);
    if (data.success) {
      chatHistory.push({role:'assistant',content:data.response});
      if (chatHistory.length>20) chatHistory=chatHistory.slice(-20);
      let content=`<p>${data.response.replace(/\n/g,'<br>')}</p>`;
      if (data.suggestions&&data.suggestions.length)
        content+=`<div class="quick-replies">${data.suggestions.slice(0,4).map(s=>`<button onclick="sendQuickReply('${s.replace(/'/g,'')}')">${s}</button>`).join('')}</div>`;
      if (data.stores&&data.stores.length) {
        const si={bakery:'🥐',cafe:'☕',supermarket:'🛒',restaurant:'🍛',convenience_store:'🏪',fashion:'👗',beauty:'💄',entertainment:'🎬',electronics:'📱',lifestyle:'🏠'};
        content+=`<div class="quick-replies">${data.stores.slice(0,3).map(s=>`<button onclick="location.href='/store/${s.id}'">${si[s.category]||'🏬'} ${s.name}</button>`).join('')}</div>`;
      }
      appendChatHTML(content,'ai');
      if (data.action) setTimeout(()=>handleAIAction(data.action),800);
    }
  } catch(err) {
    removeTypingIndicator(tid);
    appendChatMessage('Connection issue. Please try again.','ai');
  }
}
function handleAIAction(action) {
  if (!action) return;
  if (action.type==='navigate'&&action.url) {appendChatHTML(`<p>🚀 Navigating...</p>`,'ai'); setTimeout(()=>window.location.href=action.url,800);}
  else if (action.type==='show_store'&&action.store_id) {appendChatHTML(`<p>🏬 Opening store...</p>`,'ai'); setTimeout(()=>window.location.href=`/store/${action.store_id}`,800);}
  else if (action.type==='show_offers') {appendChatHTML(`<p>🏷️ Opening offers...</p>`,'ai'); setTimeout(()=>window.location.href='/offers',800);}
}
function sendQuickReply(text){const i=document.getElementById('chatInput');if(i)i.value=text;sendChatMessage();}
function appendChatMessage(text,role,id=null){
  const m=document.getElementById('chatMessages'); if(!m)return;
  const d=document.createElement('div'); d.className=`chat-msg ${role==='user'?'user-msg':'ai-msg'}`;
  d.innerHTML=`<div class="msg-avatar"><i class="fas fa-${role==='user'?'user':'robot'}"></i></div><div class="msg-content"><p ${id?`id="${id}"`:''}>${text}</p></div>`;
  m.appendChild(d); m.scrollTop=m.scrollHeight;
}
function appendChatHTML(html,role){
  const m=document.getElementById('chatMessages'); if(!m)return;
  const d=document.createElement('div'); d.className=`chat-msg ${role==='user'?'user-msg':'ai-msg'}`;
  d.innerHTML=`<div class="msg-avatar"><i class="fas fa-robot"></i></div><div class="msg-content">${html}</div>`;
  m.appendChild(d); m.scrollTop=m.scrollHeight;
}
function appendTypingIndicator(id){
  const m=document.getElementById('chatMessages'); if(!m)return;
  const d=document.createElement('div'); d.className='chat-msg ai-msg'; d.id=`wrap-${id}`;
  d.innerHTML=`<div class="msg-avatar"><i class="fas fa-robot"></i></div><div class="msg-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div>`;
  m.appendChild(d); m.scrollTop=m.scrollHeight;
}
function removeTypingIndicator(id){const e=document.getElementById(`wrap-${id}`);if(e)e.remove();}

// ══ LANGUAGE SELECTOR ════════════════════════════════════
function buildLangSelector() {
  const sel = document.getElementById('voiceLangSelect');
  if (!sel) return;
  Object.entries(supportedLangs).forEach(([code,name]) => {
    const opt = document.createElement('option');
    opt.value=code; opt.textContent=name;
    if (code===currentVoiceLang) opt.selected=true;
    sel.appendChild(opt);
  });
  sel.addEventListener('change', e => { currentVoiceLang=e.target.value; });
}

// ══ VOICE ASSISTANT (REAL — Multilingual) ════════════════
function openVoiceAssistant(){document.getElementById('voiceModal').classList.add('open');}
function closeVoiceAssistant(){document.getElementById('voiceModal').classList.remove('open');if(isListening)stopListening();}
function startVoiceChat(){openVoiceAssistant();setTimeout(()=>startListening(),300);}

function toggleVoiceListening(){if(isListening)stopListening();else startListening();}

function startListening(){
  const SpeechRecognition = window.SpeechRecognition||window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    setVoiceStatus('❌ Speech recognition not supported. Use Chrome or Edge.');
    return;
  }
  recognition = new SpeechRecognition();
  recognition.lang = currentVoiceLang;
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    isListening = true;
    setVoiceOrb('listening');
    setVoiceStatus(`🎙️ Listening in ${supportedLangs[currentVoiceLang]}...`);
    setVoiceWaves(true);
    setVoiceMicBtn(true);
    document.getElementById('voiceTranscript').textContent='';
  };
  recognition.onresult = event => {
    let interim='', final='';
    for (let i=event.resultIndex;i<event.results.length;i++) {
      const t=event.results[i][0].transcript;
      if (event.results[i].isFinal) final+=t; else interim+=t;
    }
    document.getElementById('voiceTranscript').textContent=final||interim;
    if (final) { stopListening(); processVoiceCommand(final.trim()); }
  };
  recognition.onerror = event => {
    stopListening();
    if (event.error==='no-speech') setVoiceStatus('No speech detected. Tap again.');
    else setVoiceStatus(`Error: ${event.error}. Tap to retry.`);
  };
  recognition.onend = ()=>{ if(isListening)stopListening(); };
  recognition.start();
}

function stopListening(){
  isListening=false;
  if(recognition){try{recognition.stop();}catch(e){}}
  setVoiceOrb('idle');
  setVoiceWaves(false);
  setVoiceMicBtn(false);
}

// ══ VOICE COMMAND PROCESSOR — executes real actions ══════
async function processVoiceCommand(text) {
  if (!text) { setVoiceStatus('Tap the mic to start'); return; }
  setVoiceOrb('processing');
  setVoiceStatus('🤔 Processing...');
  addVoiceHistoryItem(text,'user');

  // ── Local intent detection FIRST (fast execution) ──
  const tl = text.toLowerCase();
  let localHandled = false;

  // Navigation commands
  if (/\b(open|go to|navigate|show)\b.*(map|explore)/i.test(text)) {
    localHandled = true;
    speakAndAct('Opening the map now!', () => window.location.href='/map');
  } else if (/\b(open|go to|show)\b.*(offer|deal|discount)/i.test(text)) {
    localHandled = true;
    speakAndAct('Opening offers page!', () => window.location.href='/offers');
  } else if (/\b(open|go to|show)\b.*(dashboard|hub|my hub)/i.test(text)) {
    localHandled = true;
    speakAndAct('Opening your dashboard!', () => window.location.href='/dashboard');
  } else if (/\b(open|go to|show)\b.*(retailer|store manager|analytics)/i.test(text)) {
    localHandled = true;
    speakAndAct('Opening retailer dashboard!', () => window.location.href='/retailer');
  } else if (/\b(open|go to|show)\b.*(billing|checkout|cart|payment)/i.test(text)) {
    localHandled = true;
    speakAndAct('Opening billing and checkout!', () => window.location.href='/billing');
  } else if (/\b(open|go to|show)\b.*(home|main|start)/i.test(text)) {
    localHandled = true;
    speakAndAct('Going to home page!', () => window.location.href='/');
  } else if (/\b(login|sign in|logout|sign out)/i.test(text)) {
    if (/logout|sign out/i.test(text)) {
      localHandled = true;
      speakAndAct('Signing you out!', () => logout());
    } else {
      localHandled = true;
      speakAndAct('Opening login page!', () => window.location.href='/login');
    }
  }
  // Map-specific: search for a place
  else if (/\b(find|search|show|where is|locate|take me to)\b.*(mall|store|restaurant|cafe|shop|market|cinema|movie|fashion|beauty|apple|zara|starbucks)/i.test(text)) {
    // Extract the query and redirect to map with search
    const query = text.replace(/\b(find|search|show|where is|locate|take me to)\b/gi,'').trim();
    localHandled = true;
    speakAndAct(`Searching for ${query} on the map!`, () => {
      sessionStorage.setItem('mapSearch', query);
      window.location.href='/map';
    });
  }
  // AMB Mall
  else if (/amb\s*mall/i.test(text)) {
    localHandled = true;
    speakAndAct('Taking you to AMB Mall!', () => {
      sessionStorage.setItem('mapSearch', 'AMB Mall');
      window.location.href='/map';
    });
  }

  if (localHandled) return;

  // ── Send to Claude AI for complex queries ──
  try {
    const res = await fetch('/api/ai/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({query:text, lat:userLat||DEMO_LAT, lng:userLng||DEMO_LNG, history:voiceHistory, lang:currentVoiceLang})
    });
    const data = await res.json();
    if (data.success) {
      const aiText = data.response;
      voiceHistory.push({role:'user',content:text});
      voiceHistory.push({role:'assistant',content:aiText});
      if (voiceHistory.length>12) voiceHistory=voiceHistory.slice(-12);
      addVoiceHistoryItem(aiText,'ai');
      document.getElementById('voiceTranscript').textContent=aiText;
      speakText(aiText, () => {
        setVoiceOrb('idle');
        setVoiceStatus('Tap the mic to ask again');
        if (data.action) setTimeout(()=>executeVoiceAction(data.action),600);
      });
    }
  } catch(err) {
    setVoiceOrb('idle');
    setVoiceStatus('Connection error. Tap to retry.');
  }
}

function speakAndAct(speech, action) {
  addVoiceHistoryItem(speech,'ai');
  document.getElementById('voiceTranscript').textContent=speech;
  setVoiceOrb('speaking');
  setVoiceStatus('🔊 Speaking...');
  speakText(speech, ()=>{
    setVoiceOrb('idle');
    setVoiceStatus('Executing...');
    setTimeout(action, 400);
  });
}

function executeVoiceAction(action){
  if (!action) return;
  if (action.type==='navigate'&&action.url) setTimeout(()=>window.location.href=action.url,600);
  else if (action.type==='show_store'&&action.store_id) setTimeout(()=>window.location.href=`/store/${action.store_id}`,600);
  else if (action.type==='show_offers') setTimeout(()=>window.location.href='/offers',600);
}

function speakText(text, onEnd) {
  if (!synth) { if(onEnd)onEnd(); return; }
  synth.cancel();
  const clean = text.replace(/[\u{1F300}-\u{1FFFF}]/gu,'').replace(/[*_~`]/g,'').substring(0,400);
  const utt = new SpeechSynthesisUtterance(clean);
  // Use the selected voice language
  utt.lang = currentVoiceLang;
  utt.rate = 1.0; utt.pitch = 1.0; utt.volume = 1.0;
  const voices = synth.getVoices();
  const preferred = voices.find(v=>v.lang===currentVoiceLang) ||
                    voices.find(v=>v.lang.startsWith(currentVoiceLang.split('-')[0]+'_')) ||
                    voices.find(v=>v.lang.startsWith(currentVoiceLang.split('-')[0])) ||
                    voices.find(v=>v.lang.startsWith('en'));
  if (preferred) utt.voice = preferred;
  utt.onend  = ()=>{ if(onEnd)onEnd(); };
  utt.onerror= ()=>{ if(onEnd)onEnd(); };
  synth.speak(utt);
}

function setVoiceOrb(state){
  const orb=document.getElementById('voiceOrb');
  const icon=document.getElementById('voiceOrbIcon');
  if(!orb)return;
  orb.className=`voice-orb${state!=='idle'?' '+state:''}`;
  if(icon) icon.className = state==='listening'?'fas fa-microphone':state==='speaking'?'fas fa-volume-up':state==='processing'?'fas fa-circle-notch fa-spin':'fas fa-microphone';
}
function setVoiceStatus(msg){const e=document.getElementById('voiceStatus');if(e)e.textContent=msg;}
function setVoiceWaves(active){const e=document.getElementById('voiceWaves');if(e)e.className=`voice-waves${active?'':' silent'}`;}
function setVoiceMicBtn(listening){
  const btn=document.getElementById('voiceMicBtn');
  const icon=document.getElementById('voiceMicIcon');
  const text=document.getElementById('voiceMicText');
  if(!btn)return;
  btn.style.background=listening?'linear-gradient(135deg,#ef4444,#dc2626)':'linear-gradient(135deg,var(--accent),var(--accent2))';
  if(icon)icon.className=listening?'fas fa-stop':'fas fa-microphone';
  if(text)text.textContent=listening?'Stop Listening':'Start Listening';
}
function addVoiceHistoryItem(text,role){
  const h=document.getElementById('voiceHistory'); if(!h)return;
  const d=document.createElement('div'); d.className=`voice-history-item ${role}`;
  d.textContent=`${role==='user'?'🎙️ You: ':'🤖 AI: '}${text.substring(0,120)}${text.length>120?'...':''}`;
  h.insertBefore(d,h.firstChild);
  while(h.children.length>4)h.removeChild(h.lastChild);
}

// ══ MOBILE NAV ════════════════════════════════════════════
function toggleMobileNav(){const l=document.getElementById('navLinks');if(l)l.classList.toggle('open');}

// ══ DYNAMIC CSS INJECTIONS ════════════════════════════════
const extraCSS = document.createElement('style');
extraCSS.textContent=`
.typing-indicator{display:flex;gap:4px;padding:8px 0}
.typing-indicator span{width:8px;height:8px;border-radius:50%;background:var(--text-3);animation:typingDot 1.2s ease-in-out infinite}
.typing-indicator span:nth-child(2){animation-delay:.2s}
.typing-indicator span:nth-child(3){animation-delay:.4s}
@keyframes typingDot{0%,80%,100%{transform:scale(.8);opacity:.5}40%{transform:scale(1.2);opacity:1}}
.chat-voice-btn{width:36px;height:36px;border-radius:50%;border:none;background:rgba(99,102,241,0.15);color:var(--accent);font-size:14px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .2s;flex-shrink:0}
.chat-voice-btn:hover{background:rgba(99,102,241,0.3)}
`;
document.head.appendChild(extraCSS);


// ── SHOPVERSE ADDITIONS ───────────────────────────────────

// Initialize Socket.IO for real-time updates
let shopSocket = null;
function initSocketIO() {
  if (typeof io === 'undefined') return;
  const user = JSON.parse(localStorage.getItem('smartaisle_user') || 'null');
  if (!user) return;
  shopSocket = io();
  shopSocket.emit('join', {room: user.id});
  shopSocket.on('new_message', (msg) => {
    updateMsgBadgeGlobal();
    addNotification('💬 New Message', msg.message.substring(0, 60) + '...');
  });
  shopSocket.on('order_update', (data) => {
    addNotification('📦 Order Update', data.message);
  });
  shopSocket.on('new_order', (order) => {
    if (user.role === 'retailer') {
      addNotification('🛒 New Order!', `Order ${order.id} — ₹${order.total}`);
    }
  });
  shopSocket.on('offer_toggled', (data) => {
    // Refresh offers on page if visible
    if (typeof loadAllOffers === 'function') loadAllOffers();
  });
}

async function updateMsgBadgeGlobal() {
  const user = JSON.parse(localStorage.getItem('smartaisle_user') || 'null');
  if (!user) return;
  try {
    const res = await fetch(`/api/messages/${user.id}`);
    const data = await res.json();
    const unread = (data.messages || []).filter(m => m.receiver === user.id && !m.read).length;
    const badge = document.getElementById('msgNavBadge');
    if (badge) {
      badge.style.display = unread ? 'inline-flex' : 'none';
      badge.textContent = unread > 9 ? '9+' : unread;
    }
  } catch(e) {}
}

// Load SocketIO dynamically if needed
if (typeof io === 'undefined') {
  const sc = document.createElement('script');
  sc.src = 'https://cdn.socket.io/4.7.2/socket.io.min.js';
  sc.onload = initSocketIO;
  document.head.appendChild(sc);
} else {
  document.addEventListener('DOMContentLoaded', initSocketIO);
}

// Auto-update message badge every 30 seconds
setInterval(updateMsgBadgeGlobal, 30000);
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(updateMsgBadgeGlobal, 2000);
});

// Show toast helper (global)
function showToast(msg, type = 'info') {
  const existing = document.querySelector('.toast-notification');
  if (existing) existing.remove();
  const t = document.createElement('div');
  t.className = 'toast-notification';
  const colors = {info: '', success: 'border-color:var(--green);', error: 'border-color:var(--red);'};
  t.style.cssText = colors[type] || '';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.classList.add('show'), 100);
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3500);
}
window.showToast = showToast;
