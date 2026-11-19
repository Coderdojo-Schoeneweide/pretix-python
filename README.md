# pretix-python

Python library and tool for creating events in the pretix ticketing system.

## Description

This program enables cloning and automatic customization of events in the pretix ticketing system. It was developed to quickly create recurring events (e.g., workshops) by using an existing event as a template.

## Prerequisites

- Python 3.7 or higher
- A pretix account with API token
- Organizer permissions in pretix

## Installation

1. **Clone or download the repository**

2. **Create a virtual environment** (recommended but not necessary)
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
4. **Configure environment variables**:
   
   Create a `.env` file in the main directory with the following content:
   ```
   API_TOKEN=your_pretix_api_token
   ORGANIZER=your_organizer_slug
   ```
   
   - `API_TOKEN`: Your personal API token from pretix (found under: teams → klick on a team → under API-Tokens → add)
   - `ORGANIZER`: The slug of your organizer (e.g., "dojosw")

## Usage

### Starting the Program

There are two ways to start the program:

**Option 1: Using the run.sh script**
```bash
./run.sh r
```

**Option 2: Directly with Python**
```bash
PYTHONPATH=pretix-python python3 main.py
```

### Main Menu Options

- **Create Event**: Clone a template event and create a single event.
- **Create Event Series**: Clone a template event as an event series (`has_subevents=True`) and add multiple sub-event dates (individually or recurring weekly).
- **Add Sub-events to Series**: Add new sub-event dates to an existing event series.
- **Change Description**: Update the frontpage text and title of an event or series.
- **Change Location**: Change the venue location of an event.
- **Shred Past Events**: Export and shred personal attendee data from past events.

### Creating an Event Series

1. Select **Create Event Series** from the main menu.
2. Choose a template event to copy settings, products, and categories from.
3. Enter the series slug (e.g. `workshop-series-2026`).
4. Choose how to configure dates:
   - **Add dates individually**: Select start/end times for each date interactively and optionally set custom date names.
   - **Create recurring weekly dates**: Choose the start date/time of the first session, enter the number of dates and the weekly interval.
5. Choose a workshop description and required devices.
6. The program creates the event series container and all sub-events on pretix, configuring quotas for each date and adjusting latecomer ticket availability.

### Adding Sub-events to an Existing Series

1. Select **Add Sub-events to Series** from the main menu.
2. Select an existing event series from the list.
3. Choose how to configure dates (individually or recurring weekly).
4. The program adds the sub-events to the series on pretix, setting up quotas based on existing sub-event quotas and adjusting latecomer ticket availability.

### Managing Description Templates

Descriptions are managed in the `descriptions/` folder. Each template has its own subfolder with language files:

```
descriptions/
  my_workshop/
    de-informal.txt    # German versionc
    en.txt             # English version
```

To add a new description:
1. Create a new folder under `descriptions/`
2. Create the desired language files (e.g., `de-informal.txt`, `en.txt`)
3. Add the description text to the files

## Development

For testing and development, you can start an interactive Python shell with preloaded modules:

```bash
./run.sh t
```

This starts `ipython` with the correct PYTHONPATH.