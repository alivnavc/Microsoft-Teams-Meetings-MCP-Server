# Microsoft Teams MCP Server

A server to schedule, reschedule, cancel Microsoft Teams interviews, and manage calendar events using the Microsoft Graph API.

## Features

- Schedule new Microsoft Teams meetings with attendees, subject, and body.
- Reschedule existing meetings by updating their start and end times.
- Cancel meetings using their event ID.
- List team calendar events with timezone support.
- Retrieve a list of IANA-supported timezones for scheduling and filtering events.

## Prerequisites

- Python 3.8 or higher.
- A Microsoft Azure AD application with Microsoft Graph API permissions (e.g., `Calendars.ReadWrite`, `User.Read.All`).
- `git` and `pip` installed on your system.
- (Optional) `uv` for running the server (install via `pip install uv`).
- (Optional) `ngrok` for exposing the local server with HTTPS (required for OpenAI API integration).

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/teams-mcp-server.git
   cd teams-mcp-server
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Unix/Linux/MacOS:
   source venv/bin/activate
   # On Windows (Command Prompt):
   venv\Scripts\activate
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Create a `.env` file in the project root.
   - Add your Microsoft Graph API credentials:
     ```env
     MS_TENANT_ID=your_tenant_id
     MS_CLIENT_ID=your_client_id
     MS_CLIENT_SECRET=your_client_secret
     MS_USER_ID=your_user_id
     ```

5. Run the server:
   ```bash
   python server.py
   ```
   Or, if using `uv`:
   ```bash
   uv run server.py
   ```
6. Deploying through Docker(Optional)

    Pull and Run Docker Image with .env file
    ``` 
    docker pull alivnavc/microsoft-teams-mcp

    docker run -d -p 4200:4200 --name teams-mcp-server --env-file /path/to/.env alivnavc/microsoft-teams-mcp

    ```
    --env-file /path/to/.env loads environment variables from your local .env file into the container
    (replace /path/to/.env with the actual path to your .env file)

    Verify container is running

    ```
    docker ps
    ```

## Azure AD Setup for Microsoft Graph API

