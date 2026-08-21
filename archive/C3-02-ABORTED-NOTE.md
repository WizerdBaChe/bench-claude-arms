C3-02 aborted 2026-08-20, NOT a valid run. Terminated by the print-mode background-task
wait ceiling (600s) while its subagents were still working; the PowerShell batch then
aborted because \Continue='Stop' fires on a native exe's stderr under 2>&1.
Both causes were fixes to the harness, not to the arm. Kept for the record; excluded from
all analysis. Replaced by a fresh C3-02 run under the corrected harness.
