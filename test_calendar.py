"""
Quick script to test which Google account is connected and list all calendars.
Run this to debug calendar access issues.
"""
from app.model import User
from app.settings import engine
from sqlmodel import Session, select
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def test_calendar_access():
    print("\n" + "="*60)
    print("🔍 TESTING GOOGLE CALENDAR ACCESS")
    print("="*60 + "\n")
    
    with Session(engine) as s:
        user = s.exec(select(User)).first()
        if not user or not user.google_tokens:
            print("❌ No authenticated user found!")
            print("   Run the OAuth flow first: GET /auth/google/start")
            return
        
        print(f"✅ Found user in database: {user.email}")
        print(f"   (Note: This is a placeholder email, not the actual Google account)\n")
        
        # Build calendar service
        tokens = user.google_tokens
        creds = Credentials.from_authorized_user_info(
            tokens,
            ["https://www.googleapis.com/auth/calendar.readonly"]
        )
        cal = build("calendar", "v3", credentials=creds)
        
        # Get actual user info
        print("📧 Fetching actual Google account info...")
        try:
            # Get calendar list to see which account
            calendar_list = cal.calendarList().list().execute()
            
            print(f"\n📅 Found {len(calendar_list.get('items', []))} calendars:\n")
            
            for calendar in calendar_list.get('items', []):
                is_primary = " (PRIMARY)" if calendar.get('primary') else ""
                print(f"   • {calendar.get('summary')}{is_primary}")
                print(f"     ID: {calendar.get('id')}")
                print(f"     Access: {calendar.get('accessRole')}")
                print()
            
            # Try to get events from primary calendar
            print("\n🔍 Fetching events from PRIMARY calendar for today...")
            from datetime import datetime, timedelta
            # Use timezone-aware datetime to match local calendar view
            now = datetime.now().astimezone()
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            
            print(f"   Time range: {start.isoformat()} to {end.isoformat()}")
            
            events_result = cal.events().list(
                calendarId='primary',
                timeMin=start.isoformat(),  # Already has timezone
                timeMax=end.isoformat(),    # Already has timezone
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            print(f"   Found {len(events)} events\n")
            
            if not events:
                print("   ⚠️  No events found for today!")
                print("   This could mean:")
                print("   1. You authenticated with a different Google account")
                print("   2. The events are on a different calendar (not primary)")
                print("   3. The events are all-day events")
            else:
                for event in events:
                    start_time = event['start'].get('dateTime', event['start'].get('date'))
                    print(f"   • {event.get('summary', 'No title')}")
                    print(f"     Start: {start_time}")
                    print(f"     Type: {'Timed' if 'dateTime' in event['start'] else 'All-day'}")
                    print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("="*60 + "\n")

if __name__ == "__main__":
    test_calendar_access()