To use the Microsoft Graph API, you need to register an application in Microsoft Azure AD and configure the necessary permissions. Follow these steps (summarized from [MS-Teams-setup.md](https://github.com/InditexTech/mcp-teams-server/blob/master/doc/MS-Teams-setup.md)):

1. **Register an Azure AD Application**:
   - Create a Microsoft Entra ID application in the Azure portal.
   - Note the application UUID (set as `MS_CLIENT_ID` in your `.env` file).
   - Configure the application for either Single Tenant or Multi Tenant:
     - For Single Tenant, store the tenant UUID in `MS_TENANT_ID` and set `MS_APP_TYPE=SingleTenant`.
     - For Multi Tenant, adjust settings accordingly in Azure.

2. **Add a Client Secret**:
   - Generate a client secret for your Azure AD application.
   - Store the secret in `MS_CLIENT_SECRET` in your `.env` file.

3. **Configure Microsoft Graph API Permissions**:
   - Add the `Calendars.ReadWrite` permission (and optionally `User.Read.All` for listing events) to your Azure AD application.
   - Ensure the permissions are granted admin consent.

4. **Azure Bot Registration (Optional)**:
   - If integrating with Microsoft Teams channels, register an Azure Bot using the same `MS_CLIENT_ID`.
   - Connect the bot to the Teams channel and configure it to use the Microsoft Graph API.

For detailed instructions, refer to [MS-Teams-setup.md](https://github.com/InditexTech/mcp-teams-server/blob/master/doc/MS-Teams-setup.md).

## Usage

The server runs on `http://localhost:4200/mcp/` by default when running locally. It exposes a JSON-RPC API for interacting with Microsoft Teams meetings and calendars.

### Important Notes
- **Microsoft’s MCP Server**: Microsoft provides an MCP server for managing Teams meetings, but certain tools (e.g., scheduling with custom attendees, rescheduling, canceling, and timezone-supported calendar event listing) were found to be missing or insufficient. This project was developed to address those gaps, providing a custom implementation with the tools described below.
- **Storing Event IDs**: When scheduling a meeting using `schedule_teams_meeting`, the response includes an `event_id`. Store this ID in a database or a local file (e.g., JSON or CSV) as it is required for rescheduling (`reschedule_teams_meeting`) or canceling (`cancel_teams_meeting`) the meeting. For example, you can save the `event_id` and related metadata (e.g., meeting subject, date) in a SQLite database or a JSON file for easy retrieval.
- **OpenAI API Integration**: If you plan to integrate this server with the OpenAI API, note that OpenAI requires HTTPS endpoints. The local server (`http://localhost:4200/mcp/`) will not work with OpenAI. Use `ngrok` to expose the local server with an HTTPS URL:
  1. Install `ngrok` (e.g., via `npm install -g ngrok` or download from [ngrok.com](https://ngrok.com)).
  2. Run:
     ```bash
     ngrok http 4200
     ```
     to generate an HTTPS URL (e.g., `https://your-ngrok-subdomain.ngrok.io`).
  3. Use the ngrok URL (e.g., `https://your-ngrok-subdomain.ngrok.io/mcp/`) as the endpoint for OpenAI API integration.

### Deploying on a Server
1. Deploy the application on a server (e.g., AWS EC2, Azure VM).
2. Update the server URL in your client to the server’s public IP or domain (e.g., `http://your-server-ip:4200/mcp/`).
3. Ensure HTTPS is enabled for production using a reverse proxy like Nginx.
4. Secure sensitive data (e.g., API credentials) using environment variables.

## API Usage

The server uses the `FastMCP` framework to expose JSON-RPC endpoints for managing Microsoft Teams meetings and calendars. Below are the available tools, their features, and how to use them with example JSON-RPC payloads.

### 1. `schedule_teams_meeting`
**Description**: Schedules a new Microsoft Teams meeting with a specified subject, start/end times (in UTC, ISO 8601 format), meeting body, and required attendees.

**Features**:
- Creates a Teams meeting with a unique join URL.
- Supports multiple attendees with email addresses and names.
- Allows HTML or plain text for the meeting body.
- Returns the event ID and join URL upon successful scheduling. **Store the `event_id` for rescheduling or canceling the meeting.**

**Usage**:
- **Method**: `tools/call`
- **Parameters**:
  - `subject` (string): The title of the meeting.
  - `body` (string): The meeting description (HTML or plain text).
  - `start_time` (string): Meeting start time in ISO 8601 UTC format (e.g., `2025-09-10T18:00:00Z`).
  - `end_time` (string): Meeting end time in ISO 8601 UTC format.
  - `required_attendees` (list): List of attendee objects, each with `email` (valid email) and `name` (string).

**Example Payload**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "schedule_teams_meeting",
    "arguments": {
      "subject": "Technical Interview - Backend Engineer",
      "body": "Dear candidate,<br><br>Please join the Microsoft Teams meeting for your interview.<br><br>Regards,<br>Recruitment Team",
      "required_attendees": [
        {
          "email": "example@domain.com",
          "name": "Alice Applicant"
        }
      ],
      "start_time": "2025-09-10T18:00:00Z",
      "end_time": "2025-09-10T19:00:00Z"
    }
  }
}
```

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "event_id": "AAMkADg0OWNmYTNjLTJlZmQtNDc2Ny1hNjAyLWNlZDE2MjEzNzAwMQBGAAAAAADbWWPmN-qjQqZ5uOjCatRNBwD4kwMhw138Q6oKJi3U2FGBAAAAAAENAAD4kwMhw138Q6oKJi3U2FGBAAFJIBYCAAA",
    "join_url": "https://teams.microsoft.com/l/meetup-join/..."
  }
}
```

### 2. `reschedule_teams_meeting`
**Description**: Reschedules an existing Microsoft Teams meeting by updating its start and end times.

**Features**:
- Updates the start and end times of an existing meeting using its event ID.
- Maintains other meeting details (e.g., attendees, subject).
- Returns the event ID upon successful rescheduling.
- Requires the `event_id` from a previously scheduled meeting.

**Usage**:
- **Method**: `tools/call`
- **Parameters**:
  - `event_id` (string): The Microsoft Graph event ID of the meeting to reschedule.
  - `start_time` (string): New start time in ISO 8601 UTC format.
  - `end_time` (string): New end time in ISO 8601 UTC format.

**Example Payload**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "reschedule_teams_meeting",
    "arguments": {
      "event_id": "AAMkADE1MzJlYTAwLWRkZTMtNDAyMy04ZTk2LTljOTI4OWRjYjg5MABGAAAAAABaL71tdJQET4NwOuYku0EHBwC7MkKjdoRHQ4cHEDY3mToXAAAAAAENAAC7MkKjdoRHQ4cHEDY3mToXAAFPchCuAAA=",
      "start_time": "2025-09-07T14:00:00Z",
      "end_time": "2025-09-07T16:00:00Z"
    }
  }
}
```

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "event_id": "AAMkADE1MzJlYTAwLWRkZTMtNDAyMy04ZTk2LTljOTI4OWRjYjg5MABGAAAAAABaL71tdJQET4NwOuYku0EHBwC7MkKjdoRHQ4cHEDY3mToXAAAAAAENAAC7MkKjdoRHQ4cHEDY3mToXAAFPchCuAAA=",
    "join_url": ""
  }
}
```

### 3. `cancel_teams_meeting`
**Description**: Cancels an existing Microsoft Teams meeting using its event ID.

**Features**:
- Deletes a meeting from the calendar.
- Returns a confirmation message upon successful cancellation.
- Requires the `event_id` from a previously scheduled meeting.

**Usage**:
- **Method**: `tools/call`
- **Parameters**:
  - `event_id` (string): The Microsoft Graph event ID of the meeting to cancel.

**Example Payload**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "cancel_teams_meeting",
    "arguments": {
      "event_id": "AAMkADg0OWNmYTNjLTJlZmQtNDc2Ny1hNjAyLWNlZDE2MjEzNzAwMQBGAAAAAADbWWPmN-qjQqZ5uOjCatRNBwD4kwMhw138Q6oKJi3U2FGBAAAAAAENAAD4kwMhw138Q6oKJi3U2FGBAAFJIBYCAAA"
    }
  }
}
```

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "message": "Interview 'AAMkADg0OWNmYTNjLTJlZmQtNDc2Ny1hNjAyLWNlZDE2MjEzNzAwMQBGAAAAAADbWWPmN-qjQqZ5uOjCatRNBwD4kwMhw138Q6oKJi3U2FGBAAAAAAENAAD4kwMhw138Q6oKJi3U2FGBAAFJIBYCAAA' canceled in Teams."
  }
}
```

