DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>myCam - Sovereign Camera Hub</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0b0f19;
            --card-bg: #141d2f;
            --card-border: #1e293b;
            --accent: #6366f1;
            --accent-hover: #4f46e5;
            --accent-glow: rgba(99, 102, 241, 0.3);
            --text: #f8fafc;
            --muted: #94a3b8;
            --emerald: #10b981;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg);
            color: var(--text);
            padding: 2rem;
            min-height: 100vh;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1.25rem;
        }
        h1 { font-size: 1.85rem; font-weight: 700; color: #a5b4fc; display: flex; align-items: center; gap: 0.5rem; }
        .badge {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .actions { margin-bottom: 2rem; display: flex; flex-wrap: wrap; gap: 0.75rem; }
        .btn {
            background: var(--accent);
            color: white;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }
        .btn:hover { background: var(--accent-hover); transform: translateY(-1px); }
        .btn-alt { background: #334155; }
        .btn-alt:hover { background: #475569; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, border-color 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: #4338ca;
        }
        .media-container {
            width: 100%;
            height: 200px;
            background: #000;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            position: relative;
        }
        .media-container img, .media-container video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            cursor: pointer;
        }
        .card-body { padding: 1.2rem; flex: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .card-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.4rem; color: #fff; }
        .card-meta { font-size: 0.8rem; color: var(--muted); margin-bottom: 0.8rem; }
        .training-tag {
            display: inline-block;
            background: rgba(99, 102, 241, 0.2);
            color: #a5b4fc;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            margin-top: 0.4rem;
        }
        /* Modal for full preview */
        .modal {
            display: none;
            position: fixed;
            z-index: 100;
            left: 0; top: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.85);
            align-items: center; justify-content: center;
        }
        .modal-content {
            max-width: 90%;
            max-height: 90%;
            border-radius: 8px;
            box-shadow: 0 0 20px rgba(0,0,0,0.8);
        }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>myCam Sentinel</h1>
            <p style="color: var(--muted); font-size: 0.9rem; margin-top: 0.2rem;">Sovereign Local Video & Event Vault</p>
        </div>
        <div class="badge">● Sentinel Active</div>
    </header>

    <div class="actions">
        <button class="btn" onclick="triggerCapture('adb', 'Ring Doorbell Motion')">Record Edge Stream (15s)</button>
        <button class="btn btn-alt" onclick="triggerCapture('snapshot', 'Desktop Snapshot')">Take Snapshot</button>
        <button class="btn btn-alt" onclick="fetchEvents()">Refresh Feed</button>
    </div>

    <div class="grid" id="eventsGrid">
        <p style="color: var(--muted)">Loading events...</p>
    </div>

    <div class="modal" id="mediaModal" onclick="closeModal()">
        <div id="modalTarget" style="display:flex; justify-content:center; align-items:center; width:100%; height:100%;"></div>
    </div>

    <script>
        async function fetchEvents() {
            try {
                const res = await fetch('/api/events');
                const events = await res.json();
                renderEvents(events);
            } catch (err) {
                console.error("Failed to load events", err);
            }
        }

        function renderEvents(events) {
            const grid = document.getElementById('eventsGrid');
            if (!events || events.length === 0) {
                grid.innerHTML = '<p style="color: var(--muted)">No motion events vaulted yet.</p>';
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
                        <div class="media-container">${mediaHtml}</div>
                        <div class="card-body">
                            <div>
                                <div class="card-title">${escapeHtml(evt.notification_title || 'Motion Alert')}</div>
                                <div class="card-meta">
                                    <span>${new Date(evt.timestamp).toLocaleString()}</span> • 
                                    <span style="color: #38bdf8">${evt.trigger_type}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        async function triggerCapture(mode, title) {
            try {
                await fetch('/trigger', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mode: mode, title: title })
                });
                setTimeout(fetchEvents, 2000);
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

        fetchEvents();
        setInterval(fetchEvents, 5000);
    </script>
</body>
</html>
'''
