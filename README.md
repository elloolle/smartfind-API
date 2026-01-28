## Запуск проекта
```bash
  docker compose --file deployment/docker-compose.yml up -d --build
```
## Запуск проекта без билда
```bash
  docker compose --file deployment/docker-compose.yml up -d
```
## Удалить бд
```bash
     docker rm -f  deployment-postgres-1 | docker volume rm deployment_db_data
```
### Команды для сервиса django
## Перед запуском нужно зайти в консоль сервиса django
```bash
    docker compose --file deployment/docker-compose.yml exec django bash
```
## Запуск проверки линтера ruff
```bash
    ruff check .
```
## Запуск тестов
```bash
    python manage.py test
```
## Инициализация бд дефолтными данными(запускается при старте контейнера)
```bash
    python manage.py create_default_db_objects
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
