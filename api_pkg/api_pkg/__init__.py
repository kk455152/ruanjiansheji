from flask import Blueprint

api_bp = Blueprint("api_routes", __name__, url_prefix="/api")

# 导入后自动把路由注册到 api_bp。
from . import auth_home  # noqa: F401,E402
from . import player  # noqa: F401,E402
from . import friends_rooms  # noqa: F401,E402
from . import share_data_history  # noqa: F401,E402
from . import device  # noqa: F401,E402
from . import music_service  # noqa: F401,E402
from . import panel_page  # noqa: F401,E402
from . import db_board  # noqa: F401,E402
