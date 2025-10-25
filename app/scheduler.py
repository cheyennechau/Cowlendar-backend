from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select
from datetime import date
from .model import DaySummary, User
from .calendar_client import get_today_events
from .brain import decide_mood_and_message
from .settings import settings, engine

def compute_done(events, now_ts):
    import dateutil.parser
    for e in events:
        e["_done"] = dateutil.parser.isoparse(e["end"]).timestamp() < now_ts
    done = sum(1 for e in events if e["_done"])
    percent = round(100 * done / len(events)) if events else 0
    return percent, events

def run_tick():
    from time import time
    with Session(engine) as s:
        user = s.exec(select(User)).first()
        if not user or not user.google_tokens: return

        events = get_today_events(user.google_tokens)
        percent, events = compute_done(events, time())

        # last 7 day history for mood nuance
        rows = s.exec(select(DaySummary).where(DaySummary.user_id==user.id).order_by(DaySummary.day.desc()).limit(7)).all()
        hist = [r.percent_done for r in rows[::-1]]  # oldest -> newest

        mood, message, _ = decide_mood_and_message(settings.ANTHROPIC_API_KEY, events, hist)

        # upsert today
        today = date.today()
        row = s.exec(select(DaySummary).where(DaySummary.user_id==user.id, DaySummary.day==today)).first()
        if not row:
            row = DaySummary(user_id=user.id, day=today, total_events=len(events),
                             completed_events=sum(1 for e in events if e["_done"]),
                             percent_done=percent, mood=mood, message=message,
                             milk_points=percent // 10)
            s.add(row)
        else:
            row.total_events = len(events)
            row.completed_events = sum(1 for e in events if e["_done"])
            row.percent_done = percent
            row.mood = mood
            row.message = message
            row.milk_points = percent // 10
        s.commit()

def start_scheduler():
    sched = BackgroundScheduler()
    sched.add_job(run_tick, "interval", minutes=5, id="tick", replace_existing=True)
    sched.start()
    return sched
