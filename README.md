```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
docker compose --file deployment/docker-compose.yaml up -d #поднять постгрес
stripe listen --forward-to localhost:8000/api/payments/process/stripe/ -e checkout.session.async_payment_failed,checkout.session.async_payment_succeeded,checkout.session.completed,checkout.session.expired #активация stripe cli     
stripe trigger checkout.session.completed #отправка запроса на вебхук 
```