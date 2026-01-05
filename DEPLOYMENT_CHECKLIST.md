# PantryBot Open WebUI - Deployment Checklist

## Files to Transfer to Windows

Transfer these files from Mac to `C:\pantrybot\` on Windows:

✅ **Updated Files:**
- `docker-compose.yml` (UPDATED - now includes Open WebUI)
- `.env` (existing, no changes)
- `Dockerfile` (existing, no changes)
- `pantry_bot_mcp.py` (existing, no changes)
- `mcp_http_bridge.py` (existing, no changes)
- `requirements.txt` (existing, no changes)

📝 **Keep for Reference on Mac:**
- `open_webui_pantrybot_function.py` (you'll copy-paste this into Open WebUI browser)
- `OPEN_WEBUI_SETUP.md` (setup guide)
- `pantrybot_cli.py` (old CLI, can archive)

## Pre-Deployment Steps on Windows

```powershell
# 1. Create Open WebUI data directory
mkdir E:\pantrybot\open-webui

# 2. Verify existing directories
dir E:\pantrybot\recipes        # Should exist (recipes)
dir E:\ollama-data              # Should exist (Ollama models)

# 3. Stop existing containers
cd C:\pantrybot
docker-compose down
```

## Deployment Steps

```powershell
# 4. Transfer docker-compose.yml to C:\pantrybot\

# 5. Pull Open WebUI image
docker pull ghcr.io/open-webui/open-webui:main

# 6. Start all services
docker-compose up -d

# 7. Verify all containers running
docker ps

# Should see:
# - ollama (port 11434)
# - pantrybot (port 9999)
# - open-webui (port 3004)
```

## Post-Deployment Verification

```powershell
# 8. Check logs
docker logs open-webui --tail 50
docker logs pantrybot --tail 50
docker logs ollama --tail 50

# 9. Test endpoints from Windows
curl http://localhost:3004       # Should return HTML
curl http://localhost:9999       # Should return PantryBot JSON
curl http://localhost:11434/api/tags  # Should list Ollama models
```

## Access from Mac/Other Devices

```bash
# 10. Test from Mac browser
open http://192.168.0.83:3004

# Or from any device
# Open browser → http://192.168.0.83:3004
```

## Initial Setup in Browser

1. ✅ Create admin account
2. ✅ Verify Ollama connection (Settings → Connections)
3. ✅ Test chat with llama3.1:8b
4. ✅ Install PantryBot function (Admin Panel → Functions)
5. ✅ Test "What's in my pantry?"

## Success Criteria

- [ ] All 3 containers running (`docker ps`)
- [ ] Can access Open WebUI at http://192.168.0.83:3004
- [ ] Can chat with llama3.1:8b model
- [ ] PantryBot function installed and enabled
- [ ] "What's in my pantry?" returns real Grocy data
- [ ] Can save recipes successfully
- [ ] No timeouts or connection errors

## Rollback (if needed)

```powershell
# Stop new setup
docker-compose down

# Restore old docker-compose.yml (without Open WebUI)

# Start old setup
docker-compose up -d

# Use old Mac CLI
./pantrybot_cli.py --server http://192.168.0.83:9999
```

## Expected Timeline

- File transfer: 2 minutes
- Pull Open WebUI image: 3-5 minutes
- Container startup: 1-2 minutes
- Browser setup: 5 minutes
- Function installation: 3 minutes

**Total: ~15 minutes**

## Troubleshooting Quick Reference

**Container won't start:**
```powershell
docker logs open-webui
```

**Can't access from browser:**
```powershell
# Add firewall rule
New-NetFirewallRule -DisplayName "Open WebUI" -Direction Inbound -LocalPort 3004 -Protocol TCP -Action Allow
```

**Function not working:**
- Check PANTRYBOT_URL in function valves: `http://pantrybot:8000`
- Test PantryBot directly: `curl http://localhost:9999/`

## Next Steps After Deployment

1. Create system prompt for PantryBot personality
2. Add family user accounts
3. Test from mobile devices
4. Archive old Mac CLI client
5. Update SMB share if needed (recipes still at E:\pantrybot\recipes)

---

Ready to deploy! Follow OPEN_WEBUI_SETUP.md for detailed instructions.
