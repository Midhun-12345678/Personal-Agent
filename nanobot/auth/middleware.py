"""
Auth middleware for per-user identification.
Maps API tokens or user identifiers to isolated user workspaces.
"""
import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class UserContext:
    """Represents an authenticated user context."""
    user_id: str
    display_name: str
    token: str


class AuthManager:
    """Manages user registration and authentication via token-based auth."""

    def __init__(self, workspace: Path):
        """
        Initialize AuthManager.
        
        Args:
            workspace: Base workspace path where users.json is stored.
        """
        self.workspace = workspace
        self.users_file = workspace / "users.json"
        self._users: dict[str, dict[str, Any]] = self._load_users()

    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def user_exists(self, display_name: str) -> bool:
        """
        Check if a user with this display name exists.
        
        Args:
            display_name: The display name to check.
            
        Returns:
            True if user exists, False otherwise.
        """
        self._users = self._load_users()
        name_lower = display_name.lower().strip()
        for user_data in self._users.values():
            if user_data.get("display_name", "").lower().strip() == name_lower:
                return True
        return False

    def login(self, display_name: str, password: str) -> UserContext | None:
        """
        Login an existing user by name and password.
        
        Args:
            display_name: The user's display name.
            password: The user's password.
            
        Returns:
            UserContext if credentials are valid, None otherwise.
        """
        self._users = self._load_users()
        name_lower = display_name.lower().strip()
        password_hash = self._hash_password(password)
        
        for user_data in self._users.values():
            if user_data.get("display_name", "").lower().strip() == name_lower:
                stored_hash = user_data.get("password_hash", "")
                if stored_hash and stored_hash == password_hash:
                    return UserContext(
                        user_id=user_data["user_id"],
                        display_name=user_data["display_name"],
                        token=user_data["token"],
                    )
                elif not stored_hash:
                    # User exists but has no password - allow login for backwards compatibility
                    return UserContext(
                        user_id=user_data["user_id"],
                        display_name=user_data["display_name"],
                        token=user_data["token"],
                    )
        return None

    def register_user(self, display_name: str, password: str | None = None) -> UserContext:
        """
        Creates a new user with a unique ID and secure token.
        
        Args:
            display_name: Human-readable name for the user.
            password: Optional password for the user.
            
        Returns:
            UserContext with user_id, display_name, and token.
        """
        user_id = str(uuid.uuid4())[:8]
        token = secrets.token_urlsafe(32)
        
        user_data = {
            "user_id": user_id,
            "display_name": display_name,
            "token": token,
        }
        
        if password:
            user_data["password_hash"] = self._hash_password(password)
        
        self._users[token] = user_data
        self._save_users(self._users)
        
        return UserContext(
            user_id=user_id,
            display_name=display_name,
            token=token,
        )

    def authenticate(self, token: str) -> UserContext | None:
        """
        Authenticate a user by their token.
        
        Args:
            token: The authentication token to look up.
            
        Returns:
            UserContext if token is valid, None otherwise.
        """
        # Reload users to pick up any external changes
        self._users = self._load_users()
        
        user_data = self._users.get(token)
        if user_data is None:
            return None
        
        return UserContext(
            user_id=user_data["user_id"],
            display_name=user_data["display_name"],
            token=user_data["token"],
        )

    def _load_users(self) -> dict[str, dict[str, Any]]:
        """
        Load users from users.json.
        
        Returns:
            Dict mapping tokens to user data, or empty dict if file doesn't exist.
        """
        if not self.users_file.exists():
            return {}
        
        try:
            with open(self.users_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_users(self, data: dict[str, dict[str, Any]]) -> None:
        """
        Save users to users.json atomically.
        
        Args:
            data: Dict mapping tokens to user data.
        """
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Write to temp file first, then rename for atomicity
        temp_file = self.users_file.with_suffix(".json.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.users_file)
        except Exception:
            if temp_file.exists():
                temp_file.unlink()
            raise


def require_auth(auth_manager: AuthManager, token: str) -> UserContext:
    """
    Authenticate a token or raise PermissionError.
    
    Args:
        auth_manager: The AuthManager instance to use.
        token: The token to authenticate.
        
    Returns:
        UserContext if authentication succeeds.
        
    Raises:
        PermissionError: If token is invalid or missing.
    """
    user = auth_manager.authenticate(token)
    if user is None:
        raise PermissionError("Invalid or missing token")
    return user
