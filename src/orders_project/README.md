Тестовое задание:

This is a technical requirement for this project:
* Please create a project which should provide the API endpoints for Orders.
* Create an app - Integration, which will sync your orders, so this Integration app should implement two-way sync between orders via API.
* In your Integration app you will have to provide an URL to an API endpoint of Orders.
* Run two versions of the same project on a separated environment with different databases.
* To make sure you've done everything correctly: run two projects A and B. If you go to admin and create an order in the project order in the project B and change it, the changes should appear in the project A.
* it would be great if you could explain some problems with two-way sync and which ones were resolved by your solution.
 By syncing orders I mean that your app should fetch orders from another system via API, (e.g. from an e-shop), then if somebody has made changes in your system, the order should be synced back into the another system, also via API, and vice-versa. Obviously, you don’t have the access to the another system, except POST, PUT and GET requests.

Для тестирования проекта нужно выполнить
``` shell
docker-compose up --build
```
После этого необходимо применить миграции:
``` shell
docker-compose run service1 python manage.py migrate
docker-compose run service2 python manage.py migrate
```

Тесты можно запустить:
``` shell
docker-compose run service1 python manage.py test
```

Для синхронизации изменеий составлен список состояния записей

Состояние | Код | Описание
--- | --- | ---
ST_NEW | 1 | Новый объект
ST_UPD | 2 | Обновление
ST_OK | 3 | Нормальное состояние объекта
ST_DEL | 4 | Пометка на удаление
ST_DEL_SYNCED | 5 | Удаление синхронизировано
ST_COLLISION | 6 | Возникла коллизия
ST_ERROR | 7 | Коллизия синхронизирована
ST_ERROR_SYNCED | 8 | Возникла ошибка
ST_SYNC | 9 | Ошибка синхронизирована

Таблица переходов состояний при получении объекта с удаленного сервиса
Получено | Было | Стало | Синхронизация |  |
--- | --- | ---| --- | ---
ST_NEW | ST_NEW | ST_COLLISION | + | Коллизия uuid |
ST_NEW | ST_OK | ST_OK | + | Синхронизация повтор | *
ST_NEW | ST_COLLISION | ST_COLLISION | + | Коллизия повтор | *
ST_NEW | - | ST_OK | + | Пришел новый объект | Создаем наш
ST_UPD | ST_UPD | ST_COLLISION | + | Коллизия up/up |
ST_UPD | ST_OK | ST_OK | + | Пришел измененный объект | Обновляем наш
ST_UPD | ST_DEL | ST_COLLISION | + | Коллизия up/del |
ST_UPD | ST_COLLISION | ST_COLLISION | + | Коллизия повтор | *
ST_OK | ST_NEW | ST_OK | - | Создание синхронизировано |
ST_OK | ST_UPD | ST_OK | - | Обновление синхронизировано |
ST_DEL | ST_UPD | ST_COLLISION | + | Коллизия del/up |
ST_DEL | ST_OK | ST_DEL_SYNCED | + | Пришел удаленный объект |
ST_DEL | ST_DEL | ST_COLLISION | + | Коллизия del/del |
ST_DEL | ST_DEL_SYNCED | ST_DEL_SYNCED | + | Синхронизация повтор | *
ST_DEL | ST_COLLISION | ST_COLLISION | + | Синхронизация повтор | *
ST_DEL_SYNCED | ST_DEL | ST_DEL_SYNCED | - | Удаление синхронизировано |
ST_COLLISION | ST_NEW | ST_COLLISION | - | Коллизия синхронихирована |
ST_COLLISION | ST_UPD | ST_COLLISION | - | Коллизия синхронихирована |
ST_COLLISION | ST_DEL | ST_COLLISION | - | Коллизия синхронихирована |
ST_COLLISION | ST_COLLISION | ST_COLLISION | - | Синхронизация повтор | *
ST_ERROR | * | ST_ERROR_SYNCED | + | Ошибка пришла |
ST_ERROR_SYNCED | ST_ERROR | ST_ERROR_SYNCED | - | Ошибка синхронизирована |

Другие компинации состояния считаются ошибочными.
Знаком **+** отмечена необходимость синхронизации текущего состояния объекта на другой сервис.