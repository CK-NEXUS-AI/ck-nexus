# Testing Rules

Testing has three distinct levels:

1. Static/unit: code correctness.
2. Integration/runtime: components actually interact.
3. Live/production-like: the target environment actually enforces the contract.

A passing test is evidence only for the scope it exercised.

For every important test record:
- exact revision;
- command;
- exit code;
- relevant output/artifact;
- environment;
- timestamp.

Do not hide failures with unconditional success or broad "|| true" unless the failure is explicitly normalized and evaluated afterward.
