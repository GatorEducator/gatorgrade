#!/usr/bin/env bash
# Show the diff for a specific mutant by job_id
# Usage: scripts/show_mutant_diff.sh <job_id>

JOB_ID="$1"

if [ -z "$JOB_ID" ]; then
    echo "Usage: $0 <job_id>"
    echo ""
    echo "Example: $0 33a053b45f654126811817a256780083"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Change to the project root (parent of scripts directory)
cd "$SCRIPT_DIR/.." || exit 1

# Get mutant details
MUTANT_INFO=$(sqlite3 cosmic-ray.sqlite "SELECT module_path, operator_name, occurrence, start_pos_row FROM mutation_specs WHERE job_id = '$JOB_ID';")

if [ -z "$MUTANT_INFO" ]; then
    echo "Error: Job ID not found in database"
    exit 1
fi

MODULE_PATH=$(echo "$MUTANT_INFO" | cut -d'|' -f1)
OPERATOR=$(echo "$MUTANT_INFO" | cut -d'|' -f2)
OCCURRENCE=$(echo "$MUTANT_INFO" | cut -d'|' -f3)
LINE=$(echo "$MUTANT_INFO" | cut -d'|' -f4)

# Get test outcome
OUTCOME=$(sqlite3 cosmic-ray.sqlite "SELECT test_outcome FROM work_results WHERE job_id = '$JOB_ID';")

echo "Mutant Details:"
echo "  Job ID: $JOB_ID"
echo "  File: $MODULE_PATH:$LINE"
echo "  Operator: $OPERATOR"
echo "  Occurrence: $OCCURRENCE"
echo "  Status: $OUTCOME"
echo ""
echo "Diff:"
sqlite3 cosmic-ray.sqlite "SELECT diff FROM work_results WHERE job_id = '$JOB_ID';"
