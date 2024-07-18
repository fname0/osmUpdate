# Обновление данных OSM для веб-сервера, генерирующего тайлы

## Требования к системе

Должен быть установлен веб-сервер, генерирующий тайлы( [инструция тут](https://github.com/fname0/osmUpdate?tab=readme-ov-file#установка-веб-сервера) )

## Установка приложения

Клонируйте приложение или скачайте его архивом

## Использование приложения

Для запуска приложения достаточно выполнить( без sudo, от пользователя, у кого стоит веб-сервер )

```shell
python3 путь_к_папке_проекта/main.py
```

## Возможные ошибки

Во время импорта данных в БД, последним сообщением перед шестнадцатью сообщениями ```CREATE INDEX``` должно быть( временные значения будут отличаться ):

```shell
2024-07-18 18:05:13  osm2pgsql took 2019s (33m 39s) overall.
```

Если же вместо него вывелось сообщение ниже,

```shell
Processing: Node(83400k 817.6k/s) Way(0k 0.00k/s) Relation(0 0.0/s)Killed
```

То не хватает свободного места - освободите место либо в 39 строчке ```main.py``` уменьшите значение после флага ```-C```( по умолчанию 2500, уменьшение может привести к замедлению обновления )

Также если ядер CPU меньше четырёх, уменьшите значение после флага ```--number-processes```( также может увеличить время выполнения )

## Установка веб-сервера

Перед использованием данного приложения необходимо установить веб-сервер, генерирующий тайлы

Установите зависимости:

```shell
sudo apt update
sudo apt upgrade
sudo apt install screen locate libapache2-mod-tile renderd git tar unzip wget bzip2 apache2 lua5.1 mapnik-utils python3-mapnik python3-psycopg2 python3-yaml gdal-bin npm postgresql postgresql-contrib postgis postgresql-14-postgis-3 postgresql-14-postgis-3-scripts osm2pgsql net-tools curl osmctools
```

Создайте пользователя PostgreSQL _renderd и создайте базу данных gis, указав его как владельца:

```shell
sudo -u postgres -i
createuser _renderd
createdb -E UTF8 -O _renderd gis
```

Не выходя из пользователя postgres, установите в БД расширения и создайте таблицы:

```shell
psql
```

```shell
\c gis
```

```shell
CREATE EXTENSION postgis;
CREATE EXTENSION hstore;
ALTER TABLE geometry_columns OWNER TO _renderd;
ALTER TABLE spatial_ref_sys OWNER TO _renderd;
```

Выйдите из psql и установите mapnik.xml:

```shell
\q
```

```shell
exit
```

***Команды ниже необходимо выполнять не из-под sudo su***

```shell
mkdir ~/src
cd ~/src
git clone https://github.com/gravitystorm/openstreetmap-carto
cd openstreetmap-carto
sudo npm install -g carto
carto project.mml > mapnik.xml
```

Установите актуальный набор данных ЮФО и ЦФО, объедините их в один osm.pbf файл( это необходимо в связи с тем, что они имеют общие relations, поэтому при импорте их по-отдельности через osm2pgsql с флагом --append импорт будет проходить значительно дольше ):

```shell
mkdir ~/data
cd ~/data
wget https://download.geofabrik.de/russia/south-fed-district-latest.osm.pbf
wget https://download.geofabrik.de/russia/central-fed-district-latest.osm.pbf
chmod ugo+rwx south-fed-district-latest.osm.pbf
chmod ugo+rwx central-fed-district-latest.osm.pbf
osmconvert south-fed-district-latest.osm.pbf -o=south.o5m
osmconvert central-fed-district-latest.osm.pbf -o=centr.o5m
osmconvert centr.o5m south.o5m -o=both.o5m
osmconvert both.o5m -o=both.osm.pbf
chmod ugo+rwx both.osm.pbf
```

Импортируйте данные из osm.pbf в БД gis:

```shell
sudo -u _renderd osm2pgsql -d gis --create --slim  -G --hstore --tag-transform-script ~/src/openstreetmap-carto/openstreetmap-carto.lua -C 2500 --number-processes 2 -S ~/src/openstreetmap-carto/openstreetmap-carto.style ~/data/both.osm.pbf
```

Создайте необходимые индексы в БД и shapefile:

```shell
cd ~/src/openstreetmap-carto/
sudo -u _renderd psql -d gis -f indexes.sql
cd ~/src/openstreetmap-carto/
mkdir data
sudo chown _renderd data
sudo -u _renderd scripts/get-external-data.py
```

Сконфигурируйте renderd:

```shell
sudo nano /etc/renderd.conf
```

В конец файла добавьте строки( ***замените на нужные URI и accountname*** ):

```shell
[s2o]
URI=/hot/
XML=/home/accountname/src/openstreetmap-carto/mapnik.xml
HOST=localhost
TILESIZE=256
MAXZOOM=20
```

Перезапустите renderd и сервер apache:

```shell
sudo systemctl daemon-reload
sudo systemctl restart renderd
sudo systemctl restart apache2
sudo /etc/init.d/apache2 restart
```

Готово, по адресам http://127.0.0.1/hot/{z}/{x}/{y}.png доступны тайлы( вместо 127.0.0.1 можно ввести серый/белый IP-адреса сервера )