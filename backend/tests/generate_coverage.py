#!/usr/bin/env python
"""
Generate test coverage report
Requirements: 9.5
"""

import subprocess
import sys
import json
from pathlib import Path

def main():
    print("=" * 60)
    print("Running Test Suite with Coverage")
    print("=" * 60)
    print()
    
    # Run pytest with coverage
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "--cov=application",
            "--cov=domain",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=json",
            "-v"
        ],
        capture_output=True,
        text=True
    )
    
    # Print output
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    print()
    print("=" * 60)
    print("Coverage Report Generated")
    print("=" * 60)
    print()
    
    # Check if coverage.json exists
    coverage_file = Path("coverage.json")
    if coverage_file.exists():
        with open(coverage_file) as f:
            data = json.load(f)
            total = data['totals']
            
            print(f"Coverage Summary:")
            print(f"  Lines Covered: {total['covered_lines']}/{total['num_statements']} ({total['percent_covered']:.1f}%)")
            print(f"  Missing Lines: {total['missing_lines']}")
            print(f"  Excluded Lines: {total['excluded_lines']}")
            print()
            
            # Check if we meet the 90% threshold
            if total['percent_covered'] >= 90:
                print("✅ Coverage target met (90%+)")
            else:
                print(f"⚠️  Coverage below target: {total['percent_covered']:.1f}% < 90%")
    
    print()
    print("HTML Report: htmlcov/index.html")
    print("JSON Report: coverage.json")
    print()
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
