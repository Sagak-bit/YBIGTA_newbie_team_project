from app.user.user_repository import UserRepository
from app.user.user_schema import User, UserLogin, UserUpdate

class UserService:
    def __init__(self, userRepoitory: UserRepository) -> None:
        self.repo = userRepoitory

    def login(self, user_login: UserLogin) -> User:
        ## TODO
        user = self.repo.get_user_by_email(user_login.email)

        if user is None:
            raise ValueError("User not Found.")
        elif user.password != user_login.password:
            raise ValueError("Invalid ID/PW")
        return user
        
    def register_user(self, new_user: User) -> User:
        ## TODO
        user = self.repo.get_user_by_email(new_user.email)
        if user is not None:
            raise ValueError("User already Exists.")
        saved_user = self.repo.save_user(new_user)
        return saved_user

    def delete_user(self, email: str) -> User:
        ## TODO        
        deleted_user = self.repo.get_user_by_email(email)
        if deleted_user is None:
            raise ValueError("User not Found.")
        deleted_user = self.repo.delete_user(deleted_user)
        return deleted_user

    def update_user_pwd(self, user_update: UserUpdate) -> User:
        ## TODO
        existing_user = self.repo.get_user_by_email(user_update.email)
        if existing_user is None:
            raise ValueError("User not Found.")
        existing_user.password = user_update.new_password
        self.repo.save_user(existing_user)
        return existing_user
        