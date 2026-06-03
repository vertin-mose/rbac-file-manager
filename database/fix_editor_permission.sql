-- Fix: Remove doc:review from EDITOR if it was mistakenly assigned
-- This only removes the record, no data loss.
DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE name = 'EDITOR')
  AND permission_id = (SELECT id FROM permissions WHERE name = 'doc:review');
