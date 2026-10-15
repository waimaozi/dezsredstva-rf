import json
from pathlib import Path
import sys
from common import now, save

path = Path(sys.argv[1]) / 'last-run.json'
status = json.loads(path.read_text()) if path.exists() else {}
status.update(checked_at=now(), status='failed', runner_exit_code=int(sys.argv[2]))
save(path, status)
