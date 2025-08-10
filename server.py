from typing import List, Dict, Any, Optional
from fastmcp import FastMCP, Context
import requests
from dateutil import parser
import httpx
import pytz
from msgraph import GraphServiceClient
from msgraph.generated.models.event import Event
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.location import Location
from msgraph.generated.models.attendee import Attendee
from msgraph.generated.models.email_address import EmailAddress
from azure.identity import ClientSecretCredential
import os
import traceback
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr
load_dotenv()

mcp = FastMCP("meetings_scheduler", stateless_http=True)

credential = ClientSecretCredential(
    tenant_id=os.getenv("MS_TENANT_ID"),
    client_id=os.getenv("MS_CLIENT_ID"),
    client_secret=os.getenv("MS_CLIENT_SECRET")
)
scopes = ["https://graph.microsoft.com/.default"]
graph_client = GraphServiceClient(credential, scopes)
from pydantic import BaseModel, EmailStr

class AttendeeModel(BaseModel):
    email: EmailStr
    name: str
@mcp.tool(
    name="schedule_teams_meeting",
    description=(
        "Schedule a Microsoft Teams meeting by specifying the subject, start/end times (ISO 8601 UTC), "
        "meeting body, and a list of required attendees. "
        "Each attendee must be an object with 'email' (valid email) and 'name' (string)."
    )
)
async def schedule_teams_meeting(
    start_time: str,
    end_time: str,
    subject: str,
    body: str,
    required_attendees: List[AttendeeModel],
    ctx: Context = None
) -> Dict[str, str]:
    """
    Schedule a Microsoft Teams meeting using Microsoft Graph API.

    Parameters:
    - start_time (str): Meeting start datetime in ISO 8601 format (UTC), e.g. "2025-08-15T15:00:00Z".
    - end_time (str): Meeting end datetime in ISO 8601 format (UTC).
    - subject (str): Subject/title of the meeting.
    - body (str): HTML or plain text content for the meeting description.
    - required_attendees (List[AttendeeModel]): List of required attendees.
    - ctx (Context, optional): MCP context for logging.

    Returns:
    Dict[str, str]: Dictionary containing:
        - "event_id": The Microsoft Graph event ID of the scheduled meeting.
        - "join_url": The Microsoft Teams meeting join URL.

    Raises:
    - Exception on failure, with error message logged to MCP context.
    """
    await ctx.info(f"Scheduling meeting: subject={subject}, start={start_time}, end={end_time}")
    try:
        attendee_objects = [
            Attendee(
                email_address=EmailAddress(address=person.email, name=person.name),
                type="required"
            )
            for person in required_attendees
        ]

        event = Event(
            subject=subject,
            body=ItemBody(content_type="HTML", content=body),
            start=DateTimeTimeZone(date_time=start_time, time_zone="UTC"),
            end=DateTimeTimeZone(date_time=end_time, time_zone="UTC"),
            location=Location(display_name="Microsoft Teams Meeting"),
            attendees=attendee_objects,
            is_online_meeting=True,
            online_meeting_provider="teamsForBusiness"
        )

        result = await graph_client.users.by_user_id(os.getenv("MS_USER_ID")).events.post(event)
        join_url = result.online_meeting.join_url
        await ctx.info(f"Meeting scheduled successfully with event ID {result.id} and join URL {join_url}")
        return {"event_id": result.id, "join_url": join_url}

    except Exception as e:
        await ctx.error(f"Error scheduling interview: {str(e)}\n{traceback.format_exc()}")
        return {"error": f"Error scheduling interview: {str(e)}"}

@mcp.tool(name="reschedule_teams_meeting", description="Reschedule an existing interview in Microsoft Teams")
async def reschedule_teams_meeting(
    event_id: str,
    start_time: str,
    end_time: str,
    ctx: Context = None
) -> Dict[str, str]:
    await ctx.info(f"Rescheduling meeting: event_id={event_id}, new_start={start_time}, new_end={end_time}")
    try:
        update = Event(
            start=DateTimeTimeZone(date_time=start_time, time_zone="UTC"),
            end=DateTimeTimeZone(date_time=end_time, time_zone="UTC")
        )
        await graph_client.users.by_user_id(os.getenv("MS_USER_ID")).events.by_event_id(event_id).patch(update)
        await ctx.info(f"Meeting {event_id} rescheduled successfully")
        return {"event_id": event_id, "join_url": ""}

    except Exception as e:
        await ctx.error(f"Error rescheduling interview: {str(e)}\n{traceback.format_exc()}")
        return {"error": f"Error rescheduling interview: {str(e)}"}


@mcp.tool(name="cancel_teams_meeting", description="Cancel an interview in Microsoft Teams")
async def cancel_teams_meeting(
    event_id: str,
    ctx: Context = None
) -> Dict[str, str]:
    await ctx.info(f"Cancelling meeting: event_id={event_id}")
    try:
        await graph_client.users.by_user_id(os.getenv("MS_USER_ID")).events.by_event_id(event_id).delete()
        await ctx.info(f"Meeting {event_id} cancelled successfully")
        return {"message": f"Interview '{event_id}' canceled in Teams."}

    except Exception as e:
        await ctx.error(f"Error canceling interview: {str(e)}\n{traceback.format_exc()}")
        return {"error": f"Error canceling interview: {str(e)}"}


