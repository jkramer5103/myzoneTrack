# Myzone Track for Home Assistant

An unofficial, cloud-polling Myzone Moves integration for Home Assistant. It
signs in to the Myzone dashboard, reads every dashboard endpoint, and presents
workout and progress data as native sensors.

## Features

- UI configuration with email and password validation
- Latest workout: timestamp, MEPs, calories, duration, effort, average/peak
  heart rate, and time in zone
- Monthly MEP and workout totals
- Notifications, challenges, questions, and food-entry counts
- Full latest-workout, monthly graph, calendar, goal, challenge, question, and
  food payloads retained as sensor attributes
- Five-minute shared polling coordinator
- Numeric sensors use Home Assistant state classes, so Recorder automatically
  makes them available in History; monthly totals also produce long-term
  statistics

This uses undocumented Myzone web endpoints and may need updates if Myzone
changes its dashboard.

## Install with HACS

Because this repository is private, make it public before using it as a HACS
custom repository. In HACS, open **Custom repositories**, paste this repository
URL, select **Integration**, and install **Myzone Track**. Restart Home
Assistant, then go to **Settings → Devices & services → Add integration** and
search for **Myzone Track**.

Credentials are stored in Home Assistant's config entry storage and are never
written by this integration to logs or entity attributes.

## Manual install

Copy `custom_components/myzone_track` into the `custom_components` directory in
your Home Assistant configuration, restart, and add the integration from the
UI.

## Standalone client

The original `myzone.py` client remains available for development. Create a
local `.env` (excluded from Git), then run `uv run myzone.py`.

## Development

```bash
python -m pytest
ruff check custom_components tests
```
