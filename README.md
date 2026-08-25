# myzoneTrack

An unofficial, dependency-free Python client for the requests made by the
Myzone Moves dashboard.

```python
from myzone import MyzoneClient

data = MyzoneClient("you@example.com", "your-password").dashboard()
print(data["latest_move"])
print(data["move_calendar"])
```

Create a local `.env` (it is excluded from Git):

```dotenv
MYZONE_USERNAME=you@example.com
MYZONE_PASSWORD=your-password
```

Then run:

```bash
uv run myzone.py
```

Without `.env`, pass the username as an argument; the terminal will prompt for
the password without echoing it. The module logs in with the supplied
credentials, keeps the resulting cookies
in memory, and returns the dashboard responses as ordinary Python objects. It
does not save the username, password, or cookies.
