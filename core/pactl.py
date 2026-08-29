import subprocess

# FUNCTION TO INTERACT WITH pactl
def pactl(args: str, timeout: int = 5) -> str:
    proc = subprocess.run(
        ["pactl"] + args.split(),
        capture_output=True,
        text=True,
        check=True,      # <<< raises CalledProcessError on failure
        timeout=timeout  # <<< prevents infinite hangs
    )
    
    stdout = proc.stdout.strip()
    
    # Guard load-module: stdout must be a clean numeric module ID
    if args.startswith("load-module") and not stdout.isdigit():
        raise RuntimeError(
            f"pactl load-module returned garbage ID: {stdout!r} | stderr: {proc.stderr.strip()!r}"
        )
    
    return stdout