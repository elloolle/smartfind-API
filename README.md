## Запуск проекта
```bash
pip install -r requirements.txt
docker compose -f docker-compose.local.yml up -d
python manage.py migrate
python manage.py runserver
```
## Запуск в продакшене (через Docker)
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
## Удалить бд при локальной разработке
```bash
  docker compose -f docker-compose.local.yml down -v
```
## Запуск проверки линтеров
```bash
    ruff check .
    pylint . 
```
## Запуск тестов
```bash
    python manage.py test
```
## Создание нового шаблонного приложения
```bash
    python manage.py startapp [name of app] --template ".\utils\app_template"                      
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
4. bash ```python manage.py sync_djstripe_webhook_secret```
