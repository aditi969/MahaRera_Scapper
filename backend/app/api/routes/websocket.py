"""WebSocket router for live scraper progress and streaming execution logs."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database.session import SessionLocal
from app.repositories.scraper_repository import ScraperRepository
from app.services.scraper_service import ScraperService

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/scraper/{job_id}")
async def websocket_scraper_progress(websocket: WebSocket, job_id: str):
    """Real-time bidirectional WebSocket stream for scraping progress and logs."""
    await websocket.accept()

    # Send initial job status from DB
    db = SessionLocal()
    try:
        repo = ScraperRepository(db)
        job = repo.get_job(job_id)
        if job:
            await websocket.send_text(json.dumps({
                "type": "init",
                "job_id": job.job_id,
                "district_name": job.district_name,
                "status": job.status,
                "current_page": job.current_page or job.start_page,
                "start_page": job.start_page,
                "end_page": job.end_page,
                "projects_found": job.projects_found or 0,
                "projects_extracted": job.projects_extracted or 0,
                "projects_failed": job.projects_failed or 0,
                "certificates_extracted": job.certificates_extracted or 0,
                "certificates_failed": job.certificates_failed or 0,
            }))
            # Send recent logs
            recent_logs = repo.get_logs(job_id, limit=50)
            for log in recent_logs:
                await websocket.send_text(json.dumps({
                    "type": "log",
                    "level": log.level,
                    "message": log.message,
                    "timestamp": log.created_at.isoformat(),
                }))
    finally:
        db.close()

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_event(event_dict: Dict[str, Any]):
        loop.call_soon_threadsafe(queue.put_nowait, event_dict)

    service = ScraperService.get_instance()
    service.subscribe(job_id, on_event)

    try:
        while True:
            # Wait for event from queue or receive ping from client
            event = await queue.get()
            await websocket.send_text(json.dumps(event))
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        service.unsubscribe(job_id, on_event)

