"""Background sync to MVP encoding service after 4th student photo upload."""

import os

import httpx

MVP_URL = os.getenv("MVP_URL", "https://mvp.faceattend.app/").rstrip("/")


async def trigger_sync_in_background(token: str) -> None:
    if not MVP_URL:
        print("⚠️  Auto-sync skipped: MVP_URL is not configured.")
        return

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{MVP_URL}/admin/sync-encodings",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                print(f"✅ Auto-sync complete: {resp.status_code}")
            else:
                print(f"⚠️  Auto-sync rejected: HTTP {resp.status_code} — {resp.text[:300]}")
    except httpx.UnsupportedProtocol as e:
        print(f"❌ Auto-sync failed: MVP_URL is invalid — {e!r} (MVP_URL={repr(MVP_URL)})")
    except httpx.ConnectError as e:
        print(f"❌ Auto-sync failed: cannot reach MVP server — {e!r}")
    except httpx.TimeoutException:
        print(f"❌ Auto-sync timed out after 60s (MVP_URL={repr(MVP_URL)})")
    except Exception as e:
        print(f"❌ Auto-sync failed ({type(e).__name__}): {e!r}")
