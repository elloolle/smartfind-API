```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
docker compose --file deployment/docker-compose.yaml up -d #поднять постгрес
stripe listen --forward-to localhost:8000/api/payments/webhook/  #активация stripe cli     
stripe trigger checkout.session.completed #отправка запроса на вебхук 
ngrok http 8000 # прокинуть запросы на ngrok
```