#!/bin/bash
# Quick local smoke test — no API calls, just import verification
set -euo pipefail

echo "=== Local Import Tests ==="

python3 -c "
import sys
sys.path.insert(0, '.')

errors = []

# Core contracts
try:
    from governance.core.budget_gate import preflight, is_paused
    print('  ✓ core.budget_gate')
except Exception as e:
    errors.append(f'  ✗ core.budget_gate: {e}')

try:
    from governance.core.audit_stream import emit_event, make_step_callback
    print('  ✓ core.audit_stream')
except Exception as e:
    errors.append(f'  ✗ core.audit_stream: {e}')

try:
    from governance.core.state_manager import save_checkpoint, load_checkpoint, get_entity
    print('  ✓ core.state_manager')
except Exception as e:
    errors.append(f'  ✗ core.state_manager: {e}')

# Crews
try:
    from governance.crews.base_crew import GovernanceCrew, make_llm
    print('  ✓ crews.base_crew')
except Exception as e:
    errors.append(f'  ✗ crews.base_crew: {e}')

try:
    from governance.crews.executive_crew import create_executive_crew
    print('  ✓ crews.executive_crew')
except Exception as e:
    errors.append(f'  ✗ crews.executive_crew: {e}')

try:
    from governance.crews.sales_crew import create_sales_crew
    print('  ✓ crews.sales_crew')
except Exception as e:
    errors.append(f'  ✗ crews.sales_crew: {e}')

try:
    from governance.crews.marketing_crew import create_marketing_crew
    print('  ✓ crews.marketing_crew')
except Exception as e:
    errors.append(f'  ✗ crews.marketing_crew: {e}')

# Specialists
try:
    from governance.specialists.app import app
    print('  ✓ specialists.app')
except Exception as e:
    errors.append(f'  ✗ specialists.app: {e}')

try:
    from governance.specialists.tools.composio_tools import get_specialist_tools
    print('  ✓ specialists.tools.composio_tools')
except Exception as e:
    errors.append(f'  ✗ specialists.tools.composio_tools: {e}')

# Integrations
try:
    from governance.integrations.slack_bridge import notify_agent_activity
    print('  ✓ integrations.slack_bridge')
except Exception as e:
    errors.append(f'  ✗ integrations.slack_bridge: {e}')

try:
    from governance.integrations.composio_setup import get_toolset
    print('  ✓ integrations.composio_setup')
except Exception as e:
    errors.append(f'  ✗ integrations.composio_setup: {e}')

if errors:
    print('')
    print('FAILURES:')
    for err in errors:
        print(err)
    sys.exit(1)
else:
    print('')
    print('All imports OK.')
" && echo "" && echo "=== State Manager Smoke Test ===" && python3 -c "
import sys, os, tempfile
sys.path.insert(0, '.')
os.environ['STATE_DB_PATH'] = '/tmp/test_governance.db'

from governance.core.state_manager import save_checkpoint, load_checkpoint, save_entity, get_entity, log_event, get_workflow_log

# checkpoint round-trip
save_checkpoint('test-tenant', 'test-crew', {'status': 'ok', 'step': 1})
loaded = load_checkpoint('test-tenant', 'test-crew')
assert loaded['status'] == 'ok', f'Expected ok, got {loaded}'
print('  ✓ checkpoint save/load')

# entity memory round-trip
save_entity('test-tenant', 'entity-1', 'last_action', {'type': 'email_sent'})
data = get_entity('test-tenant', 'entity-1')
assert data['last_action']['type'] == 'email_sent'
print('  ✓ entity memory save/load')

# workflow log
log_event('test-tenant', 'test-crew', 'kickoff_start', {'inputs': []})
logs = get_workflow_log('test-tenant', 'test-crew', limit=10)
assert len(logs) > 0
print('  ✓ workflow log write/read')

import os
os.unlink('/tmp/test_governance.db')
print('  ✓ cleanup OK')
print('')
print('State manager: all tests passed.')
"
echo ""
echo "=== Budget Gate Smoke Test ===" && python3 -c "
import sys
sys.path.insert(0, '.')

# Test circuit breaker + fail-open behavior
from governance.core.budget_gate import preflight, is_paused

# With no Paperclip running, should fail open
result = preflight('test_tool', 0.01, 'entity-1', 'test-tenant')
assert result == 'allow', f'Expected allow (fail-open), got {result}'
print('  ✓ fail-open when Paperclip unreachable')

# Emergency override
import os
os.environ['BUDGET_OVERRIDE'] = 'true'
result = preflight('test_tool', 9999.99, 'entity-1', 'test-tenant')
assert result == 'allow'
print('  ✓ BUDGET_OVERRIDE=true bypasses gate')
del os.environ['BUDGET_OVERRIDE']

print('')
print('Budget gate: all tests passed.')
"