def get_access_token_sync():
    token_url = f"https://login.microsoftonline.com/{os.getenv('MS_TENANT_ID')}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("MS_CLIENT_ID"),
        "client_secret": os.getenv("MS_CLIENT_SECRET"),
        "scope": "https://graph.microsoft.com/.default"
    }
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Error getting token: {response.json()}")


@mcp.tool(
    name="list_team_calendar_events",
    description="List calendar events for team members between specified dates and times with timezone support"
)
async def list_team_calendar_events(
    emails: List[str],
    start_date: str,
    end_date: Optional[str] = None,
    start_time: Optional[str] = "00:00",
    end_time: Optional[str] = "23:59",
    time_zone: Optional[str] = "UTC",
    ctx: Context = None
) -> Dict[str, Any]:
    await ctx.info(f"Listing calendar events for {emails} from {start_date} {start_time} to {end_date or start_date} {end_time} in timezone {time_zone}")
    if not end_date:
        end_date = start_date

    try:
        tz_obj = pytz.timezone(time_zone)
        start_dt_local = tz_obj.localize(datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M"))
        end_dt_local = tz_obj.localize(datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M"))
    except Exception as e:
        await ctx.error(f"Invalid date/time input: {str(e)}\n{traceback.format_exc()}")
        return {"error": f"Invalid date/time input: {str(e)}"}

    start_dt_utc = start_dt_local.astimezone(pytz.utc)
    end_dt_utc = end_dt_local.astimezone(pytz.utc)

    token_url = f"https://login.microsoftonline.com/{os.getenv('MS_TENANT_ID')}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("MS_CLIENT_ID"),
        "client_secret": os.getenv("MS_CLIENT_SECRET"),
        "scope": "https://graph.microsoft.com/.default"
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_url, data=token_data)

    if token_resp.status_code != 200:
        await ctx.error(f"Failed to obtain Microsoft Graph token: {token_resp.text}")
        return {"error": "Failed to obtain Microsoft Graph token", "details": token_resp.text}

    access_token = token_resp.json().get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    results = {}

    try:
        async with httpx.AsyncClient() as client:
            for email in emails:
                url = (
                    f"https://graph.microsoft.com/v1.0/users/{email}/calendarView"
                    f"?startDateTime={start_dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}&endDateTime={end_dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}"
                )
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    await ctx.error(f"Failed to fetch events for {email}: {resp.text}")
                    results[email] = {"error": f"Failed to fetch events: {resp.text}"}
                    continue

                events = resp.json().get("value", [])
                filtered_events = []
                for ev in events:
                    try:
                        ev_start_utc = parser.isoparse(ev.get("start", {}).get("dateTime", "")).astimezone(pytz.utc)
                        ev_end_utc = parser.isoparse(ev.get("end", {}).get("dateTime", "")).astimezone(pytz.utc)
                    except Exception:
                        await ctx.warning(f"Skipping event with invalid date format: {ev}")
                        continue

                    if ev_start_utc < end_dt_utc and ev_end_utc > start_dt_utc:
                        ev_start_local = ev_start_utc.astimezone(tz_obj)
                        ev_end_local = ev_end_utc.astimezone(tz_obj)
                        filtered_events.append({
                            "subject": ev.get("subject", ""),
                            "start": ev_start_local.strftime("%Y-%m-%d %H:%M"),
                            "end": ev_end_local.strftime("%Y-%m-%d %H:%M"),
                            "location": ev.get("location", {}).get("displayName", ""),
                            "organizer": ev.get("organizer", {}).get("emailAddress", {}).get("name", ""),
                            "event_id": ev.get("id", ""),
                            "attendees":ev.get("attendees"),
                            "organizer": ev.get("organizer")
                        })

                results[email] = filtered_events
        await ctx.info(f"Successfully fetched calendar events for {len(results)} users")
    except Exception as e:
        await ctx.error(f"Error while fetching calendar events: {str(e)}\n{traceback.format_exc()}")
        return {"error": f"Error while fetching calendar events: {str(e)}"}

    return {
        "status": "success",
        "start_date": start_date,
        "end_date": end_date,
        "start_time": start_time,
        "end_time": end_time,
        "time_zone": time_zone,
        "events": results,
        "results": str(resp.json().get("value", []))
    }



@mcp.tool(
    name="get_teams_timezones",
    description="List all IANA-supported time zones (used for scheduling and filtering calendar events)"
)
async def get_teams_timezones(ctx: Context = None) -> Dict[str, List[str] | str]:
    await ctx.info("Fetching list of supported IANA time zones")
    return {
        "message": "List of IANA-supported time zones. You can also check at https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
        "timezones": pytz.all_timezones
    }


def main():
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=4200,
        path="/mcp",
        log_level="info"
    )


if __name__ == "__main__":
    main()
