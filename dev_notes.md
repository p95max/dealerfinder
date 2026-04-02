# dev
```
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

# prod
```
docker compose up --build
```

python build_cities.py

# warm cache

Базовый запуск
python manage.py warm_search_cache

Прогреть только top 5 городов
python manage.py warm_search_cache --limit 5

Прогреть только радиус 20
python manage.py warm_search_cache --radii 20

Прогреть только города с count >= 3
python manage.py warm_search_cache --min-count 3

Комбинация
python manage.py warm_search_cache --limit 10 --radii 20 50 --min-count 2


docker compose exec web python manage.py warm_search_cache