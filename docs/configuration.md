# When the code runs from somewhere else

By default the bot looks for `config.json` next to itself, which covers running
from a clone. An orchestrator does not work that way: it downloads the packaged
bot, extracts it into a working directory of its own, and runs it from there —
where no configuration exists.

One environment variable covers that. On Windows, from an **elevated**
PowerShell — machine scope, because a service runs under its own account and
would not see a user-scoped variable:

```powershell
[Environment]::SetEnvironmentVariable(
    'RPA_CHALLENGE_CONFIG', 'C:\path\to\the\project', 'Machine'
)
```

On Linux or macOS, in the service unit or the shell profile:

```bash
export RPA_CHALLENGE_CONFIG=/path/to/the/project
```

Processes read the environment when they start, so restart the runner — and
open a new terminal — before testing.

It accepts either the folder or the file, decided by whether the path has an
extension, never by touching the disk. And because `PATH_BASE` defaults to
**the folder the configuration was found in**, that single variable also
relocates `secret/`, `logs/` and `downloads/` — they belong next to the
configuration, not next to the code. Unset, everything falls back to the
repository root and a fresh clone needs no configuration at all.

---

## Database credentials (encrypted)

PostgreSQL credentials are stored encrypted with
[Fernet](https://cryptography.io/en/latest/fernet/) under `secret/`:

```
secret/
└── db_credentials/
    ├── credentials.json   ← {"email": "<encrypted>", "password": "<encrypted>"}
    └── secret.key         ← Fernet key (binary)
```

To generate them:

```python
import json
import os

from cryptography.fernet import Fernet

key = Fernet.generate_key()
fernet = Fernet(key)

os.makedirs('secret/db_credentials', exist_ok=True)

with open('secret/db_credentials/secret.key', 'wb') as f:
    f.write(key)

with open('secret/db_credentials/credentials.json', 'w') as f:
    json.dump(
        {
            'email': fernet.encrypt(b'your_user').decode(),
            'password': fernet.encrypt(b'your_password').decode(),
        },
        f,
    )
```

---

---

[← Back to the README](../README.md)
