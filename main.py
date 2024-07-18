from getpass import getuser
user = getuser()
if user == "root":
    print("Запустите скрипт без sudo")
    exit(1)

import os
dir = os.path.dirname(os.path.realpath(__file__))

import requests
timestamp = requests.get('http://download.geofabrik.de/russia/south-fed-district-updates/state.txt').text.split('\n')[1]

if timestamp.split('=')[0] == 'timestamp':
    f = open(f"{dir}/version.txt", "r")
    curTimestamp = f.read()
    f.close()

    if curTimestamp != timestamp:
        print("---  Найдена более актуальная версия данных OSM, применяется ---")

        # Очистка папки data
        os.system(f"rm {dir}/data/*")
        # Загрузка osm.pbf
        os.system(f"wget https://download.geofabrik.de/russia/south-fed-district-latest.osm.pbf -P {dir}/data")
        os.system(f"chmod ugo+rwx {dir}/data/south-fed-district-latest.osm.pbf")
        os.system(f"wget https://download.geofabrik.de/russia/central-fed-district-latest.osm.pbf -P {dir}/data")
        os.system(f"chmod ugo+rwx {dir}/data/central-fed-district-latest.osm.pbf")
        # Объединение osm.pbf
        os.system(f"osmconvert {dir}/data/south-fed-district-latest.osm.pbf -o={dir}/data/south.o5m")
        os.system(f"osmconvert {dir}/data/central-fed-district-latest.osm.pbf -o={dir}/data/centr.o5m")
        os.system(f"osmconvert {dir}/data/centr.o5m {dir}/data/south.o5m -o={dir}/data/both.o5m")
        os.system(f"osmconvert {dir}/data/both.o5m -o={dir}/data/both.osm.pbf")
        os.system(f"chmod ugo+rwx {dir}/data/both.osm.pbf")
        print("---  osm.pbf готов  ---")
        # Удаление старых тайлов из кэша
        os.system("sudo rm -rf /var/cache/renderd/tiles/s2o")
        print("---  Старые тайлы в кэше очищены  ---")
        # Импорт osm.pbf в pgsql
        os.system(f"sudo -u _renderd osm2pgsql -d gis --create --slim  -G --hstore --tag-transform-script /home/{user}/src/openstreetmap-carto/openstreetmap-carto.lua -C 2500 --number-processes 4 -S /home/{user}/src/openstreetmap-carto/openstreetmap-carto.style {dir}/data/both.osm.pbf")
        # Создание необходимых индексов
        os.system(f"sudo -u _renderd psql -d gis -f /home/{user}/src/openstreetmap-carto/indexes.sql")
        print("---  Импорт данных в БД закончен ---")
        # Перезагрузка сервера, генерация новых тайлов
        os.system("sudo systemctl daemon-reload")
        os.system("sudo systemctl restart renderd")
        os.system("sudo systemctl restart apache2")
        os.system("sudo /etc/init.d/apache2 restart")
        print("---  Сервер перезагружен и использует актуальные данные OSM  ----")

        f = open(f"{dir}/version.txt", "w")
        f.write(timestamp)
        f.close()
else:
    print("Сайт с выгрузками OSM не отвечает корректно =(")