# RefImpl — calibration reference for the Batch Rename Studio contract

Not an experiment deliverable. This is the **known-TRUE input** used to prove
that `holdout/score.py` awards points to a correct implementation, so that a
zero from a real arm means "the arm failed", not "the scorer is broken".

Build:

    dotnet build -c Release

Run:

    BatchRenameStudio.exe --plan --dir <folder> --rules <rules.json> --out <plan.json>