### 4. `list_team_calendar_events`
**Description**: Lists calendar events for specified team members within a given date range and timezone.

**Features**:
- Retrieves events for multiple email addresses.
- Supports custom date ranges and times with timezone conversion (IANA timezones, e.g., `America/Los_Angeles`).
- Filters events to include only those within the specified time window.
- Returns detailed event information (subject, start/end times, location, organizer, attendees, event ID).

**Usage**:
- **Method**: `tools/call`
- **Parameters**:
  - `emails` (list): List of email addresses to fetch events for.
  - `start_date` (string): Start date in `YYYY-MM-DD` format.
  - `end_date` (string, optional): End date in `YYYY-MM-DD` format (defaults to `start_date` if not provided).
  - `start_time` (string, optional): Start time in `HH:MM` format (defaults to `00:00`).
  - `end_time` (string, optional): End time in `HH:MM` format (defaults to `23:59`).
  - `time_zone` (string, optional): IANA timezone (defaults to `UTC`).

**Example Payload**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "list_team_calendar_events",
    "arguments": {
      "emails": ["example@domain.com"],
      "start_date": "2025-09-07",
      "time_zone": "America/Los_Angeles"
    }
  }
}
```

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "status": "success",
    "start_date": "2025-09-07",
    "end_date": "2025-09-07",
    "start_time": "00:00",
    "end_time": "23:59",
    "time_zone": "America/Los_Angeles",
    "events": {
      "example@domain.com": [
        {
          "subject": "Technical Interview - Backend Engineer",
          "start": "2025-09-07 11:00",
          "end": "2025-09-07 12:00",
          "location": "Microsoft Teams Meeting",
          "organizer": "Recruitment Team",
          "event_id": "AAMkADg0OWNmYTNjLTJlZmQtNDc2Ny1hNjAyLWNlZDE2MjEzNzAwMQBGAAAAAADbWWPmN-qjQqZ5uOjCatRNBwD4kwMhw138Q6oKJi3U2FGBAAAAAAENAAD4kwMhw138Q6oKJi3U2FGBAAFJIBYCAAA",
          "attendees": [
            {
              "emailAddress": {
                "address": "example@domain.com",
                "name": "Alice Applicant"
              },
              "type": "required"
            }
          ]
        }
      ]
    },
    "results": "[...]"
  }
}
```

