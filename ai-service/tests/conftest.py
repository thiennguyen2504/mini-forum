import os
import sys

# Đảm bảo ai-service/ nằm đầu sys.path khi chạy test từ thư mục gốc repo
AI_SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AI_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, AI_SERVICE_ROOT)
