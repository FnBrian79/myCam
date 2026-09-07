"""
dashboard.py - Sovereign Camera Sentinel & Omnipresent Hardware Hub
===================================================================
A high-performance dark HUD dashboard displaying:
  - Live Kindle Fire Sentinel & Ring camera streams
  - Enrolled Sovereign Identities & Google Photos reference vectors
  - Connected designated libraries (E:\\takeout, %USERPROFILE%\\Pictures)
  - Architectural Blueprint: Magnetic Wall Charging Plates & Modded Tablets/iPads
  - Interactive training feed & vaulted media playback
"""

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>myCam • Sovereign Sentinel & Omnipresent Home Vault</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #06090e;
            --bg-surface: #0d131f;
            --bg-card: #121a2d;
            --bg-card-hover: #16213a;
            --border: #1e293b;
            --border-glow: #38bdf833;
            --cyan: #38bdf8;
            --indigo: #6366f1;
            --emerald: #10b981;
            --amber: #f59e0b;
            --rose: #f43f5e;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-base);
            color: var(--text);
            padding: 1.75rem 2.25rem;
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 15% 10%, rgba(56, 189, 248, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 85% 85%, rgba(99, 102, 241, 0.05) 0%, transparent 40%);
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2rem;
        }

        .brand-title {
            font-family: 'Outfit', sans-serif;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .brand-sub {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
            font-family: 'JetBrains Mono', monospace;
        }

        .status-pill-row {
            display: flex;
            gap: 0.75rem;
            align-items: center;
        }

        .pill {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.45rem 0.9rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.12);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .pill.dock {
            background: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border-color: rgba(56, 189, 248, 0.3);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: currentColor;
            box-shadow: 0 0 8px currentColor;
            animation: pulse 2s infinite ease-in-out;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
        }

        /* Metrics Bar */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .metric-box {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.1rem 1.4rem;
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            position: relative;
            overflow: hidden;
        }

        .metric-box::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--cyan), transparent);
            opacity: 0.3;
        }

        .metric-label {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-dim);
        }

        .metric-val {
            font-family: 'Outfit', sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            color: #fff;
        }

        .metric-hint {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        /* Controls */
        .actions-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-bottom: 2rem;
            background: var(--bg-surface);
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            align-items: center;
            justify-content: space-between;
        }

        .btn-group {
            display: flex;
            gap: 0.6rem;
            flex-wrap: wrap;
        }

        .btn {
            background: linear-gradient(135deg, var(--indigo) 0%, #4338ca 100%);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.1);
            padding: 0.65rem 1.25rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(99, 102, 241, 0.4);
        }

        .btn-alt {
            background: #1e293b;
            color: var(--text);
            box-shadow: none;
            border: 1px solid #334155;
        }

        .btn-alt:hover {
            background: #334155;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        .btn-emerald {
            background: linear-gradient(135deg, #059669 0%, #047857 100%);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        }

        .btn-emerald:hover {
            box-shadow: 0 6px 18px rgba(16, 185, 129, 0.4);
        }

        /* Section Headings */
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 1.2rem;
            margin-top: 2rem;
        }

        .section-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.25rem;
            font-weight: 700;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Hardware Concept Showcase */
        .hardware-showcase {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }

        .concept-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: all 0.3s ease;
        }

        .concept-card:hover {
            border-color: var(--cyan);
            transform: translateY(-3px);
            box-shadow: 0 12px 28px -5px rgba(56, 189, 248, 0.2);
        }

        .concept-media {
            width: 100%;
            height: 220px;
            background: #000;
            position: relative;
            overflow: hidden;
        }

        .concept-media img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            cursor: pointer;
            transition: transform 0.4s ease;
        }

        .concept-media img:hover {
            transform: scale(1.04);
        }

        .concept-body {
            padding: 1.2rem;
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .concept-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.15rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 0.4rem;
        }

        .concept-desc {
            font-size: 0.85rem;
            color: var(--text-muted);
            line-height: 1.45;
            margin-bottom: 0.85rem;
        }

        .concept-meta-tag {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            color: var(--cyan);
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.25);
            padding: 0.3rem 0.6rem;
            border-radius: 4px;
            display: inline-block;
            align-self: flex-start;
        }

        /* Identities Shelf */
        .identities-shelf {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
            gap: 1rem;
            margin-bottom: 2.5rem;
        }

        .id-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0.85rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            transition: all 0.2s;
            position: relative;
        }

        .id-card:hover {
            transform: translateY(-2px);
            border-color: var(--cyan);
            box-shadow: 0 8px 20px rgba(56, 189, 248, 0.15);
        }

        .id-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--cyan);
            margin-bottom: 0.75rem;
            background: #000;
        }

        .id-name {
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 0.95rem;
            color: #fff;
            margin-bottom: 0.25rem;
        }

        .id-origin {
            font-size: 0.72rem;
            color: var(--text-dim);
            margin-bottom: 0.5rem;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .id-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.68rem;
            background: rgba(56, 189, 248, 0.1);
            color: var(--cyan);
            border: 1px solid rgba(56, 189, 248, 0.25);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }

        /* Event Cards Grid */
        .events-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, border-color 0.2s;
        }

        .card:hover {
            transform: translateY(-2px);
            border-color: var(--indigo);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        }

        .media-box {
            width: 100%;
            height: 220px;
            background: #000;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .media-box img, .media-box video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            cursor: pointer;
        }

        .card-body {
            padding: 1.25rem;
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .card-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.1rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 0.35rem;
        }

        .card-meta {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 0.75rem;
        }

        .card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding-top: 0.75rem;
            margin-top: 0.5rem;
        }

        .source-tag {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.1);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0; top: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.88);
            align-items: center; justify-content: center;
            backdrop-filter: blur(4px);
        }
        .modal-content {
            max-width: 90%;
            max-height: 90%;
            border-radius: 10px;
            box-shadow: 0 0 30px rgba(0,0,0,0.9);
            border: 1px solid rgba(255,255,255,0.1);
        }
    </style>
