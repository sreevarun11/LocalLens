import os
import re
import sys

# Directories to audit (strictly production code, ignoring tests/ and demo_snapshots/)
TARGET_DIRS = [
    os.path.join("backend", "app"),
    os.path.join("frontend", "src")
]

# Patterns forbidden in production code
BANNED_PATTERNS = [
    (r"\bmock[A-Z0-9_]*\b", "mock token"),
    (r"\bdummy[A-Z0-9_]*\b", "dummy data token"),
    (r"\bsampleData\b", "sampleData token"),
    (r"\[\s*\{\s*[\"']?lat[\"']?\s*:\s*\d+\.\d+\s*,\s*[\"']?lng[\"']?\s*:\s*\d+\.\d+\s*\}", "hard-coded coordinate array")
]

def scan_files():
    violations = []
    for base_dir in TARGET_DIRS:
        if not os.path.exists(base_dir):
            continue
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            # Skip comments that might explain compliance or tests
                            stripped = line.strip()
                            if stripped.startswith(("#", "//", "/*", "*")):
                                continue
                            for pattern, desc in BANNED_PATTERNS:
                                if re.search(pattern, line, re.IGNORECASE):
                                    # Allow legitimate words like 'mockup' or 'unmocked'
                                    if "mockup" in line.lower():
                                        continue
                                    violations.append((path, line_no, desc, stripped))
    return violations

if __name__ == "__main__":
    print("=== Running No-Mock & Zero-Fabrication Linter ===")
    violations = scan_files()
    if violations:
        print(f"\n[FAIL] Found {len(violations)} forbidden fabrication pattern(s):")
        for path, line_no, desc, line in violations:
            print(f"  {path}:{line_no} [{desc}] -> {line[:80]}")
        sys.exit(1)
    else:
        print("[PASS] Zero mock/dummy/hard-coded coordinate data found in production source files.")
        sys.exit(0)
