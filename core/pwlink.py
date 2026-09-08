import subprocess

# FUNCTION TO INTERACT WITH pw-link
def pwlink(args, timeout=5):
    if isinstance(args, str):
        args = args.split()

    proc = subprocess.run(
        ["pw-link", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )

    print(proc)

    return proc