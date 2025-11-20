## Запуск проекта
```bash
pip install -r requirements.txt
docker compose --file deployment/docker-compose.yaml up -d # поднять постгрес
python manage.py migrate
python manage.py runserver
```
## Запуск тестов
```bash
python manage.py test
```
## Тестирование вебхуков
```bash
stripe listen --forward-to localhost:8000/api/payments/webhook/  # активация stripe cli     
stripe trigger checkout.session.completed # отправка запроса на вебхук 
```
## Прокинуть вебхуки на ngrok
```bash
ngrok http 8000
```