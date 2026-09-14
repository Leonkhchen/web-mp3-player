# Web MP3 Player Cloudflare Migration — Project Compact

## Project
- Name: Web MP3 Player Cloudflare Migration
- Repository: `Leonkhchen/web-mp3-player`
- Type: migration
- Status: migration
- Priority: P2
- Primary Agent: OpenCode
- Review Agent: ChatGPT

## Current Milestone
- Milestone: Local-file playback first
- Goal: Deliver a browser-first local MP3 playback version that does not depend on a server-side Python runtime; Google Drive integration remains phase 2.
- Progress: 15%

## Current State
- Default branch: `main`
- Existing implementation is Python-based and includes `app.py`, templates and Docker deployment support.
- Existing architecture is not a direct Cloudflare Workers fit if it depends on a persistent Python web server.
- Cloudflare migration should prioritize moving playback and playlist behavior into the browser.
- Active branch: none recorded
- Active PR: none recorded

## Completed
- Existing repository identified and added to LeonBoard.
- Product direction set: local-file playback first; Google Drive integration second.

## Test / Validation Evidence
- Repository structure inspected for migration planning.
- No Cloudflare preview validation has been recorded yet.

## Known Issues
- Browser file access/security constraints differ from the current server model.
- Persistent access to user-selected local files may require browser capabilities such as File System Access where available, with graceful fallback for iOS/Safari.

## Blockers
- None for the local-playback prototype.

## Architecture / Scope Decisions
- Phase 1 should minimize backend dependencies and keep audio files local to the user's device/browser where possible.
- Google Drive OAuth/API integration is explicitly deferred to phase 2.
- Avoid carrying the existing Python server to Cloudflare merely to preserve implementation shape; migrate behavior, not unnecessary runtime dependencies.

## Next Action
- Implement or prototype a static/browser local-file player and verify iPhone Safari and desktop behavior before introducing cloud storage integration.

## Recommended Next Agent
- OpenCode for browser-first implementation; ChatGPT for browser capability/fallback review.

## Handoff
- Last updated: 2026-09-14
- Updated by: ChatGPT
- Summary: Migration state recorded. Phase 1 is local playback, not Google Drive and not a Python-runtime lift-and-shift.
