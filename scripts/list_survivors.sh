#!/usr/bin/env bash
# List all surviving mutants with their details
# Usage: scripts/list_survivors.sh [limit]

LIMIT="${1:-10}"

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Change to the project root (parent of scripts directory)
cd "$SCRIPT_DIR/.." || exit 1

echo "Surviving Mutants (showing $LIMIT):"
echo "===================================="
echo ""

sqlite3 cosmic-ray.sqlite << SQL
.mode line
SELECT 
    m.job_id as 'Job ID',
    m.module_path || ':' || m.start_pos_row as 'Location',
    m.operator_name as 'Operator',
    m.occurrence as 'Occurrence'
FROM mutation_specs m 
JOIN work_results r ON m.job_id = r.job_id 
WHERE r.test_outcome = 'SURVIVED'
ORDER BY m.module_path, m.start_pos_row
LIMIT $LIMIT;
SQL

echo ""
echo "To see diff for a specific mutant, run:"
echo "  scripts/show_mutant_diff.sh <job_id>"
echo ""
echo "To test a specific mutant, run:"
echo "  scripts/test_mutant.sh <job_id>"
