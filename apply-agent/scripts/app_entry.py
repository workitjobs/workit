"""WorkIt Auto Apply's program (KAN-833, W8): scripts/build_app.py compiles this file into the app.

The app has no Python, so the one program does both jobs. Started by the student, it opens the window
(apply.student.app). Started by Chrome through a plain Worker's wrapper with the host flag first
(apply.plain.launcher), it runs only the plain Workers' relay (apply.plain.host), which imports nothing
of the app: Chrome starts it once per Worker, and it opens no window.
"""

import sys

from apply.plain import host

if sys.argv[1:2] == [host.APP_FLAG]:
    host.main(sys.argv[2:])
else:
    from apply.student import app

    app()
