# app.py 需要确认的修改

在 `app.py` 里确认存在：

```python
from api_routes import api_bp
```

并且已经注册：

```python
app.register_blueprint(api_bp)
```

推荐位置：

```python
from auth_routes import auth_bp
from device_routes import device_bp
from stats_routes import stats_bp
from mongo_routes import mongo_bp
from api_routes import api_bp

app.register_blueprint(auth_bp)
app.register_blueprint(device_bp)
app.register_blueprint(stats_bp)
app.register_blueprint(mongo_bp)
app.register_blueprint(api_bp)
```
