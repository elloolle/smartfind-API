## Запуск проекта
```bash
pip install -r requirements.txt
docker compose --file deployment/docker-compose.yaml up -d
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
## Прокинуть вебхуки
# clo
```bash
clo publish http 8000
```
# ngrok
```bash
ngrok http 8000
```
## Установить верификацию сигнатуры вебхуков
```python
 from djstripe.models import WebhookEndpoint
 
 raw = settings.DJSTRIPE_WEBHOOK_SECRET
 try:
     endpoints = WebhookEndpoint.objects.all()
 except Exception:
     endpoints = None
 if not raw or not endpoints:
     return
 endpoint = endpoints[0]
 endpoint.secret = raw
 endpoint.save()
```

## Создание нового приложения
```bash
    python manage.py startapp [name of app] --template ".\utils\app_template"                      
``` 

## Удалить бд
```bash
     docker rm -f  deployment-postgres-1 | docker volume rm deployment_db_data
```
## Запуск проверки линтера ruff
```bash
    ruff check .
```