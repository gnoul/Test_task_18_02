
docker-compose run service1 python manage.py migrate
docker-compose run service2 python manage.py migrate

docker-compose run service1 python manage.py test