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
## Подключение вебхуков
1. Создать через админку новый api_key со значением STRIPE_API_KEY.
2. Создать через админку новый webhook endpoint с base_url, на который stripe будет напрямую присылать события
3. В stripe поставить url для приема вебхуков, который стал названием созданного webhook endpoint
4. python ```python manage.py sync_djstripe_webhook_secret```

## Создание нового шаблонного приложения
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