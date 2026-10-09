# GrimoireLab Core Docker Image

This docker image runs a container preinstalled with a certain release of
GrimoireLab core, including all libraries and programs. By default, it runs
the `grimoirelab` command.

For more information about GrimoireLab, please visit
our [website](https://chaoss.github.io/grimoirelab/).


## How to use this image

### Quickstart

This image allows you to run GrimoireLab Core Server, including its workers and administration commands.

Make sure MySQL and Valkey (a Redis-compatible key-value store) containers are
running.

```bash
docker network create grimoire-net

docker run --rm -d --net grimoire-net --name mysqldb -e 'MYSQL_ROOT_PASSWORD=root' mariadb:latest

docker run --rm -d --net grimoire-net --name valkeydb  valkey/valkey:latest valkey-server --appendonly yes
```

#### Configure the database

The command asks whether you want to create a superuser, so run it with `-it`:

```bash
docker run --rm -it --net grimoire-net \
    --env-file docker/grimoirelab.env \
    grimoirelab/grimoirelab-core \
    grimoirelab admin setup
```

To run it without prompts, use `--no-interactive` and set the superuser
credentials with environment variables:

```bash
docker run --rm --net grimoire-net \
    --env-file docker/grimoirelab.env \
    -e GRIMOIRELAB_SUPERUSER_USERNAME=admin \
    -e GRIMOIRELAB_SUPERUSER_PASSWORD=<password> \
    grimoirelab/grimoirelab-core \
    grimoirelab admin setup --no-interactive
```

#### Run the eventizers

Eventizers run the jobs that fetch data from software repositories and turn it
into events. Use `--workers` to set how many workers run in the pool.

```bash
docker run --rm -d --net grimoire-net --name grimoirelab-eventizers \
    --env-file docker/grimoirelab.env \
    grimoirelab/grimoirelab-core \
    grimoirelab run eventizers --workers 5
```


#### Run the SortingHat workers


SortingHat workers run the identity management jobs.

```bash
docker run --rm -d --net grimoire-net --name grimoirelab-sortinghat-workers \
    --env-file docker/grimoirelab.env \
    grimoirelab/grimoirelab-core \
    grimoirelab run sortinghat-workers --workers 5
```

#### Run the ushers

Ushers read the events from the Redis stream and store the identities they find
in SortingHat.

```bash
docker run --rm -d --net grimoire-net --name grimoirelab-ushers \
    --env-file docker/grimoirelab.env \
    grimoirelab/grimoirelab-core \
    grimoirelab run ushers --workers 20
```

#### Run the web server

The `--web` flag also serves the web interface. The server listens on
`127.0.0.1` by default, which isn't reachable from outside the container, so
set `GRIMOIRELAB_HTTP_HOST=0.0.0.0` to use `-p 8000:8000`.

```bash
docker run --rm -d --net grimoire-net --name grimoirelab-server \
    --env-file docker/grimoirelab.env -p 8000:8000 \
    -e GRIMOIRELAB_HTTP_HOST=0.0.0.0 \
    grimoirelab/grimoirelab-core \
    grimoirelab run server --web
```

To make the web interface work, collect the static files inside the server
container:

```bash
docker exec grimoirelab-server /opt/venv/bin/grimoirelab admin setup --no-interactive
```

#### Run the archivists

Archivists read the events from the Redis stream and store them in OpenSearch,
so they need an OpenSearch instance. Set its URL with
`GRIMOIRELAB_ARCHIVIST_STORAGE_URL`:

```bash
docker run --rm -d --net grimoire-net --name grimoirelab-archivists \
    --env-file docker/grimoirelab.env \
    -e GRIMOIRELAB_ARCHIVIST_STORAGE_URL=http://opensearch:9200 \
    grimoirelab/grimoirelab-core \
    grimoirelab run archivists --workers 20
```


## Building the image

Once the package is ready, make sure to follow these steps to build the Docker
image. The image requires that the `grimoirelab-core` Python package is built
and ready in `dist` directory.

Optionally, you can make sure there are no old packages by running:

```bash
rm -rf dist/
```

Before building the Python package, you need to compile the UI from the `ui/`
directory. If you skip this step, the server shows a blank page.

```bash
cd ui
corepack enable
yarn install
yarn build
cd ..
```

You can build a new package running the next command:

```bash
poetry build
```

Once the package is ready, to build the image, run `docker build` command from
the repository root directory:

```bash
docker build -f docker/Dockerfile -t grimoirelab/grimoirelab-core .
```

## License

GrimoireLab is licensed under GNU General Public License (GPL), version 3
or later.

However, this image is based on the [Debian docker image](https://hub.docker.com/_/debian).
Check their [license information](https://www.debian.org/social_contract#guidelines)
for the type of software contained in this image.
