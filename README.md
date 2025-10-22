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
PYTHONPATH=pretix-python ./tests/main.py
```

### Workflow

1. **Select Event Template**:
   - The program displays the 10 most recent events
   - Use arrow keys to select the event that should serve as a template
   - Confirm with Enter

2. **Enter New Event Data**:
   - **Event Name**: Enter the name for the new event (or press Enter to keep the same name)
   - **Date**: Choose the date for the new event (suggestion: next Saturday)
   - **Time**: Enter the start time (in HH:MM format)
   - **Duration**: Enter the duration in hours

3. **Select Description**:
   - The program shows all available description templates
   - These are located in the `descriptions/` folder
   - Choose the appropriate description for your event

4. **Done**:
   - The new event is created and automatically configured
   - For events with latecomer tickets, availability is automatically set to the Wednesday before the event

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