#!/usr/bin/env python3
"""
CLOUD DEPLOYMENT CHECKLIST - Quick Reference
"""

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║           ATHLETE APP - STREAMLIT CLOUD DEPLOYMENT CHECKLIST               ║
╚════════════════════════════════════════════════════════════════════════════╝

📋 PRE-DEPLOYMENT CHECKS (Local)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Syntax Validation
   python -m py_compile app.py pages/*.py src/**/*.py
   ✅ All files compile without errors

2. Local Test Run
   streamlit run app.py
   ✅ Dashboard loads in < 2 seconds
   ✅ Plan page loads in < 2 seconds
   ✅ Garmin sync completes or times out gracefully (< 20s)
   ✅ No AttributeError or TypeError exceptions

3. Diagnostics
   - Run local: http://localhost:8501/diagnostico_performance
   - Check: Import times < 1s each
   - Check: Query times < 500ms each
   - Check: Database indices present (12+)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 CLOUD CONFIGURATION (.streamlit/config.toml)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Already configured for optimal performance:
   - maxMegabytes = 50 (cache limit)
   - logger.level = "error" (reduce logs)
   - gatherUsageStats = false
   - showErrorDetails = false

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 DEPLOYMENT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Commit all changes
   git add -A
   git commit -m "perf: optimize for Streamlit Cloud - cache, lazy load, timeouts"

2. Push to Streamlit Cloud
   Set deployment trigger or: git push origin main

3. Monitor Cloud App
   - Open https://share.streamlit.io/[your-app]
   - Check: App loads completely (< 10s first time)
   - Run: /diagnostico_performance (check import times)

4. Test Critical Paths
   ✅ Login → Dashboard (should be < 2s)
   ✅ Switch to Plan (should be < 1.5s)
   ✅ Click "Sincronizar Garmin" (should timeout gracefully after 20s)
   ✅ Diario page loads (< 1.5s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ "AttributeError: executemany"
   → FIXED: Changed to execute() loop in db_manager.py

❌ "App hangs for 2+ minutes"
   → FIXED: Added 15-20s timeouts to Garmin API, DB init checks

❌ "Dashboard takes 5+ seconds"
   → FIXED: Added @st.cache_data(ttl=300) to all dashboard functions
   → FIXED: Reduced query LIMIT 1500 → 200

❌ "Plan page takes 4+ seconds"
   → FIXED: Lazy-loaded expensive imports (generar_plan_semana, etc.)

❌ Still slow after deployment?
   1. Run /diagnostico_performance in Cloud
   2. Check: Which import/query is slowest?
   3. Profile: Add st.write(time.time()) markers
   4. Clear: Cache via "Manage app" → "Reboot app"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 EXPECTED METRICS (Cloud)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dashboard load:        1-2 seconds (was 3-4s)
Page switch:           0.5-1.5 seconds (was 2-3s)
Garmin sync timeout:   15-20 seconds max (was infinite)
Memory usage:          < 100MB (cache: 50MB)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Ready to deploy!
""")
