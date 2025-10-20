"""
LICS Backend Authentication API Endpoints

FastAPI endpoints for authentication, user registration, and account management.
Follows Documentation.md Section 10.1-10.2 for JWT and security patterns.
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.schemas.auth import (
    # Request schemas
    LoginRequest, LogoutRequest, RefreshTokenRequest,
    UserRegistrationRequest, PasswordResetRequest, PasswordResetConfirm,
    PasswordChangeRequest, EmailVerificationRequest, ResendVerificationRequest,
    UserUpdateRequest, MFASetupRequest, MFAConfirmRequest, MFADisableRequest,
    UserRoleAssignment, SessionTerminateRequest,

    # Response schemas
    LoginResponse, LoginResponseWrapper, UserRegistrationResponse,
    UserRegistrationResponseWrapper, UserProfile, UserProfileResponse,
    TokenPair, TokenPairResponse, AccessTokenResponse, AccessTokenResponseWrapper,
    UserSessionInfo, SessionListResponse, MFASetupResponse,

    # Filter schemas
    UserFilterSchema, SessionListResponse
)
from app.schemas.base import (
    BaseResponse, PaginatedResponse, ErrorResponse, PaginationParams,
    create_response, create_paginated_response, create_error_response
)
from app.services.auth import (
    AuthService, UserService, PasswordService, MFAService, SessionService,
    AuthenticationError, InvalidTokenError, AccountLockedError,
    MFARequiredError, WeakPasswordError
)
from app.services.base import (
    ServiceError, ValidationError, NotFoundError, ConflictError, PermissionError
)

logger = get_logger(__name__)

# Create router
router = APIRouter()

# Security scheme for Bearer token
security = HTTPBearer(auto_error=False)

# Service instances
auth_service = AuthService()
user_service = UserService()
password_service = PasswordService()
mfa_service = MFAService()
session_service = SessionService()


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Extract user agent from request."""
    return request.headers.get("User-Agent", "unknown")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_db_session)
) -> Optional[UserProfile]:
    """
    Get current authenticated user from JWT token.

    Returns None if no token provided or invalid token.
    For endpoints that require authentication, use get_current_active_user instead.
    """
    if not credentials:
        logger.warning("get_current_user: No credentials provided")
        return None

    try:
        from app.core.security import verify_token, ACCESS_TOKEN_TYPE
        from app.services.auth import UserRepository, is_token_in_blacklist
        from app.models.auth import User
        from sqlalchemy import and_

        logger.info(f"get_current_user: Verifying token starting with: {credentials.credentials[:30]}...")

        # Verify and decode JWT token
        payload = verify_token(credentials.credentials, ACCESS_TOKEN_TYPE, return_payload=True)
        if not payload:
            logger.warning(f"get_current_user: Token verification returned None")
            return None

        # Check if token is blacklisted (logged out)
        jti = payload.get("jti")
        if jti and is_token_in_blacklist(jti):
            logger.warning(f"get_current_user: Token is blacklisted (logged out): {jti}")
            return None

        # Extract user ID from token
        user_id = payload.get("sub")
        if not user_id:
            logger.warning(f"get_current_user: No 'sub' in token payload: {list(payload.keys())}")
            return None

        # Load user from database using the session passed to this function
        user_repo = UserRepository(User, session)
        user = await user_repo.get_by_id(uuid.UUID(user_id))

        if not user:
            logger.warning(f"get_current_user: User not found in database: {user_id}")
            return None

        # Check if user is active
        if not user.is_active:
            logger.warning(f"get_current_user: User {user_id} is not active")
            return None

        # Convert roles to RoleInfo with permissions
        from app.schemas.auth import PermissionInfo, RoleInfo

        role_infos = []
        all_permissions = set()

        for role in user.roles:
            # Collect permission infos for this role
            permission_infos = []
            for permission in role.permissions:
                permission_info = PermissionInfo(
                    id=permission.id,
                    name=permission.name,
                    display_name=permission.display_name,
                    description=permission.description,
                    resource=permission.resource,
                    action=permission.action,
                    is_system_permission=permission.is_system_permission,
                    created_at=permission.created_at,
                    updated_at=permission.updated_at
                )
                permission_infos.append(permission_info)
                all_permissions.add(permission.name)  # Add to user's total permissions

            role_info = RoleInfo(
                id=role.id,
                name=role.name,
                display_name=role.display_name,
                description=role.description,
                is_system_role=role.is_system_role,
                is_default=role.is_default,
                parent_role_id=role.parent_role_id,
                created_at=role.created_at,
                updated_at=role.updated_at,
                permissions=permission_infos
            )
            role_infos.append(role_info)

        # Create UserProfile with populated roles and permissions
        user_profile = UserProfile(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            organization_id=user.organization_id,
            timezone=user.timezone,
            language=user.language,
            last_login_at=user.last_login_at,
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=role_infos,
            permissions=all_permissions
        )

        logger.info(f"get_current_user: Successfully authenticated user {user.email}")
        return user_profile

    except Exception as e:
        logger.error(f"get_current_user: Exception during verification: {e}", exc_info=True)
        return None


