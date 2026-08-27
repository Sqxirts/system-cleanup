# system-cleanup

Interactive Windows disk cleanup script. Scans the Recycle Bin, user Temp folder, and the Windows Update cache (`SoftwareDistribution\Download`), shows you the size of each, and asks yes/no before clearing anything.

Windows Update cache is owned by SYSTEM/TrustedInstaller, so clearing it needs admin rights. Rather than requiring the whole script to run elevated, it only relaunches that one step in an elevated window (UAC prompt) when needed.

## Usage

```
python system_cleanup.py
```

Requires Python 3. No dependencies.
