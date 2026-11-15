---
description: Show the user how to run the first-time setup or change the Legal tools settings
---
The user wants to set up or change the settings of the Legal tools (work mode, Legal folder, database password, user name, VAT, default event location, backups).

1. Tell the user, in Hebrew, that the settings wizard must be run **by them** in a terminal window, and give the exact command with the plugin root shown in the session-start message `[Legal plugin] root: ...`:
   `powershell -NoProfile -File "<plugin root>\tools\Setup-MasTmd.ps1"`
   First run asks all questions one by one (every question shows its default; press Enter to accept it). Later runs show the current settings and let them change any of them.
2. Do **not** run the wizard, answer it, or create or edit the settings file yourself.
3. When the user says they finished, run `Invoke-MasTmdWrite.ps1 -Action ShowPaths` and report the mode, the Legal folder and whether the database was found.