</head>
<body>
    <header>
        <div>
            <div class="brand-title">
                <span>⚡ myCam Sentinel</span>
            </div>
            <div class="brand-sub">Sovereign Vault • 3-Tier WAL Substrate • RTX 5070 Edge Host</div>
        </div>
        <div class="status-pill-row">
            <div class="pill">
                <div class="pulse-dot"></div>
                <span>Kindle Fire HD 8+ Online</span>
            </div>
            <div class="pill dock">
                <span>⚡ Qi Wireless 100%</span>
            </div>
            <div class="pill" style="background: rgba(99, 102, 241, 0.15); color: #818cf8; border-color: rgba(99, 102, 241, 0.3);">
                <span>5/5 Ring Cams Linked</span>
            </div>
        </div>
    </header>

    <!-- Metrics Bar -->
    <div class="metrics-grid">
        <div class="metric-box">
            <div class="metric-label">Motion Events Vaulted</div>
            <div class="metric-val" id="metricEvents">0</div>
            <div class="metric-hint">SHA-256 Sealed & Encrypted</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Enrolled Identities</div>
            <div class="metric-val" id="metricIdentities">0</div>
            <div class="metric-hint">Google Photos & User Profiles</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Local Feature Vectors</div>
            <div class="metric-val" id="metricVectors">0</div>
            <div class="metric-hint">768-d Ollama nomic-embed</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Connected Libraries</div>
            <div class="metric-val" id="metricSources">Auto</div>
            <div class="metric-hint">E:\\takeout + Designated Pictures</div>
        </div>
    </div>

    <!-- Actions Control Bar -->
    <div class="actions-bar">
        <div class="btn-group">
            <button class="btn btn-emerald" onclick="triggerIngest()">
                <span>📸 Scan & Ingest Photo Libraries</span>
            </button>
            <button class="btn" onclick="triggerCapture('adb', 'Ring Doorbell Motion')">
                <span>🎥 Record Edge Sentinel (15s)</span>
            </button>
            <button class="btn btn-alt" onclick="triggerCapture('snapshot', 'Desktop Snapshot')">
                <span>🖼️ Snapshot Sentinel</span>
            </button>
        </div>
        <div>
            <button class="btn btn-alt" onclick="refreshAll()">
                <span>🔄 Refresh Substrate</span>
            </button>
        </div>
    </div>

    <!-- Hardware Architecture Showcase -->
    <div class="section-header">
        <div class="section-title">
            <span>🏛️ Architectural Blueprint: Magnetic Wall Plates & Omnipresent Home</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--text-dim);">The "Out of Your Hands" Philosophy • Luxury Hardware Mods for Kindle Fires & iPads</div>
    </div>
    
    <div class="hardware-showcase">
        <!-- Card 1: Arrival & Omnipresence -->
        <div class="concept-card">
            <div class="concept-media">
                <img src="/api/media?path=captures/hardware_concept_phone_omnipresent.jpg" alt="Omnipresent Entryway Dock" onclick="openModal(this.src, false)" />
            </div>
            <div class="concept-body">
                <div>
                    <div class="concept-title">1. Arrival: The Omnipresent Hand-off</div>
                    <div class="concept-desc">You walk through the front door and snap your phone magnetically onto the wall plate. It leaves your hands. The house wakes up—ambient displays illuminate, room audio activates, and the compute expands into the home.</div>
                </div>
                <div class="concept-meta-tag">PHASE 1 • ENTRYWAY DECOUPLING</div>
            </div>
        </div>

        <!-- Card 2: 24/7 Sentinel Kiosk Mode -->
        <div class="concept-card">
            <div class="concept-media">
                <img src="/api/media?path=captures/hardware_concept_magnetic_dock.jpg" alt="Mounted Sentinel HUD" onclick="openModal(this.src, false)" />
            </div>
            <div class="concept-body">
                <div>
                    <div class="concept-title">2. Docked: 24/7 Silent Sentinel</div>
                    <div class="concept-desc">Modified recycled Kindle Fires and iPads mount flush to slate wall plates with spring-loaded gold pogo pins or MagSafe coils. Powers via standard low-voltage doorbell wire. 24/7 kiosk running myCam sentinel without draining batteries.</div>
                </div>
                <div class="concept-meta-tag">PHASE 2 • RECYCLED TABLET C2</div>
            </div>
        </div>

        <!-- Card 3: One-Hand Grab & Go -->
        <div class="concept-card">
            <div class="concept-media">
                <img src="/api/media?path=captures/hardware_concept_detachable_dock.jpg" alt="Detachable Magnetic Plate" onclick="openModal(this.src, false)" />
            </div>
            <div class="concept-body">
                <div>
                    <div class="concept-title">3. Instant Detach: Grab-and-Go</div>
                    <div class="concept-desc">Zero friction. Take the tablet off the wall plate in half a second with one hand—no cables, no clips. Utilize it as a handheld sovereign tactical viewer or intercom anywhere, then snap it right back.</div>
                </div>
                <div class="concept-meta-tag">PHASE 3 • DUAL-MODE MOBILITY</div>
            </div>
        </div>
    </div>

    <!-- Enrolled Identities Shelf -->
    <div class="section-header">
        <div class="section-title">
            <span>🧬 Enrolled Identities & Visual Reference Shelf</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--text-dim);" id="identitySubtitle">Auto-harvested from Google Takeout & Designated Libraries</div>
    </div>
    <div class="identities-shelf" id="identitiesShelf">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Scanning enrolled identities...</p>
    </div>

    <!-- Live Sentinel Feed -->
    <div class="section-header">
        <div class="section-title">
            <span>🛡️ Live Vaulted Motion & Sentinel Captures</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--text-dim);">Real-time ADB Push & Ring Capture Ingest</div>
    </div>
    <div class="events-grid" id="eventsGrid">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Loading vaulted captures...</p>
    </div>

    <!-- Media Fullscreen Modal -->
    <div class="modal" id="mediaModal" onclick="closeModal()">
        <div id="modalTarget" style="display:flex; justify-content:center; align-items:center; width:100%; height:100%;"></div>
    </div>

    <script>
        async function fetchEvents() {
            try {
                const res = await fetch('/api/events');
                const events = await res.json();
                renderEvents(events);
                document.getElementById('metricEvents').innerText = events.length;
            } catch (err) {
                console.error("Events fetch error", err);
            }
        }

        async function fetchIdentities() {
            try {
                const res = await fetch('/api/identities');
                const identities = await res.json();
                renderIdentities(identities);
                document.getElementById('metricIdentities').innerText = identities.length;
                const vectorizedCount = identities.filter(i => i.has_vector).length;
                document.getElementById('metricVectors').innerText = vectorizedCount;
            } catch (err) {
                console.error("Identities fetch error", err);
            }
        }

        async function fetchSources() {
            try {
                const res = await fetch('/api/sources');
                const data = await res.json();
                document.getElementById('metricSources').innerText = data.sources ? data.sources.length : 0;
            } catch (err) {
                console.error("Sources fetch error", err);
            }
        }

        function renderIdentities(identities) {
            const shelf = document.getElementById('identitiesShelf');
            if (!identities || identities.length === 0) {
                shelf.innerHTML = '<p style="color: var(--text-muted)">No identities enrolled yet. Click "Scan & Ingest Photo Libraries" above.</p>';
                return;
            }

            shelf.innerHTML = identities.slice(0, 16).map(idItem => {
                const imgUrl = `/api/media?path=${encodeURIComponent(idItem.local_path)}`;
                return `
                    <div class="id-card">
                        <img src="${imgUrl}" class="id-avatar" alt="${escapeHtml(idItem.name)}" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'80\\' height=\\'80\\'><rect fill=\\'%231e293b\\' width=\\'80\\' height=\\'80\\'/><text fill=\\'%2394a3b8\\' font-size=\\'12\\' x=\\'50%\\' y=\\'50%\\' text-anchor=\\'middle\\' dy=\\'.3em\\'>ID PHOTO</text></svg>'" onclick="openModal('${imgUrl}', false)" />
                        <div class="id-name">${escapeHtml(idItem.name)}</div>
                        <div class="id-origin" title="${escapeHtml(idItem.source)}">${escapeHtml(idItem.source)}</div>
                        <div class="id-badge">⚡ 768-d Vector Ready</div>
                    </div>
                `;
            }).join('');
        }

        function renderEvents(events) {
            const grid = document.getElementById('eventsGrid');
            if (!events || events.length === 0) {
                grid.innerHTML = '<p style="color: var(--text-muted)">No motion events vaulted yet.</p>';
                return;
            }

            grid.innerHTML = events.map(evt => {
                const mediaFile = (evt.media && evt.media.length > 0) ? evt.media[0] : null;
                let mediaHtml = '<div style="color: #64748b; font-size: 0.9rem;">No media attached</div>';
                
                if (mediaFile) {
                    const mediaUrl = `/api/media?path=${encodeURIComponent(mediaFile)}`;
                    if (mediaFile.toLowerCase().endsWith('.mp4')) {
                        mediaHtml = `<video src="${mediaUrl}" autoplay loop muted playsinline onclick="openModal('${mediaUrl}', true)"></video>`;
                    } else {
                        mediaHtml = `<img src="${mediaUrl}" alt="Event Media" loading="lazy" onclick="openModal('${mediaUrl}', false)" />`;
                    }
                }

                return `
                    <div class="card">
                        <div class="media-box">${mediaHtml}</div>
                        <div class="card-body">
                            <div>
                                <div class="card-title">${escapeHtml(evt.notification_title || 'Sentinel Alert')}</div>
                                <div class="card-meta">
                                    <span>${new Date(evt.timestamp).toLocaleString()}</span>
                                </div>
                            </div>
                            <div class="card-footer">
                                <span class="source-tag">${escapeHtml(evt.trigger_type || 'edge_ring')}</span>
                                <span style="font-size: 0.75rem; color: var(--emerald);">● Verified Local</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        async function triggerIngest() {
            try {
                const btn = event.currentTarget;
                btn.style.opacity = '0.5';
                btn.innerText = 'Scanning Libraries...';
                await fetch('/api/ingest_photos', { method: 'POST' });
                setTimeout(() => {
                    refreshAll();
                    btn.style.opacity = '1';
                    btn.innerHTML = '<span>📸 Scan & Ingest Photo Libraries</span>';
                }, 3000);
            } catch (err) {
                alert("Ingest trigger error: " + err);
            }
        }

        async function triggerCapture(mode, title) {
            try {
                await fetch('/trigger', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mode: mode, title: title })
                });
                setTimeout(fetchEvents, 2500);
            } catch (err) {
                alert("Trigger error: " + err);
            }
        }

        function openModal(url, isVideo) {
            const modal = document.getElementById('mediaModal');
            const target = document.getElementById('modalTarget');
            if (isVideo) {
                target.innerHTML = `<video class="modal-content" src="${url}" controls autoplay></video>`;
            } else {
                target.innerHTML = `<img class="modal-content" src="${url}" />`;
            }
            modal.style.display = 'flex';
        }

        function closeModal() {
            document.getElementById('mediaModal').style.display = 'none';
            document.getElementById('modalTarget').innerHTML = '';
        }

        function escapeHtml(str) {
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function refreshAll() {
            fetchEvents();
            fetchIdentities();
            fetchSources();
        }

        refreshAll();
        setInterval(fetchEvents, 5000);
        setInterval(fetchIdentities, 10000);
    </script>
</body>
</html>
'''