### 5. `get_teams_timezones`
**Description**: Retrieves a list of all IANA-supported timezones for use in scheduling or filtering calendar events.

**Features**:
- Returns the complete list of IANA timezones supported by the `pytz` library.
- Useful for ensuring valid timezone inputs for other API calls (e.g., `list_team_calendar_events`).

**Usage**:
- **Method**: `tools/call`
- **Parameters**: None.

**Example Payload**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_teams_timezones",
    "arguments": {}
  }
}
```

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "message": "List of IANA-supported time zones. You can also check at https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
    "timezones": [
      "Africa/Abidjan",
      "Africa/Accra",
      "America/Los_Angeles",
      ...
    ]
  }
}
```

### Listing Available Tools
To retrieve a list of all available tools (e.g., to discover `schedule_teams_meeting`, `reschedule_teams_meeting`, etc.), use the `tools/list` method.

**Example Payload**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {
    "cursor": "optional-cursor-value"
  }
}
```

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "schedule_teams_meeting",
        "description": "Schedule a Microsoft Teams meeting by specifying the subject, start/end times (ISO 8601 UTC), meeting body, and a list of required attendees..."
      },
      {
        "name": "reschedule_teams_meeting",
        "description": "Reschedule an existing interview in Microsoft Teams"
      },
      {
        "name": "cancel_teams_meeting",
        "description": "Cancel an interview in Microsoft Teams"
      },
      {
        "name": "list_team_calendar_events",
        "description": "List calendar events for team members between specified dates and times with timezone support"
      },
      {
        "name": "get_teams_timezones",
        "description": "List all IANA-supported time zones (used for scheduling and filtering calendar events)"
      }
    ],
    "next_cursor": null
  }
}
```

# Connect your LLM to MCP Server
Example: OpenAI API
```python
from openai import OpenAI

client = OpenAI(api_key="your_api_key_here")

resp = client.responses.create(
    model="gpt-4.1",
    tools=[
        {
            "type": "mcp",
            "server_label": "meetings_scheduler",
            "server_url": "https://yourdomain.com/mcp/",
            "require_approval": "never",
        },
    ],
    input="""
"Schedule a meeting titled 'Project Sync' starting at 2025-09-01T14:00:00Z ending at 2025-09-01T15:00:00Z. The body is 'Discuss project updates'. "
Please scheduel and let ,me know .
required Attendee name is Naveen and email is example@email.com

"""
)
print(resp)
print(resp.output_text)

# "Schedule a meeting titled 'Project Sync' starting at 2025-09-01T14:00:00Z ending at 2025-09-01T15:00:00Z. The body is 'Discuss project updates'. "
# Please scheduel and let ,me know .
# required Attendee name is Naveen and email is email@email.com

#could you please give me the event id of the meeting scheduled on August 9th, 2025 PST timezone with email@email.com """

#Can you please reschedule the meeting  event id 
# ET4NwOuYku0EHBwC7MkKjdoRHQ4cHEDY3mToXAAAAAAENAAC7MkKjdoRHQ4cHEDY3mToXAAFPchCwAAA=
#  to sept 20, 2025 same time.
# """
# Can you please cancel the interview  event id  is
# AAMAyMy04ZTk2LTljOTI4OWRjYjg5MABGAAAAAABaL71tdJQET4NwOuYku0EHBwC7MkKjdoRHQ4cHEDY3mToXAAAAAAENAAC7MkKjdoRHQ4cHEDY3mToXAAFPchCwAAA=
```

## API Documentation
For additional details on endpoints and parameters, refer to the [Microsoft Graph API documentation](https://docs.microsoft.com/en-us/graph/api/overview).

## Contributing
Contributions are welcome! We encourage you to contribute by adding new tools or enhancing existing ones to further improve the functionality of this MCP server. Please submit issues or pull requests via GitHub. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.