-- Fix 1: Remove doc:review from EDITOR if it was mistakenly assigned
DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE name = 'EDITOR')
  AND permission_id = (SELECT id FROM permissions WHERE name = 'doc:review');

-- Fix 2: Move system:backup from ADMIN to SUPER_ADMIN
DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE name = 'ADMIN')
  AND permission_id = (SELECT id FROM permissions WHERE name = 'system:backup');

INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'SUPER_ADMIN' AND p.name = 'system:backup';
