python3 -m venv venv
source venv/bin/activate
pip install pymongo -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install pymongo==3.12.3 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip list | grep pymongo
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
cd frontend && npm install --registry=https://registry.npmmirror.com && cd -