async def get_current_active_user(
    current_user: Optional[UserProfile] = Depends(get_current_user)
) -> UserProfile:
    """
    Get current authenticated user, raising 401 if not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    return current_user


# ===== AUTHENTICATION ENDPOINTS =====

@router.post(
    "/login",
    response_model=LoginResponseWrapper,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user with email and password, return access and refresh tokens"
)
async def login(
    login_data: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> LoginResponseWrapper:
    """
    Authenticate user and create session.

    - **email**: User's email address
    - **password**: User's password
    - **remember_me**: Extend session duration (optional)
    - **mfa_code**: Multi-factor authentication code (if MFA enabled)

    Returns user profile, JWT tokens, and session information.
    """
    try:
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        user, token_pair, session_id = await auth_service.authenticate_user(
            email=login_data.email,
            password=login_data.password,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Convert user to UserProfile schema
        user_profile = UserProfile(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            organization_id=user.organization_id,
            timezone=user.timezone,
            language=user.language,
            last_login_at=user.last_login_at,
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=[],  # TODO: Convert roles to RoleInfo
            permissions=set()  # TODO: Get user permissions
        )

        login_response = LoginResponse(
            user=user_profile,
            tokens=token_pair,
            session_id=session_id,
            requires_mfa=False  # TODO: Check if MFA is required
        )

        return create_response(login_response)

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message
        )
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=e.message
        )
    except MFARequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post(
    "/refresh",
    response_model=TokenPair,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Generate new access token using refresh token"
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session)
) -> TokenPair:
    """
    Refresh access token using valid refresh token.

    - **refresh_token**: Valid JWT refresh token

    Returns new token pair with extended access token.
    """
    try:
        token_pair = await auth_service.refresh_access_token(refresh_data.refresh_token)
        return token_pair

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Logout user and invalidate session(s)"
)
async def logout(
    current_user: UserProfile = Depends(get_current_active_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    logout_data: Optional[LogoutRequest] = None,
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Logout user and invalidate sessions.

    - **everywhere**: Logout from all devices (optional, default: false)

    Invalidates current session or all user sessions if everywhere=true.
    Also blacklists the current access token.
    """
    try:
        everywhere = logout_data.everywhere if logout_data else False

        # Extract token and blacklist it
        if credentials:
            from app.core.security import get_token_payload
            from app.services.auth import add_token_to_blacklist

            payload = get_token_payload(credentials.credentials)
            if payload and "jti" in payload:
                add_token_to_blacklist(payload["jti"])
                logger.info(f"Blacklisted token JTI: {payload['jti']}")

        await auth_service.logout_user(
            user_id=current_user.id,
            everywhere=everywhere
        )

        return {"message": "Logged out successfully"}

    except ServiceError as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# ===== USER REGISTRATION ENDPOINTS =====

