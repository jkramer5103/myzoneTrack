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
- Account-only lifetime workout count, MEPs, calories, and duration
- Friend count and monthly leaderboard position
- Weight and height from the account's biometrics
- A separate Home Assistant device for every friend sharing workout data, with
  latest workout metrics plus separate monthly and lifetime MEP/workout totals
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

## Python client

Protocol and authentication code now lives in the public, Python-only
[`myzoneAPI`](https://github.com/jkramer5103/myzoneAPI) repository. This
integration vendors a pinned snapshot of that module so HACS installs remain
self-contained; it is not a REST service and needs no separate setup.

## Development

```bash
python -m pytest
ruff check custom_components tests
```
