from db.dao.base import BaseDAO
from db.user.models import User, Profile

class UserDAO(BaseDAO):
    model = User

class ProfileDAO(BaseDAO):
    model = Profile