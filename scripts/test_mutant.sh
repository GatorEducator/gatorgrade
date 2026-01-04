#!/usr/bin/env bash
# Test a single mutant by job_id
# Usage: scripts/test_mutant.sh <job_id>

JOB_ID="$1"

if [ -z "$JOB_ID" ]; then
    echo "Usage: $0 <job_id>"
    echo ""
    echo "Example: $0 33a053b45f654126811817a256780083"
    echo ""
    echo "To find job IDs, run:"
    echo "  scripts/list_survivors.sh"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Change to the project root (parent of scripts directory)
cd "$SCRIPT_DIR/.." || exit 1

# Get mutant details from database
MUTANT_INFO=$(sqlite3 cosmic-ray.sqlite "SELECT module_path, operator_name, occurrence FROM mutation_specs WHERE job_id = '$JOB_ID';")

if [ -z "$MUTANT_INFO" ]; then
    echo "Error: Job ID not found in database"
    exit 1
fi

MODULE_PATH=$(echo "$MUTANT_INFO" | cut -d'|' -f1)
OPERATOR=$(echo "$MUTANT_INFO" | cut -d'|' -f2)
OCCURRENCE=$(echo "$MUTANT_INFO" | cut -d'|' -f3)

echo "Testing mutant:"
echo "  Job ID: $JOB_ID"
echo "  File: $MODULE_PATH"
echo "  Operator: $OPERATOR"
echo "  Occurrence: $OCCURRENCE"
echo ""
echo "Diff:"
sqlite3 cosmic-ray.sqlite "SELECT diff FROM work_results WHERE job_id = '$JOB_ID';"
echo ""
echo "Applying mutation..."

# Backup the original file
cp "$MODULE_PATH" "${MODULE_PATH}.backup"

# Apply the mutation
uv run cosmic-ray apply "$MODULE_PATH" "$OPERATOR" "$OCCURRENCE"

echo "Running tests..."
if uv run pytest -x --tb=short -q; then
    echo ""
    echo "RESULT: SURVIVED (tests passed with mutation)"
    EXIT_CODE=1
else
    echo ""
    echo "RESULT: KILLED (tests failed with mutation)"
    EXIT_CODE=0
fi

# Restore the original file
mv "${MODULE_PATH}.backup" "$MODULE_PATH"

exit $EXIT_CODE