@router.post(
    "/register",
    response_model=UserRegistrationResponseWrapper,
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Register new user account"
)
async def register_user(
    registration_data: UserRegistrationRequest,
    session: AsyncSession = Depends(get_db_session)
) -> UserRegistrationResponseWrapper:
    """
    Register new user account.

    - **email**: User's email address (must be unique)
    - **username**: Username (must be unique, 3-50 characters)
    - **password**: Password (8+ characters with complexity requirements)
    - **password_confirm**: Password confirmation (must match password)
    - **first_name**: First name (optional)
    - **last_name**: Last name (optional)
    - **organization_id**: Organization to associate user with
    - **timezone**: User's timezone (optional, default: UTC)
    - **language**: Language preference (optional, default: en)

    Returns user profile and registration status.
    """
    try:
        user = await user_service.register_user(registration_data)

        user_profile = UserProfile(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            organization_id=user.organization_id,
            timezone=user.timezone,
            language=user.language,
            last_login_at=user.last_login_at,
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=[],  # TODO: Convert roles to RoleInfo
            permissions=set()
        )

        registration_response = UserRegistrationResponse(
            user=user_profile,
            message="User registered successfully",
            verification_required=not user.is_verified
        )

        return create_response(registration_response)

    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post(
    "/verify-email",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Email",
    description="Verify user email with verification token"
)
async def verify_email(
    verification_data: EmailVerificationRequest,
    session: AsyncSession = Depends(get_db_session)
) -> UserProfileResponse:
    """
    Verify user email address using verification token.

    - **token**: Email verification token received via email

    Updates user verification status and returns user profile.
    """
    try:
        user = await user_service.verify_email(verification_data.token)

        user_profile = UserProfile(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            organization_id=user.organization_id,
            timezone=user.timezone,
            language=user.language,
            last_login_at=user.last_login_at,
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=[],
            permissions=set()
        )

        return create_response(user_profile)

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.post(
    "/resend-verification",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resend Verification Email",
    description="Resend email verification link"
)
async def resend_verification_email(
    resend_data: ResendVerificationRequest,
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Resend email verification link to user.

    - **email**: User's email address

    Sends new verification email if user exists and is not verified.
    """
    try:
        # TODO: Implement resend verification logic
        # This would generate a new verification token and send email

        return {"message": "Verification email sent if account exists"}

    except ServiceError as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )


# ===== PASSWORD MANAGEMENT ENDPOINTS =====

@router.post(
    "/password/forgot",
    status_code=status.HTTP_200_OK,
    summary="Request Password Reset",
    description="Request password reset link via email"
)
@router.post(
    "/request-password-reset",
    status_code=status.HTTP_200_OK,
    summary="Request Password Reset",
    description="Request password reset link via email",
    include_in_schema=False  # Alias, don't show in API docs
)
async def forgot_password(
    reset_data: PasswordResetRequest,
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Request password reset for user account.

    - **email**: User's email address

    Sends password reset email if account exists.
    """
    try:
        reset_token = await password_service.request_password_reset(reset_data.email)

        # In production, this would send an email and not return the token
        # For development/testing, we return the token
        return {"message": "Password reset email sent if account exists"}

    except ServiceError as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )


@router.post(
    "/password/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset Password",
    description="Reset password using reset token"
)
async def reset_password(
    reset_data: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Reset user password using reset token.

    - **token**: Password reset token received via email
    - **password**: New password (8+ characters with complexity requirements)
    - **password_confirm**: Password confirmation (must match password)

    Updates user password and clears reset token.
    """
    try:
        await password_service.reset_password(reset_data.token, reset_data.password)

        return {"message": "Password reset successfully"}

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post(
    "/password/change",
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Change user password (requires authentication)"
)
@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Change user password (requires authentication)",
    include_in_schema=False  # Alias, don't show in API docs
)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Change user password (authenticated users only).

    - **current_password**: Current password for verification
    - **new_password**: New password (8+ characters with complexity requirements)
    - **new_password_confirm**: New password confirmation (must match new_password)

    Updates user password after verifying current password.
    """
    try:
        await password_service.change_password(
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )

        return {"message": "Password changed successfully"}

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message
        )
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


# ===== USER PROFILE ENDPOINTS =====

@router.get(
    "/me",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Get current authenticated user's profile information"
)
async def get_current_user_profile(
    current_user: UserProfile = Depends(get_current_active_user)
) -> UserProfile:
    """
    Get current user's profile information.

    Returns complete user profile including roles and permissions.
    """
    return current_user


