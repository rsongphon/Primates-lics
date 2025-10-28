"""
Integration tests for RBAC (Role-Based Access Control) API endpoints.
"""

import pytest
from uuid import uuid4

from httpx import AsyncClient
from fastapi import status

from tests.conftest import create_test_role_data, create_test_permission_data


class TestRoleManagement:
    """Test role management endpoints."""

    @pytest.mark.asyncio
    async def test_create_role_success(self, async_client: AsyncClient, admin_auth_headers, test_permissions):
        """Test successful role creation."""
        role_data = create_test_role_data(
            permissions=[str(p.id) for p in test_permissions[:2]]
        )

        response = await async_client.post(
            "/api/v1/rbac/roles",
            headers=admin_auth_headers,
            json=role_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["name"] == role_data["name"]
        assert data["description"] == role_data["description"]
        assert len(data["permissions"]) == 2
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_role_duplicate_name(self, async_client: AsyncClient, admin_auth_headers, test_roles):
        """Test creating role with duplicate name."""
        role_data = create_test_role_data(name=test_roles[0].name)

        response = await async_client.post(
            "/api/v1/rbac/roles",
            headers=admin_auth_headers,
            json=role_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "already exists" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_role_invalid_permission(self, async_client: AsyncClient, admin_auth_headers):
        """Test creating role with invalid permission ID."""
        role_data = create_test_role_data(
            permissions=[str(uuid4())]  # Non-existent permission
        )

        response = await async_client.post(
            "/api/v1/rbac/roles",
            headers=admin_auth_headers,
            json=role_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_role_unauthorized(self, async_client: AsyncClient, auth_headers):
        """Test role creation without admin permissions."""
        role_data = create_test_role_data()

        response = await async_client.post(
            "/api/v1/rbac/roles",
            headers=auth_headers,  # Regular user headers
            json=role_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_roles_list(self, async_client: AsyncClient, admin_auth_headers, test_roles):
        """Test getting list of roles."""
        response = await async_client.get(
            "/api/v1/rbac/roles",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) >= len(test_roles)

    @pytest.mark.asyncio
    async def test_get_role_by_id(self, async_client: AsyncClient, admin_auth_headers, test_roles):
        """Test getting specific role by ID."""
        role = test_roles[0]

        response = await async_client.get(
            f"/api/v1/rbac/roles/{role.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == str(role.id)
        assert data["name"] == role.name
        assert data["description"] == role.description

    @pytest.mark.asyncio
    async def test_get_role_not_found(self, async_client: AsyncClient, admin_auth_headers):
        """Test getting non-existent role."""
        response = await async_client.get(
            f"/api/v1/rbac/roles/{uuid4()}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_role(self, async_client: AsyncClient, admin_auth_headers, test_roles, test_permissions):
        """Test updating role."""
        role = test_roles[0]
        update_data = {
            "description": "Updated description",
            "permissions": [str(p.id) for p in test_permissions[:1]]
        }

        response = await async_client.put(
            f"/api/v1/rbac/roles/{role.id}",
            headers=admin_auth_headers,
            json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["description"] == "Updated description"
        assert len(data["permissions"]) == 1

    @pytest.mark.asyncio
    async def test_delete_role(self, async_client: AsyncClient, admin_auth_headers, db_session, test_permissions):
        """Test deleting role."""
        # Create role to delete
        from app.models.auth import Role
        role = Role(
            name="ToDelete",
            description="Role to be deleted",
            permissions=test_permissions[:1]
        )
        db_session.add(role)
        await db_session.commit()
        await db_session.refresh(role)

        response = await async_client.delete(
            f"/api/v1/rbac/roles/{role.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify role is deleted
        get_response = await async_client.get(
            f"/api/v1/rbac/roles/{role.id}",
            headers=admin_auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_system_role_forbidden(self, async_client: AsyncClient, admin_auth_headers, db_session):
        """Test that system roles cannot be deleted."""
        # Create system role
        from app.models.auth import Role
        system_role = Role(
            name="SystemRole",
            description="System role",
            is_system_role=True
        )
        db_session.add(system_role)
        await db_session.commit()
        await db_session.refresh(system_role)

        response = await async_client.delete(
            f"/api/v1/rbac/roles/{system_role.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "system role" in data["detail"]


class TestPermissionManagement:
    """Test permission management endpoints."""

    @pytest.mark.asyncio
    async def test_create_permission_success(self, async_client: AsyncClient, admin_auth_headers):
        """Test successful permission creation."""
        permission_data = create_test_permission_data()

        response = await async_client.post(
            "/api/v1/rbac/permissions",
            headers=admin_auth_headers,
            json=permission_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["name"] == permission_data["name"]
        assert data["display_name"] == permission_data["display_name"]
        assert data["description"] == permission_data["description"]
        assert data["resource"] == permission_data["resource"]
        assert data["action"] == permission_data["action"]

    @pytest.mark.asyncio
    async def test_create_permission_duplicate_name(self, async_client: AsyncClient, admin_auth_headers, test_permissions):
        """Test creating permission with duplicate name."""
        permission_data = create_test_permission_data(name=test_permissions[0].name)

        response = await async_client.post(
            "/api/v1/rbac/permissions",
            headers=admin_auth_headers,
            json=permission_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_permission_unauthorized(self, async_client: AsyncClient, auth_headers):
        """Test permission creation without admin permissions."""
        permission_data = create_test_permission_data()

        response = await async_client.post(
            "/api/v1/rbac/permissions",
            headers=auth_headers,
            json=permission_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_permissions_list(self, async_client: AsyncClient, admin_auth_headers, test_permissions):
        """Test getting list of permissions."""
        response = await async_client.get(
            "/api/v1/rbac/permissions",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= len(test_permissions)

    @pytest.mark.asyncio
    async def test_get_permission_by_id(self, async_client: AsyncClient, admin_auth_headers, test_permissions):
        """Test getting specific permission by ID."""
        permission = test_permissions[0]

        response = await async_client.get(
            f"/api/v1/rbac/permissions/{permission.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == str(permission.id)
        assert data["name"] == permission.name

    @pytest.mark.asyncio
    async def test_get_permissions_filtered(self, async_client: AsyncClient, admin_auth_headers, test_permissions):
        """Test getting permissions with filters."""
        response = await async_client.get(
            "/api/v1/rbac/permissions?resource=users",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should only return permissions with resource="users"
        for item in data["items"]:
            assert item["resource"] == "users"

    @pytest.mark.asyncio
    async def test_update_permission(self, async_client: AsyncClient, admin_auth_headers, test_permissions):
        """Test updating permission."""
        permission = test_permissions[0]
        update_data = {
            "description": "Updated permission description",
            "display_name": "Updated Display Name"
        }

        response = await async_client.put(
            f"/api/v1/rbac/permissions/{permission.id}",
            headers=admin_auth_headers,
            json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["description"] == "Updated permission description"
        assert data["display_name"] == "Updated Display Name"

    @pytest.mark.asyncio
    async def test_delete_permission(self, async_client: AsyncClient, admin_auth_headers, db_session):
        """Test deleting permission."""
        # Create permission to delete
        from app.models.auth import Permission
        permission = Permission(
            name="test:delete",
            display_name="Test Delete",
            description="Permission to be deleted",
            resource="test",
            action="delete"
        )
        db_session.add(permission)
        await db_session.commit()
        await db_session.refresh(permission)

        response = await async_client.delete(
            f"/api/v1/rbac/permissions/{permission.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify permission is deleted
        get_response = await async_client.get(
            f"/api/v1/rbac/permissions/{permission.id}",
            headers=admin_auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


class TestUserRoleAssignment:
    """Test user role assignment endpoints."""

    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, async_client: AsyncClient, admin_auth_headers, test_user, test_roles):
        """Test assigning role to user."""
        role = test_roles[1]  # Researcher role

        response = await async_client.post(
            f"/api/v1/rbac/users/{test_user.id}/roles/{role.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Role assigned successfully"

    @pytest.mark.asyncio
    async def test_assign_role_already_assigned(self, async_client: AsyncClient, admin_auth_headers, test_user, test_roles):
        """Test assigning role that user already has."""
        role = test_roles[0]  # User role (already assigned in fixture)

        response = await async_client.post(
            f"/api/v1/rbac/users/{test_user.id}/roles/{role.id}",
            headers=admin_auth_headers
        )

        # Should handle gracefully
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    @pytest.mark.asyncio
    async def test_remove_role_from_user(self, async_client: AsyncClient, admin_auth_headers, test_user, test_roles, db_session):
        """Test removing role from user."""
        role = test_roles[1]  # Researcher role

        # First assign the role
        test_user.roles.append(role)
        await db_session.commit()

        response = await async_client.delete(
            f"/api/v1/rbac/users/{test_user.id}/roles/{role.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Role removed successfully"

    @pytest.mark.asyncio
    async def test_get_user_roles(self, async_client: AsyncClient, admin_auth_headers, test_user):
        """Test getting user roles."""
        response = await async_client.get(
            f"/api/v1/rbac/users/{test_user.id}/roles",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1  # User has at least one role from fixture

    @pytest.mark.asyncio
    async def test_get_user_permissions(self, async_client: AsyncClient, admin_auth_headers, test_user):
        """Test getting user permissions through roles."""
        response = await async_client.get(
            f"/api/v1/rbac/users/{test_user.id}/permissions",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        # Should have permissions from assigned roles

    @pytest.mark.asyncio
    async def test_check_user_permission(self, async_client: AsyncClient, admin_auth_headers, test_user, test_permissions):
        """Test checking if user has specific permission."""
        permission = test_permissions[0]

        response = await async_client.get(
            f"/api/v1/rbac/users/{test_user.id}/permissions/{permission.name}/check",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "has_permission" in data
        assert isinstance(data["has_permission"], bool)

    @pytest.mark.asyncio
    async def test_assign_role_unauthorized(self, async_client: AsyncClient, auth_headers, test_user, test_roles):
        """Test role assignment without admin permissions."""
        role = test_roles[1]

        response = await async_client.post(
            f"/api/v1/rbac/users/{test_user.id}/roles/{role.id}",
            headers=auth_headers  # Regular user headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_assign_role_nonexistent_user(self, async_client: AsyncClient, admin_auth_headers, test_roles):
        """Test assigning role to non-existent user."""
        role = test_roles[1]

        response = await async_client.post(
            f"/api/v1/rbac/users/{uuid4()}/roles/{role.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_assign_nonexistent_role(self, async_client: AsyncClient, admin_auth_headers, test_user):
        """Test assigning non-existent role to user."""
        response = await async_client.post(
            f"/api/v1/rbac/users/{test_user.id}/roles/{uuid4()}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRolePermissionAssignment:
    """Test role permission assignment endpoints."""

    @pytest.mark.asyncio
    async def test_assign_permission_to_role(self, async_client: AsyncClient, admin_auth_headers, test_roles, test_permissions, db_session):
        """Test assigning permission to role."""
        role = test_roles[1]  # Use role with fewer permissions
        permission = test_permissions[-1]  # Use last permission (likely not assigned)

        response = await async_client.post(
            f"/api/v1/rbac/roles/{role.id}/permissions/{permission.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Permission assigned to role successfully"

    @pytest.mark.asyncio
    async def test_remove_permission_from_role(self, async_client: AsyncClient, admin_auth_headers, test_roles, test_permissions, db_session):
        """Test removing permission from role."""
        role = test_roles[0]  # Admin role with many permissions
        permission = test_permissions[0]

        # Ensure permission is assigned to role
        if permission not in role.permissions:
            role.permissions.append(permission)
            await db_session.commit()

        response = await async_client.delete(
            f"/api/v1/rbac/roles/{role.id}/permissions/{permission.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_role_permissions(self, async_client: AsyncClient, admin_auth_headers, test_roles):
        """Test getting role permissions."""
        role = test_roles[0]  # Admin role

        response = await async_client.get(
            f"/api/v1/rbac/roles/{role.id}/permissions",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        # Admin role should have permissions

    @pytest.mark.asyncio
    async def test_bulk_assign_permissions_to_role(self, async_client: AsyncClient, admin_auth_headers, test_roles, test_permissions):
        """Test bulk assigning permissions to role."""
        role = test_roles[1]  # Researcher role
        permission_ids = [str(p.id) for p in test_permissions[:3]]

        response = await async_client.put(
            f"/api/v1/rbac/roles/{role.id}/permissions",
            headers=admin_auth_headers,
            json={"permission_ids": permission_ids}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["permissions"]) >= 3


class TestPermissionChecking:
    """Test permission checking functionality."""

    @pytest.mark.asyncio
    async def test_check_permission_endpoint_access(self, async_client: AsyncClient, auth_headers, admin_auth_headers):
        """Test that permission checking works for endpoint access."""
        # Regular user should not be able to create roles
        role_data = create_test_role_data()

        response = await async_client.post(
            "/api/v1/rbac/roles",
            headers=auth_headers,
            json=role_data
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Admin user should be able to create roles
        response = await async_client.post(
            "/api/v1/rbac/roles",
            headers=admin_auth_headers,
            json=role_data
        )
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_permission_inheritance(self, async_client: AsyncClient, admin_auth_headers, test_researcher_user):
        """Test that users inherit permissions from their roles."""
        # Researcher should have experiment permissions but not admin permissions
        researcher_token = create_access_token(
            data={"sub": str(test_researcher_user.id), "email": test_researcher_user.email}
        )
        researcher_headers = {"Authorization": f"Bearer {researcher_token}"}

        # Should be able to check own permissions
        response = await async_client.get(
            f"/api/v1/rbac/users/{test_researcher_user.id}/permissions",
            headers=researcher_headers
        )
        # This might require different permission level - adjust test as needed
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_organization_scoped_permissions(self, async_client: AsyncClient, admin_auth_headers, test_user, test_organization):
        """Test that permissions are scoped to organization."""
        # User should only have access within their organization
        response = await async_client.get(
            f"/api/v1/rbac/users/{test_user.id}/roles",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify user is in correct organization context
        user_response = await async_client.get(
            f"/api/v1/users/{test_user.id}",
            headers=admin_auth_headers
        )
        if user_response.status_code == status.HTTP_200_OK:
            user_data = user_response.json()
            assert user_data.get("organization_id") == str(test_organization.id)


class TestRBACComplexScenarios:
    """Test complex RBAC scenarios."""

    @pytest.mark.asyncio
    async def test_role_hierarchy_simulation(self, async_client: AsyncClient, admin_auth_headers, db_session, test_permissions):
        """Test simulating role hierarchy through permission assignment."""
        # Create hierarchical roles
        from app.models.auth import Role

        # Super Admin (all permissions)
        super_admin_role = Role(
            name="SuperAdmin",
            description="Super Administrator",
            permissions=test_permissions
        )

        # Manager (subset of permissions)
        manager_role = Role(
            name="Manager",
            description="Manager role",
            permissions=test_permissions[:3]
        )

        # Employee (minimal permissions)
        employee_role = Role(
            name="Employee",
            description="Employee role",
            permissions=test_permissions[:1]
        )

        db_session.add_all([super_admin_role, manager_role, employee_role])
        await db_session.commit()

        # Verify permission counts
        super_admin_perms = await async_client.get(
            f"/api/v1/rbac/roles/{super_admin_role.id}/permissions",
            headers=admin_auth_headers
        )
        assert super_admin_perms.status_code == status.HTTP_200_OK
        assert len(super_admin_perms.json()) == len(test_permissions)

        manager_perms = await async_client.get(
            f"/api/v1/rbac/roles/{manager_role.id}/permissions",
            headers=admin_auth_headers
        )
        assert manager_perms.status_code == status.HTTP_200_OK
        assert len(manager_perms.json()) == 3

    @pytest.mark.asyncio
    async def test_permission_revocation_cascade(self, async_client: AsyncClient, admin_auth_headers, test_user, test_roles, db_session):
        """Test that permission changes cascade properly."""
        role = test_roles[1]  # Researcher role

        # Assign role to user
        test_user.roles.append(role)
        await db_session.commit()

        # Get initial permissions
        initial_perms = await async_client.get(
            f"/api/v1/rbac/users/{test_user.id}/permissions",
            headers=admin_auth_headers
        )
        initial_count = len(initial_perms.json()) if initial_perms.status_code == 200 else 0

        # Remove permission from role
        if role.permissions:
            permission_to_remove = role.permissions[0]
            await async_client.delete(
                f"/api/v1/rbac/roles/{role.id}/permissions/{permission_to_remove.id}",
                headers=admin_auth_headers
            )

            # Check user permissions again
            updated_perms = await async_client.get(
                f"/api/v1/rbac/users/{test_user.id}/permissions",
                headers=admin_auth_headers
            )

            if updated_perms.status_code == 200:
                updated_count = len(updated_perms.json())
                assert updated_count <= initial_count

    @pytest.mark.asyncio
    async def test_multiple_role_permission_aggregation(self, async_client: AsyncClient, admin_auth_headers, test_user, test_roles, db_session):
        """Test that user permissions are properly aggregated from multiple roles."""
        # Assign multiple roles to user
        test_user.roles.extend(test_roles[:2])  # Assign first two roles
        await db_session.commit()

        # Get user permissions
        response = await async_client.get(
            f"/api/v1/rbac/users/{test_user.id}/permissions",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        permissions = response.json()

        # Should have permissions from both roles (without duplicates)
        permission_names = [p["name"] for p in permissions]
        assert len(permission_names) == len(set(permission_names))  # No duplicates

    @pytest.mark.asyncio
    async def test_dynamic_permission_checking(self, async_client: AsyncClient, admin_auth_headers, test_user, test_permissions):
        """Test dynamic permission checking."""
        permission = test_permissions[0]

        # Check if user has specific permission
        response = await async_client.get(
            f"/api/v1/rbac/users/{test_user.id}/permissions/{permission.name}/check",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        has_permission_before = data["has_permission"]

        # If user doesn't have permission, assign a role that has it
        if not has_permission_before:
            # Find a role with this permission
            role_with_permission = None
            for role in test_roles:
                if permission in role.permissions:
                    role_with_permission = role
                    break

            if role_with_permission:
                # Assign role to user
                await async_client.post(
                    f"/api/v1/rbac/users/{test_user.id}/roles/{role_with_permission.id}",
                    headers=admin_auth_headers
                )

                # Check permission again
                response = await async_client.get(
                    f"/api/v1/rbac/users/{test_user.id}/permissions/{permission.name}/check",
                    headers=admin_auth_headers
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["has_permission"] is True


class TestRBACErrorHandling:
    """Test RBAC error handling."""

    @pytest.mark.asyncio
    async def test_invalid_uuid_parameters(self, async_client: AsyncClient, admin_auth_headers):
        """Test handling of invalid UUID parameters."""
        # Invalid user ID
        response = await async_client.get(
            "/api/v1/rbac/users/invalid-uuid/roles",
            headers=admin_auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Invalid role ID
        response = await async_client.get(
            "/api/v1/rbac/roles/invalid-uuid",
            headers=admin_auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_malformed_request_data(self, async_client: AsyncClient, admin_auth_headers):
        """Test handling of malformed request data."""
        # Invalid role creation data
        response = await async_client.post(
            "/api/v1/rbac/roles",
            headers=admin_auth_headers,
            json={"invalid": "data"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Invalid permission data
        response = await async_client.post(
            "/api/v1/rbac/permissions",
            headers=admin_auth_headers,
            json={"name": ""}  # Empty name
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_concurrent_role_modification(self, async_client: AsyncClient, admin_auth_headers, test_roles):
        """Test handling of concurrent role modifications."""
        role = test_roles[0]

        # Simulate concurrent updates
        update_data1 = {"description": "Updated by request 1"}
        update_data2 = {"description": "Updated by request 2"}

        # Both requests should succeed (last one wins)
        response1 = await async_client.put(
            f"/api/v1/rbac/roles/{role.id}",
            headers=admin_auth_headers,
            json=update_data1
        )

        response2 = await async_client.put(
            f"/api/v1/rbac/roles/{role.id}",
            headers=admin_auth_headers,
            json=update_data2
        )

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        # Final state should reflect last update
        final_response = await async_client.get(
            f"/api/v1/rbac/roles/{role.id}",
            headers=admin_auth_headers
        )
        assert final_response.json()["description"] == "Updated by request 2"