@router.patch(
    "/me",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Update User Profile",
    description="Update current user's profile information"
)
@router.put(
    "/profile",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Update User Profile",
    description="Update current user's profile information",
    include_in_schema=False  # Alias, don't show in API docs
)
async def update_user_profile(
    profile_data: UserUpdateRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> UserProfile:
    """
    Update current user's profile information.

    - **first_name**: First name (optional)
    - **last_name**: Last name (optional)
    - **timezone**: User's timezone (optional)
    - **language**: Language preference (optional)

    Returns updated user profile.
    """
    try:
        updated_user = await user_service.update_profile(
            user_id=current_user.id,
            update_data=profile_data,
            current_user_id=current_user.id
        )

        user_profile = UserProfile(
            id=updated_user.id,
            email=updated_user.email,
            username=updated_user.username,
            first_name=updated_user.first_name,
            last_name=updated_user.last_name,
            is_active=updated_user.is_active,
            is_verified=updated_user.is_verified,
            is_superuser=updated_user.is_superuser,
            organization_id=updated_user.organization_id,
            timezone=updated_user.timezone,
            language=updated_user.language,
            last_login_at=updated_user.last_login_at,
            mfa_enabled=updated_user.mfa_enabled,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
            roles=[],
            permissions=set()
        )

        return user_profile

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


# ===== SESSION MANAGEMENT ENDPOINTS =====

@router.get(
    "/sessions",
    status_code=status.HTTP_200_OK,
    summary="Get User Sessions",
    description="Get current user's active sessions"
)
async def get_user_sessions(
    current_user: UserProfile = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, List[UserSessionInfo]]:
    """
    Get current user's active sessions.

    Returns list of active sessions with device information.
    """
    try:
        sessions = await session_service.get_user_sessions(current_user.id)

        session_info_list = []
        for user_session in sessions:
            session_info = UserSessionInfo(
                id=user_session.id,
                user_id=user_session.user_id,
                session_token=f"sess_***{user_session.session_token[-6:]}",  # Masked token
                ip_address=user_session.ip_address,
                user_agent=user_session.user_agent,
                expires_at=user_session.expires_at,
                last_activity_at=user_session.last_activity_at,
                is_active=user_session.is_active,
                is_current=False,  # TODO: Determine current session
                created_at=user_session.created_at,
                updated_at=user_session.updated_at
            )
            session_info_list.append(session_info)

        return {"sessions": session_info_list}

    except ServiceError as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )


@router.delete(
    "/sessions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Terminate Sessions",
    description="Terminate specific user sessions"
)
async def terminate_sessions(
    terminate_data: SessionTerminateRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Terminate specific user sessions.

    - **session_ids**: List of session IDs to terminate

    Terminates specified sessions belonging to current user.
    """
    try:
        await session_service.terminate_sessions(
            session_ids=terminate_data.session_ids,
            current_user_id=current_user.id
        )

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Terminate sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to terminate sessions"
        )


# ===== MFA ENDPOINTS =====

@router.post(
    "/mfa/setup",
    response_model=MFASetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Setup MFA",
    description="Setup multi-factor authentication for current user"
)
@router.post(
    "/mfa/enable",
    response_model=MFASetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Setup MFA",
    description="Setup multi-factor authentication for current user",
    include_in_schema=False  # Alias, don't show in API docs
)
async def setup_mfa(
    current_user: UserProfile = Depends(get_current_active_user),
    mfa_data: Optional[MFASetupRequest] = None,
    session: AsyncSession = Depends(get_db_session)
) -> MFASetupResponse:
    """
    Setup multi-factor authentication.

    - **password**: Current password for verification (optional for testing)

    Returns MFA secret, QR code URL, and backup codes.
    """
    try:
        # For testing purposes, allow empty password (will use empty string)
        password = mfa_data.password if mfa_data else ""

        mfa_response = await mfa_service.setup_mfa(
            user_id=current_user.id,
            password=password
        )

        return mfa_response

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"MFA setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA setup failed"
        )


@router.post(
    "/mfa/confirm",
    status_code=status.HTTP_200_OK,
    summary="Confirm MFA Setup",
    description="Confirm MFA setup with verification code"
)
async def confirm_mfa(
    mfa_data: MFAConfirmRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Confirm MFA setup with verification code.

    - **code**: 6-digit verification code from authenticator app

    Enables MFA for the user account.
    """
    try:
        await mfa_service.confirm_mfa(
            user_id=current_user.id,
            code=mfa_data.code
        )

        return {"message": "MFA enabled successfully"}

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"MFA confirm error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA confirmation failed"
        )


@router.post(
    "/mfa/disable",
    status_code=status.HTTP_200_OK,
    summary="Disable MFA",
    description="Disable multi-factor authentication"
)
async def disable_mfa(
    mfa_data: MFADisableRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Disable multi-factor authentication.

    - **password**: Current password for verification
    - **code**: 6-digit MFA code or backup code

    Disables MFA for the user account.
    """
    try:
        await mfa_service.disable_mfa(
            user_id=current_user.id,
            password=mfa_data.password,
            code=mfa_data.code
        )

        return {"message": "MFA disabled successfully"}

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"MFA disable error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA disable failed"
        )